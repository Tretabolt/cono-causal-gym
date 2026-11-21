"""Demo do Espaço J do CONO Causal Gym.

Mostra as 5 propriedades do análogo funcional do J-space, sobre o
mesmo estado da geodésica (3 cliques K6, A morto perto da borda com
VarPn 0,3662, B e C válidos, Meta-Símbolo formado):

1. Pequeno e seletivo — capacidade 3, a 4ª direção despeja a mais antiga.
2. Relatável — o Meta-Símbolo diz o que está segurando.
3. Segurável — a direção persiste até ser editada, despejada ou limpa.
4. Usável no raciocínio — a direção segurada vira geodésica auditada.
5. Editável e causal — o teste da troca: editar o `para` de 0,40 para
   0,03 transforma a geodésica aprovada numa rejeitada.

E o fecho: o Meta-Símbolo propondo sozinho — `tentar_auto_proposta`
gera a direção das medições, segura, propõe e audita, sem ninguém de
fora ditar a proposta.

Roda com: python3 -m cono_gym.demo_workspace
"""

from cono_gym.episodios import _chamar
from cono_gym.mcp_server import ConoGymServer, construir_cenario_tres_cliques


def _estado():
    grafo, grupos = construir_cenario_tres_cliques()
    servidor = ConoGymServer(grafo)
    for nome in ("A", "B", "C"):
        _chamar(
            servidor,
            "request_symbol_formation",
            {"serial_simbolo": f"simbolo-{nome}", "membros": grupos[nome]},
        )
    for k in range(3):
        _chamar(
            servidor,
            "deposit_trail",
            {
                "origem": grupos["A"][0],
                "destino": grupos["A"][1 + k],
                "tipo_relacao": "pesado",
                "peso": 100.0,
            },
        )
    assert servidor.meta_simbolo is not None
    return servidor


def _segurar(servidor, regra, de, para, motivo):
    return _chamar(
        servidor,
        "hold_direction",
        {"tipo": "direcao", "regra": regra, "de": de, "para": para, "motivo": motivo},
    )


def main():
    print("== Espaço J: o workspace do Meta-Símbolo ==\n")
    servidor = _estado()
    print("Meta-Símbolo formado; A morto perto da borda (VarPn 0,3662).")

    print("\n-- 1. Pequeno e seletivo (capacidade 3) --")
    for i, para in enumerate((0.40, 0.41, 0.42, 0.43)):
        r = _segurar(servidor, "limiar_var", 0.36, para, f"direção {i + 1}")
        despejado = r["despejado"]
        print(
            f"segurada direção para={para}"
            + (
                f" — despejada a mais antiga (para={despejado['para']})"
                if despejado
                else ""
            )
        )

    print("\n-- 2. Relatável --")
    relato = _chamar(servidor, "report_workspace")
    for c in relato["conteudos"]:
        print(f"  id {c['id']}: {c['regra']} {c['de']} -> {c['para']} ({c['motivo']})")

    print("\n-- 3. Segurável + 4. Usável no raciocínio --")
    print("A direção segurada vira geodésica e é auditada:")
    proposta = _chamar(
        servidor,
        "propose_geodesic",
        {"payload": {"do_workspace": True, "direcao_id": 4}},
    )
    auditada = _chamar(
        servidor, "audit_geodesic", {"proposta_id": proposta["id"]}
    )
    print(f"  veredito: {auditada['auditoria']['veredito']}")
    print(f"  regras vigentes agora: {servidor.regras}")

    print("\n-- 5. Editável e causal: o teste da troca --")
    servidor2 = _estado()
    segurado = _segurar(servidor2, "limiar_var", 0.36, 0.40, "ressuscitar A")
    direcao_id = segurado["segurado"]["id"]
    _chamar(
        servidor2,
        "edit_direction",
        {"direcao_id": direcao_id, "mudancas": {"para": 0.03}},
    )
    print("  editado o `para` de 0,40 para 0,03 (mesma direção, outro alvo)")
    proposta2 = _chamar(
        servidor2,
        "propose_geodesic",
        {"payload": {"do_workspace": True, "direcao_id": direcao_id}},
    )
    auditada2 = _chamar(
        servidor2, "audit_geodesic", {"proposta_id": proposta2["id"]}
    )
    print(f"  veredito: {auditada2['auditoria']['veredito']}")
    print(f"  regras vigentes agora: {servidor2.regras}")

    print("\n-- O Meta-Símbolo propondo sozinho --")
    servidor3 = _estado()
    resultado = servidor3.tentar_auto_proposta()
    print(f"  direção gerada das medições, segurada e auditada:")
    print(f"  veredito: {resultado['veredito']}")
    print(f"  regras vigentes agora: {servidor3.regras}")


if __name__ == "__main__":
    main()
