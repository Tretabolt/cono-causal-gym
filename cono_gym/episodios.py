"""Loop de episódios do CONO Causal Gym.

A divisão de papéis é deliberada e está escrita aqui para não se perder:

- O AGENTE age SÓ pelas tools do MCP server (ver, depositar, seguir,
  formar Símbolo). Ele não toca no grafo diretamente.
- O EXPERIMENTADOR mede com as mesmas funções verificadas que as tools
  usam (avaliar_cluster, auditoria_diversidade), aplicadas ao grafo do
  servidor a cada episódio. Não existe tool de medir — medir é o trabalho
  de quem roda o experimento, não do agente.

Política do agente (MVP, determinística por semente): a cada episódio
ele olha a vizinhança de uma UIF sorteada, deposita 3 rastros entre
UIFs sorteadas (peso 1 na maioria das vezes, 5 ou 8 às vezes — o
rich-get-richer em miniatura), e tenta formar Símbolo nos clusters
conhecidos e no grafo inteiro.

Métricas por episódio: Símbolos registrados, quantos continuam válidos,
Gini dos pesos, Var média, tensão presente, Meta-Símbolo existe.
Estabilidade de um Símbolo = episódios em que ele continuou válido /
episódios desde que se formou. O registro de Símbolos é append-only:
um Símbolo que se desfez continua no registro, e a estabilidade é o
que conta a história dele.
"""

import random

from .auditoria import auditoria_diversidade
from .espectro import avaliar_cluster


def _chamar(servidor, nome, argumentos=None):
    resp = servidor.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": nome, "arguments": argumentos or {}},
        }
    )
    if "error" in resp:
        raise RuntimeError(resp["error"]["message"])
    return resp["result"]["content"][0]["data"]


class LoopEpisodios:
    """Roda N episódios contra um ConoGymServer e mede tudo."""

    def __init__(self, servidor, clusters=None, semente=42, rastros_por_episodio=3):
        self.servidor = servidor
        self.clusters = clusters or {}
        self.rng = random.Random(semente)
        self.rastros_por_episodio = rastros_por_episodio
        self.estabilidade = {}  # serial -> {"desde": ep, "validos": n, "total": m}

    def _medir(self, episodio):
        grafo = self.servidor.grafo
        simbolos = list(self.servidor.simbolos.values())
        validos = self.servidor.simbolos_validos()
        auditoria = auditoria_diversidade(
            grafo,
            validos,
            limiar_gini=self.servidor.regras["limiar_gini"],
            limiar_var=self.servidor.regras["limiar_var"],
        )
        n_validos = 0
        for serial, rel in self.servidor.simbolos.items():
            if serial not in self.estabilidade:
                self.estabilidade[serial] = {"desde": episodio, "validos": 0, "total": 0}
            reavaliado = avaliar_cluster(
                grafo.subgrafo(rel.get("membros", [])), serial
            )
            est = self.estabilidade[serial]
            est["total"] += 1
            if reavaliado["simbolo"]:
                n_validos += 1
                est["validos"] += 1
        h = self.servidor.h_causal_atual()
        return {
            "n_registrados": len(simbolos),
            "n_validos": n_validos,
            "gini_pesos": auditoria["gini_pesos"],
            "var_media": auditoria["var_media_simbolos"],
            "h_causal": h,
            "isc_global": self.servidor.isc_global_atual(),
            "tensao_presente": auditoria["tensao_presente"],
            "meta_simbolo": self.servidor.meta_simbolo is not None,
            "n_rastros": grafo.n_arestas(),
        }

    def _episodio(self, n):
        servidor = self.servidor
        hashes = servidor.grafo.hashes()
        foco = self.rng.choice(hashes)
        _chamar(servidor, "get_local_causal_view", {"hash_uif": foco})
        for _ in range(self.rastros_por_episodio):
            a, b = self.rng.sample(hashes, 2)
            peso = self.rng.choices([1.0, 5.0, 8.0], weights=[7, 2, 1])[0]
            _chamar(
                servidor,
                "deposit_trail",
                {"origem": a, "destino": b, "tipo_relacao": "episodio", "peso": peso},
            )
        for nome, membros in self.clusters.items():
            _chamar(
                servidor,
                "request_symbol_formation",
                {"serial_simbolo": f"simbolo-{nome}", "membros": membros},
            )
        _chamar(
            servidor,
            "request_symbol_formation",
            {"serial_simbolo": "simbolo-tudo"},
        )
        return {"episodio": n, **self._medir(n)}

    def rodar(self, n_episodios=12):
        episodios = [self._episodio(n + 1) for n in range(n_episodios)]
        estabilidades = {
            serial: (est["validos"] / est["total"] if est["total"] else 0.0)
            for serial, est in self.estabilidade.items()
        }
        ep_meta = next((e["episodio"] for e in episodios if e["meta_simbolo"]), None)
        resumo = {
            "episodios": n_episodios,
            "simbolos_registrados": sorted(self.estabilidade),
            "estabilidade_por_simbolo": {
                k: round(v, 3) for k, v in estabilidades.items()
            },
            "estabilidade_media": round(
                sum(estabilidades.values()) / len(estabilidades), 3
            )
            if estabilidades
            else 0.0,
            "episodios_com_tensao": sum(1 for e in episodios if e["tensao_presente"]),
            "meta_simbolo_formado": ep_meta is not None,
            "episodio_meta": ep_meta,
            "gini_final": episodios[-1]["gini_pesos"],
            "var_media_final": episodios[-1]["var_media"],
        }
        return {"episodios": episodios, "resumo": resumo}
