"""MCP server mínimo do CONO Causal Gym.

JSON-RPC 2.0 sobre stdio, no mesmo padrão do cono-mcp-harness:
initialize, tools/list, tools/call, e nada mais. Ferramenta desconhecida
é recusada pela AI-Jail — o servidor nunca inventa uma tool.

Tools (as 5 do spec + as 2 exclusivas do Meta-Símbolo + create_uif):
  create_uif, get_local_causal_view, deposit_trail, follow_trail,
  inspect_identity, request_symbol_formation, propose_geodesic,
  audit_geodesic, request_diversity_audit.

O servidor nasce com um grafo já construído (como o harness nasce com
um cenário), mas o agente pode CRIAR UIFs novas pela tool create_uif:
uma UIF nasce isolada (sem rastros) e só entra na causalidade quando
recebe rastros por deposit_trail. Criar identidades é o ato de gênese
do mundo — o serial é único e a duplicação é recusada (deduplicação
natural, como na ingestão do mnhi-3.0).

Regra de emergência do Meta-Símbolo (v0.3, corrigida 17/11): ele se
forma quando há 2+ Símbolos VÁLIDOS agora, a auditoria de diversidade
passa (tensão presente) e o portão de emergência passa: ISC_Global
≥ 0,80 e H_causal ≥ log2(N)/2 — H_causal é a Shannon sobre os ISCs
normalizados (a definição anterior, teto H ≤ 0,1 sobre o peso dos
rastros, estava invertida e foi apagada).
"""

import hashlib
import json
import sys
from typing import Any

from .auditoria import auditoria_diversidade
from .causal import causal_entropy_bits, pode_emergir_meta_simbolo
from .espectro import avaliar_cluster
from .geodesica import auditar_geodesica
from .grafo import GrafoCausal, UIF


