"""Demo de uma sessão no MCP server do gym, via JSON-RPC em processo.

O cliente aqui é só um dicionário por chamada — o transporte é o mesmo
que o servidor usaria sobre stdio. A sessão:

1. Lista as tools e tenta uma tool que não existe (AI-Jail recusa).
2. Forma o Símbolo A (clique K6) e o Símbolo B (outra K6).
   Com pesos uniformes não há tensão: nada de Meta-Símbolo ainda.
3. Tenta a auditoria e a geodésica sem Meta-Símbolo: recusadas.
4. Deposita 5 rastros pesados (peso 8) entre as cliques: a assimetria
   sobe, a tensão aparece, o Meta-Símbolo se forma.
5. Auditoria passa; geodésica válida é registrada (não aprovada);
   geodésica incompleta é recusada.
6. O gym cresce: 6 UIFs novas são criadas pela tool create_uif,
   ligadas em K6, e formam um terceiro Símbolo — sem nenhum grafo
   pré-construído.

Uso: python3 -m cono_gym.demo_mcp
"""

import json

from .mcp_server import ConoGymServer, construir_cenario_duas_cliques


def _chamar(servidor, id_req, metodo, params=None):
    req = {"jsonrpc": "2.0", "id": id_req, "method": metodo}
    if params is not None:
        req["params"] = params
    resp = servidor.handle_request(req)
    print(f">>> {metodo} {json.dumps(params or {}, ensure_ascii=False)}")
    print(f"<<< {json.dumps(resp, ensure_ascii=False)}")
    print()
    return resp


def _ferramenta(servidor, id_req, nome, argumentos=None):
    return _chamar(
        servidor,
        id_req,
        "tools/call",
        {"name": nome, "arguments": argumentos or {}},
    )


def main():
    grafo, grupos = construir_cenario_duas_cliques()
    servidor = ConoGymServer(grafo)
    rid = 0

    def prox():
        nonlocal rid
        rid += 1
        return rid

    _chamar(servidor, prox(), "initialize")
    _chamar(servidor, prox(), "tools/list")
    _ferramenta(servidor, prox(), "abrir_porta")  # não existe: AI-Jail recusa

    a0 = grupos["A"][0]
    _ferramenta(servidor, prox(), "inspect_identity", {"hash_uif": a0})
    _ferramenta(servidor, prox(), "get_local_causal_view", {"hash_uif": a0})

    _ferramenta(
        servidor,
        prox(),
        "request_symbol_formation",
        {"serial_simbolo": "simbolo-A", "membros": grupos["A"]},
    )
    _ferramenta(
        servidor,
        prox(),
        "request_symbol_formation",
        {"serial_simbolo": "simbolo-B", "membros": grupos["B"]},
    )
    print("Dois Símbolos registrados, pesos uniformes: sem tensão, sem Meta-Símbolo.")
    print()

    _ferramenta(servidor, prox(), "request_diversity_audit")
    _ferramenta(
        servidor,
        prox(),
        "propose_geodesic",
        {"payload": {"mudanca_regra": "tau 1.0 -> 0.9", "efeito_esperado": "mais Símbolos"}},
    )

    # 5 rastros pesados entre as cliques: a assimetria sobe e a tensão aparece.
    for i in range(5):
        _ferramenta(
            servidor,
            prox(),
            "deposit_trail",
            {
                "origem": grupos["A"][i],
                "destino": grupos["B"][i],
                "tipo_relacao": "ponte",
                "peso": 8.0,
            },
        )

    print("Meta-Símbolo formado:", servidor.meta_simbolo is not None)
    if servidor.meta_simbolo:
        print("Hash_Meta-Símbolo:", servidor.meta_simbolo["hash_meta_simbolo"][:16], "…")
    print()

    _ferramenta(servidor, prox(), "request_diversity_audit")
    _ferramenta(
        servidor,
        prox(),
        "propose_geodesic",
        {
            "payload": {
                "mudanca_regra": "limiar_var 0.36 -> 0.40",
                "efeito_esperado": "Símbolos com VarPn até 0,40 passam a valer",
                "regra": "limiar_var",
                "de": 0.36,
                "para": 0.40,
            }
        },
    )
    _ferramenta(servidor, prox(), "audit_geodesic", {"proposta_id": 1})
    _ferramenta(
        servidor, prox(), "propose_geodesic", {"payload": {"mudanca_regra": "tau 1.0"}}
    )

    print("--- O gym cresce: uma terceira clique, criada pela tool ---")
    print()
    # Os 15 depósitos da clique nova são silenciosos: o que importa é
    # o resultado — a terceira clique existe e forma um Símbolo.
    def _silencioso(nome, argumentos=None):
        return servidor.handle_request(
            {
                "jsonrpc": "2.0",
                "id": prox(),
                "method": "tools/call",
                "params": {"name": nome, "arguments": argumentos or {}},
            }
        )

    hs_novos = []
    for i in range(6):
        resp = _silencioso(
            "create_uif",
            {
                "serial": f"uif-n{i}",
                "tipo_agente": "no",
                "funcao_s": f"no-n{i}",
            },
        )
        hs_novos.append(resp["result"]["content"][0]["data"]["hash_uif"])
    print(f"6 UIFs criadas pela tool create_uif (primeira: {hs_novos[0][:12]}…)")
    for i in range(6):
        for j in range(i + 1, 6):
            _silencioso(
                "deposit_trail",
                {
                    "origem": hs_novos[i],
                    "destino": hs_novos[j],
                    "tipo_relacao": "liga",
                    "peso": 1.0,
                },
            )
    print("15 rastros depositados: a terceira clique (K6) existe.")
    _ferramenta(
        servidor,
        prox(),
        "request_symbol_formation",
        {"serial_simbolo": "simbolo-C", "membros": hs_novos},
    )
    print("Símbolos válidos agora:", sorted(s["serial"] for s in servidor.simbolos_validos()))
    print("Meta-Símbolo continua:", servidor.meta_simbolo is not None)


if __name__ == "__main__":
    main()
