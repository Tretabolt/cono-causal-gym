"""Experimento da Var ponderada — rascunho, não enviado ao GitHub.

Desenho (18/11): VarP = Var(λ_comb / tr(L)), Laplaciano combinatorial
normalizado pelo traço. Invariante a escala uniforme, sensível a
reponderação relativa.

Resultado: a cegueira da estrela acabou e o K6 não morre mais com um
só rastro x10. Limiar v0.1 proposto: 0,05 (meio geométrico entre
um-x10 0,0243 e um-x100 0,1061).

Rode: python3 var_ponderada_experimento.py (stdlib-only).
"""

import itertools

from cono_gym.espectro import avaliar_cluster
from cono_gym.grafo import GrafoCausal, UIF
from cono_gym.var_ponderada import (
    LIMIAR_VAR_PONDERADA,
    LIMIAR_VARP_NORMALIZADA,
    avaliar_cluster_ponderado,
    espectro_ponderado,
    var_ponderada,
    var_ponderada_normalizada,
)


def estrela(pesos, ordem=("C", "A", "B", "D")):
    g = GrafoCausal()
    hs = {}
    for nome in ordem:
        u = UIF(nome, "Executor", "S")
        g.adicionar_uif(u)
        hs[nome] = u.hash_uif
    for folha, peso in zip(("A", "B", "D"), pesos):
        g.depositar_rastro(hs["C"], hs[folha], "CAUSA", peso=peso)
    return g


def k6(pesos):
    g = GrafoCausal()
    hs = []
    for i in range(6):
        u = UIF(f"K{i}", "Executor", "S")
        g.adicionar_uif(u)
        hs.append(u.hash_uif)
    for (i, j), peso in zip(itertools.combinations(range(6), 2), pesos):
        g.depositar_rastro(hs[i], hs[j], "CAUSA", peso=peso)
    return g


def relatorio(nome, grafo):
    velha = avaliar_cluster(grafo, "x")
    nova = avaliar_cluster_ponderado(grafo, "x")
    print(
        f"{nome}: Var_antiga={velha['var_lambda']:.4f} "
        f"({'Simbolo' if velha['simbolo'] else 'NAO'}) | "
        f"VarP={nova['var_ponderada']:.4f} "
        f"VarPn={nova['var_ponderada_normalizada']:.3f} "
        f"({'Simbolo' if nova['simbolo'] else 'NAO'})"
    )


def main():
    print("== estrela K1,3: a VarP ve os pesos? ==")
    for nome, pesos in [
        ("[1, 1, 1]", [1, 1, 1]),
        ("x10 uniforme", [10, 10, 10]),
        ("[10, 1, 1]", [10, 1, 1]),
        ("[1, 0.1, 0.1]", [1, 0.1, 0.1]),
        ("[100, 1, 1]", [100, 1, 1]),
        ("[5, 3, 1]", [5, 3, 1]),
    ]:
        relatorio(f"estrela {nome}", estrela(pesos))

    print("== estrela: reordenacao (pesos 7, 2, 0.5) ==")
    for ordem in [["C", "A", "B", "D"], ["A", "B", "D", "C"], ["D", "C", "B", "A"]]:
        g = estrela([7, 2, 0.5], ordem=ordem)
        print(f"ordem {ordem}: VarP={var_ponderada(g):.4f}")

    print("== K6: um rastro pesado mata o Simbolo? ==")
    for nome, pesos in [
        ("uniforme", [1] * 15),
        ("x5 uniforme", [5] * 15),
        ("um x2", [2] + [1] * 14),
        ("um x5", [5] + [1] * 14),
        ("um x10", [10] + [1] * 14),
        ("um x100", [100] + [1] * 14),
        ("metade x10", [10] * 7 + [1] * 8),
    ]:
        relatorio(f"K6 {nome}", k6(pesos))

    print()
    print(f"Limiar VarP v0.1: {LIMIAR_VAR_PONDERADA} (meio geometrico entre")
    print("um-x10 0,0243 e um-x100 0,1061). A Var antiga matava o K6 com")
    print("um x10; a VarP segura ate x100. A estrela continua fora do")
    print("Simbolo pelo ISC, mas agora a Var ao menos a enxerga.")
    print(f"Normalizacao (19/11): VarPn = VarP / teto(n), limiar {LIMIAR_VARP_NORMALIZADA} —")
    print("um unico limiar para todo tamanho (a razao do K6 preservada).")


if __name__ == "__main__":
    main()