def _sha(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def construir_cenario_duas_cliques():
    """Mundo padrão do MVP: duas cliques K6 desconectadas (A e B).
    Retorna (grafo, {"A": [hashes], "B": [hashes]})."""
    grafo = GrafoCausal()
    grupos = {}
    for grupo in ("A", "B"):
        hs = []
        for i in range(6):
            uif = UIF(
                serial=f"uif-{grupo.lower()}{i}",
                tipo_agente="no",
                funcao_s=f"no-{grupo.lower()}{i}",
            )
            grafo.adicionar_uif(uif)
            hs.append(uif.hash_uif)
        for i in range(6):
            for j in range(i + 1, 6):
                grafo.depositar_rastro(hs[i], hs[j], "liga", peso=1.0)
        grupos[grupo] = hs
    return grafo, grupos


def construir_cenario_tres_cliques():
    """Mundo de 3 cliques K6 (A, B, C) com uma única ponte B-C (peso 8).
    Os rastros pesados dentro de A NÃO estão aqui: a demo os deposita
    via tools, para que A se forme válido e morra depois, ficando no
    registro. Quando A morre, só B e C restam válidos — e a H_causal
    entre eles é 1,0 bit (dois ISCs iguais). Retorna (grafo, {"A": [...],
    "B": [...], "C": [...]})."""
    grafo, grupos = construir_cenario_duas_cliques()
    grupos["C"] = []
    for i in range(6):
        uif = UIF(
            serial=f"uif-c{i}",
            tipo_agente="no",
            funcao_s=f"no-c{i}",
        )
        grafo.adicionar_uif(uif)
        grupos["C"].append(uif.hash_uif)
    for i in range(6):
        for j in range(i + 1, 6):
            grafo.depositar_rastro(grupos["C"][i], grupos["C"][j], "liga", peso=1.0)
    grafo.depositar_rastro(grupos["B"][0], grupos["C"][0], "ponte", peso=8.0)
    return grafo, grupos


class ConoGymServer:
    """Servidor JSON-RPC 2.0 sobre stdio expondo as tools do gym."""

    TOOLS = [
        {"name": "create_uif", "inputSchema": {"type": "object", "properties": {"serial": {"type": "string"}, "tipo_agente": {"type": "string"}, "funcao_s": {"type": "string"}}, "required": ["serial", "tipo_agente", "funcao_s"]}},
        {"name": "get_local_causal_view", "inputSchema": {"type": "object", "properties": {"hash_uif": {"type": "string"}, "raio": {"type": "integer"}}, "required": ["hash_uif"]}},
        {"name": "deposit_trail", "inputSchema": {"type": "object", "properties": {"origem": {"type": "string"}, "destino": {"type": "string"}, "tipo_relacao": {"type": "string"}, "peso": {"type": "number"}}, "required": ["origem", "destino", "tipo_relacao"]}},
        {"name": "follow_trail", "inputSchema": {"type": "object", "properties": {"hash_rastro": {"type": "string"}}, "required": ["hash_rastro"]}},
        {"name": "inspect_identity", "inputSchema": {"type": "object", "properties": {"hash_uif": {"type": "string"}}, "required": ["hash_uif"]}},
        {"name": "request_symbol_formation", "inputSchema": {"type": "object", "properties": {"serial_simbolo": {"type": "string"}, "membros": {"type": "array", "items": {"type": "string"}}}, "required": ["serial_simbolo"]}},
        {"name": "propose_geodesic", "inputSchema": {"type": "object", "properties": {"payload": {"type": "object"}}, "required": ["payload"]}},
        {"name": "audit_geodesic", "inputSchema": {"type": "object", "properties": {"proposta_id": {"type": "integer"}}, "required": ["proposta_id"]}},
        {"name": "request_diversity_audit", "inputSchema": {"type": "object", "properties": {}}},
    ]

    def __init__(self, grafo: GrafoCausal) -> None:
        self.grafo = grafo
        self.foco = None
        self.simbolos = {}  # serial -> relatório de avaliar_cluster
        self.meta_simbolo = None
        self.geodesicas = []  # propostas registradas, aguardando auditoria
        # Regras de julgamento vigentes. Só mudam por geodésica aprovada.
        self.regras = {"limiar_isc": 0.85, "limiar_var": 0.36, "limiar_gini": 0.30}

    # -- JSON-RPC ------------------------------------------------------

    def handle_request(self, req: dict[str, Any]) -> dict[str, Any]:
        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params") or {}

        if method == "initialize":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"serverInfo": {"name": "cono-causal-gym", "version": "0.1.0"}}}

        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": self.TOOLS}}

        if method == "tools/call":
            name = params.get("name")
            args = params.get("arguments") or {}
            try:
                obs = self._dispatch_tool(name, args)
                return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "json", "data": obs}]}}
            except Exception as exc:
                return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32602, "message": str(exc)}}

        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Metodo nao suportado: {method}"}}

    def _dispatch_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "create_uif":
            return self._criar_uif(
                str(args["serial"]),
                str(args["tipo_agente"]),
                str(args["funcao_s"]),
            )
        if name == "get_local_causal_view":
            return self._vista_local(str(args["hash_uif"]), int(args.get("raio", 1)))
        if name == "deposit_trail":
            return self._depositar(
                str(args["origem"]),
                str(args["destino"]),
                str(args["tipo_relacao"]),
                float(args.get("peso", 1.0)),
            )
        if name == "follow_trail":
            return self._seguir(str(args["hash_rastro"]))
        if name == "inspect_identity":
            return self._inspecionar(str(args["hash_uif"]))
        if name == "request_symbol_formation":
            return self._formar_simbolo(
                str(args["serial_simbolo"]), args.get("membros")
            )
        if name == "propose_geodesic":
            return self._propor_geodesica(args["payload"])
        if name == "audit_geodesic":
            return self._auditar_geodesica(int(args["proposta_id"]))
        if name == "request_diversity_audit":
            return self._auditoria()
        raise ValueError(f"Tool nao autorizada pela AI-Jail: {name}")

    # -- Tools ----------------------------------------------------------

    def _criar_uif(self, serial: str, tipo_agente: str, funcao_s: str):
        """Cria uma UIF nova. O serial é o identificador único de
        gênese: duplicá-lo é recusado (deduplicação natural). A UIF
        nasce isolada, sem rastros — só entra na causalidade quando
        recebe rastros por deposit_trail. Criar não dispara a
        verificação do Meta-Símbolo: nada sobre os Símbolos mudou."""
        for nome, valor in (
            ("serial", serial),
            ("tipo_agente", tipo_agente),
            ("funcao_s", funcao_s),
        ):
            if not valor or not valor.strip():
                raise ValueError(f"create_uif precisa de '{nome}' não vazio")
        uif = UIF(serial=serial, tipo_agente=tipo_agente, funcao_s=funcao_s)
        self.grafo.adicionar_uif(uif)
        return {
            "hash_uif": uif.hash_uif,
            "serial": serial,
            "tipo_agente": tipo_agente,
            "criado": True,
            "nota": "UIF isolada: sem rastros até receber um deposit_trail.",
        }

    def _vista_local(self, hash_uif: str, raio: int):
        vista = self.grafo.vizinhanca(hash_uif, raio=raio)
        return {
            "centro": hash_uif,
            "raio": raio,
            "vizinhos": [
                {
                    "hash_uif": h,
                    "rastros": [
                        {"hash_rastro": hr, "peso": p} for hr, p in rastros
                    ],
                }
                for h, rastros in vista.items()
            ],
        }

    def _depositar(self, origem, destino, tipo_relacao, peso):
        if peso <= 0:
            raise ValueError("peso do rastro precisa ser positivo")
        rastro = self.grafo.depositar_rastro(origem, destino, tipo_relacao, peso)
        formou_meta = self._verificar_meta_simbolo()
        return {
            "hash_rastro": rastro.hash_rastro,
            "origem": origem,
            "destino": destino,
            "tipo_relacao": tipo_relacao,
            "peso": peso,
            "meta_simbolo_formado_agora": formou_meta,
            "meta_simbolo_existe": self.meta_simbolo is not None,
        }

    def _seguir(self, hash_rastro: str):
        rastro = self.grafo.rastro_por_hash(hash_rastro)
        if rastro is None:
            raise ValueError(f"rastro desconhecido: {hash_rastro}")
        self.foco = rastro.destino
        return {"foco": self.foco, "vista": self._vista_local(self.foco, raio=1)}

    def _inspecionar(self, hash_uif: str):
        uif = self.grafo.uif_por_hash(hash_uif)
        if uif is None:
            raise ValueError(f"UIF desconhecida: {hash_uif}")
        # Só hash + tipo. Nunca o estado mutável completo — nem o serial.
        return {"hash_uif": uif.hash_uif, "tipo_agente": uif.tipo_agente}

    def _formar_simbolo(self, serial_simbolo: str, membros):
        if membros is None:
            membros = self.grafo.hashes()
        if not membros:
            raise ValueError("cluster vazio: nenhum membro para avaliar")
        for h in membros:
            if self.grafo.uif_por_hash(h) is None:
                raise ValueError(f"membro desconhecido: {h}")
        relatorio = avaliar_cluster(
            self.grafo.subgrafo(membros),
            serial_simbolo,
            limiar_isc=self.regras["limiar_isc"],
            limiar_var=self.regras["limiar_var"],
        )
        registrado = False
        if relatorio["simbolo"]:
            # O registro é append-only, como o Pentacosagram: um Símbolo
            # formado fica no registro com seu hash. A validade é
            # re-medida a cada episódio pelo loop — o registro não apaga.
            self.simbolos[serial_simbolo] = {**relatorio, "membros": list(membros)}
            registrado = True
            self._verificar_meta_simbolo()
        return {**relatorio, "registrado": registrado}

    def _propor_geodesica(self, payload):
        if self.meta_simbolo is None:
            raise ValueError(
                "Geodésica só pode ser proposta pelo Meta-Símbolo, que ainda não existe."
            )
        if not isinstance(payload, dict):
            raise ValueError("payload da geodésica precisa ser um objeto")
        for campo in ("mudanca_regra", "efeito_esperado"):
            if not payload.get(campo):
                raise ValueError(f"payload da geodésica precisa de '{campo}'")
        proposta = {
            "id": len(self.geodesicas) + 1,
            "payload": payload,
            "status": "aguardando_auditoria",
        }
        self.geodesicas.append(proposta)
        return {
            **proposta,
            "nota": "Registrada, não aprovada: use audit_geodesic para julgá-la.",
        }

    def _auditar_geodesica(self, proposta_id: int):
        if self.meta_simbolo is None:
            raise ValueError(
                "Geodésica só pode ser auditada pelo Meta-Símbolo, que ainda não existe."
            )
        proposta = next(
            (g for g in self.geodesicas if g["id"] == proposta_id), None
        )
        if proposta is None:
            raise ValueError(f"proposta desconhecida: {proposta_id}")
        if proposta["status"] != "aguardando_auditoria":
            return proposta  # idempotente: devolve o veredito já dado
        relatorio = auditar_geodesica(
            self.grafo, self.simbolos, self.regras, proposta
        )
        proposta["status"] = relatorio["veredito"]
        proposta["auditoria"] = relatorio
        if relatorio["veredito"] == "aprovada":
            self.regras = relatorio["novas_regras"]
        return proposta

    def _auditoria(self):
        if self.meta_simbolo is None:
            raise ValueError(
                "Auditoria de diversidade só pode ser pedida pelo Meta-Símbolo, que ainda não existe."
            )
        relatorio = auditoria_diversidade(
            self.grafo,
            self.simbolos_validos(),
            limiar_gini=self.regras["limiar_gini"],
            limiar_var=self.regras["limiar_var"],
        )
        return {**relatorio, "meta_simbolo": self.meta_simbolo["hash_meta_simbolo"]}

    # -- Medição do estado atual ---------------------------------------

    def simbolos_validos(self):
        """Reavalia cada Símbolo registrado sob as regras vigentes e
        devolve só os que continuam válidos (com "membros"). O registro
        é append-only; a validade é do agora."""
        validos = []
        for serial, rel in self.simbolos.items():
            reavaliado = avaliar_cluster(
                self.grafo.subgrafo(rel.get("membros", [])),
                serial,
                limiar_isc=self.regras["limiar_isc"],
                limiar_var=self.regras["limiar_var"],
            )
            if reavaliado["simbolo"]:
                validos.append({**reavaliado, "membros": rel.get("membros", [])})
        return validos

    def h_causal_atual(self):
        """H_causal entre os Símbolos válidos agora, ou None."""
        iscs = [s["isc_local"] for s in self.simbolos_validos()]
        if len(iscs) < 2:
            return None
        return causal_entropy_bits(iscs)

    def isc_global_atual(self):
        """ISC_Global (média dos ISCs dos Símbolos válidos), ou None."""
        validos = self.simbolos_validos()
        if not validos:
            return None
        return sum(s["isc_local"] for s in validos) / len(validos)

    # -- Emergência do Meta-Símbolo --------------------------------------

    def _verificar_meta_simbolo(self) -> bool:
        """Forma o Meta-Símbolo quando há 2+ Símbolos VÁLIDOS agora, a
        auditoria de diversidade passa e o portão de emergência passa:
        ISC_Global ≥ 0,80 e H_causal ≥ log2(N)/2. Retorna True só na
        chamada que forma.

        Correção v0.3 (17/11, informação do Dan): a definição anterior
        de H_causal estava invertida (entropia do peso dos rastros
        entre Símbolos, com teto H ≤ 0,1 — premiava a concentração).
        A definição real é Shannon sobre os ISCs normalizados, com
        PISO H ≥ log2(N)/2. Nota honesta: no gym, como um Símbolo
        válido exige ISC ≥ 0,85, os portões de ISC_Global e H_causal
        são automaticamente satisfeitos quando há 2+ válidos — eles
        discriminam no harness, onde shards podem ser fracos. O que
        discrimina no gym continua sendo a tensão e a contagem de
        Símbolos válidos."""
        if self.meta_simbolo is not None:
            return False
        validos = self.simbolos_validos()
        if len(validos) < 2:
            return False
        auditoria = auditoria_diversidade(
            self.grafo,
            validos,
            limiar_gini=self.regras["limiar_gini"],
            limiar_var=self.regras["limiar_var"],
        )
        if not auditoria["tensao_presente"]:
            return False
        emergiu, isc_global, h, _h_min = pode_emergir_meta_simbolo(
            [s["isc_local"] for s in validos], True
        )
        if not emergiu:
            return False
        hashes = sorted(s["hash_simbolo"] for s in validos)
        self.meta_simbolo = {
            "hash_meta_simbolo": _sha(
                "meta|" + "|".join(hashes) + f"|h_causal={h:.6f}"
            ),
            "simbolos": sorted(s["serial"] for s in validos),
            "h_causal": h,
            "isc_global": isc_global,
            "auditoria_na_formacao": auditoria,
        }
        return True

    def run_stdio(self) -> None:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            req = json.loads(line)
            resp = self.handle_request(req)
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    grafo, _grupos = construir_cenario_duas_cliques()
    servidor = ConoGymServer(grafo)
    servidor.run_stdio()
