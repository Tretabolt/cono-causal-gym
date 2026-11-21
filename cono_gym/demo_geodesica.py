"""Demo da auditoria da geodésica: três propostas, três vereditos.

Cada caso roda sobre um estado fresco e idêntico: 3 cliques K6 (A, B,
C) com uma única ponte B-C. Os 3 Símbolos se formam válidos (nesse
momento H_causal = 1,585 bits, log2 3); depois 3 rastros peso 100
dentro de A empurram a VarPn para 0,3662 e o Símbolo A morre — mas
fica no registro. A tensão aparece (Gini alto) e o Meta-Símbolo se
forma a partir de B e C (H_causal = 1,0 bit). A versão antiga deste
parágrafo dizia "H_causal = 0" — resto da definição invertida, quando
H media concentração de pesos; corrigido em 20/11.

Peso 100, não 8: com a VarP adotada (18/11), matar um K6 por dentro
exige assimetria extrema — a VarP satura perto de 0,053 mesmo com
pesos maiores. O limiar 0,36 fica a 0,0062 da morte de A: margem
fina, registrada como tal.

1. limiar_var 0.36 -> 0.40: APROVADA. O Símbolo A ressuscita — e as
   regras do servidor mudam de verdade.
2. limiar_isc 0.85 -> 0.25: SUSPEITA (critério B). O grafo inteiro
   (ISC 0,301, VarPn 0,339) viraria um mega-símbolo com 100% do peso,
   engolindo A, B e C.
3. limiar_var 0.36 -> 0.03: REJEITADA. Colapso: nenhum Símbolo
   sobrevive (K6 uniforme tem VarPn 0,0403 > 0,03).

Uso: python3 -m cono_gym.demo_geodesica
"""

from .episodios import _chamar
from .espectro import avaliar_cluster
from .mcp_server import ConoGymServer, construir_cenario_tres_cliques


def _estado_tres_cliques():
    grafo, grupos = construir_cenario_tres_cliques()
    servidor = ConoGymServer(grafo)
    for nome in ("A", "B", "C"):
        _chamar(
            servidor,
            "request_symbol_formation",
            {"serial_simbolo": f"simbolo-{nome}", "membros": grupos[nome]},
        )
    # 3 rastros peso 100 dentro de A: ele morre (VarP 0,0509), a tensão
    # aparece e o Meta-Símbolo se forma a partir de B e C.
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
    return servidor, grafo, grupos


def _caso(titulo, payload):
    print(f"--- {titulo} ---")
    servidor, grafo, grupos = _estado_tres_cliques()
    proposta = _chamar(servidor, "propose_geodesic", {"payload": payload})
    auditada = _chamar(servidor, "audit_geodesic", {"proposta_id": proposta["id"]})
    auditoria = auditada["auditoria"]
    print(f"veredito: {auditoria['veredito']}")
    print(f"motivo: {auditoria['motivo']}")
    print(
        f"válidos antes: {auditoria['validos_antiga']} -> depois: {auditoria['validos_nova']}"
    )
    print(
        f"tensão antes: {auditoria['tensao_antiga']} -> depois: {auditoria['tensao_nova']}"
    )
    print(
        f"maior share: {auditoria['maior_share_antiga']} -> {auditoria['maior_share_nova']}"
    )
    def _fmt(v):
        return f"{v:.3f}" if v is not None else "—"

    print(
        f"JSD p/ tirania: {_fmt(auditoria['jsd_antiga'])} -> {_fmt(auditoria['jsd_nova'])} "
        f"(equilibrada: {_fmt(auditoria['jsd_uniforme_nova'])})"
    )
    print(f"regras vigentes agora: {servidor.regras}")
    if auditoria["veredito"] == "aprovada":
        rel_a = avaliar_cluster(
            grafo.subgrafo(grupos["A"]),
            "simbolo-A",
            limiar_isc=servidor.regras["limiar_isc"],
            limiar_var=servidor.regras["limiar_var"],
        )
        print(f"Símbolo A depois da regra nova: símbolo={rel_a['simbolo']} (VarPn {rel_a['var_ponderada_normalizada']:.4f})")
    print()
    return auditoria


def main():
    _caso(
        "1. limiar_var 0.36 -> 0.40 (ressuscitar o Símbolo A)",
        {
            "mudanca_regra": "limiar_var 0.36 -> 0.40",
            "efeito_esperado": "o Símbolo A volta a valer",
            "regra": "limiar_var",
            "de": 0.36,
            "para": 0.40,
        },
    )
    _caso(
        "2. limiar_isc 0.85 -> 0.25 (o grafo inteiro vira Símbolo)",
        {
            "mudanca_regra": "limiar_isc 0.85 -> 0.25",
            "efeito_esperado": "mais Símbolos se formam",
            "regra": "limiar_isc",
            "de": 0.85,
            "para": 0.25,
        },
    )
    _caso(
        "3. limiar_var 0.36 -> 0.03 (apertar o limite)",
        {
            "mudanca_regra": "limiar_var 0.36 -> 0.03",
            "efeito_esperado": "só os Símbolos mais coerentes sobrevivem",
            "regra": "limiar_var",
            "de": 0.36,
            "para": 0.03,
        },
    )


if __name__ == "__main__":
    main()
