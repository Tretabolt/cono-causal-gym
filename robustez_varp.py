"""Robustez do limiar VarP 0,05 — rascunho, nao enviado ao GitHub.

Pergunta (19/11, manha): o limiar 0,05 foi calibrado so no K6 (meio
geometrico entre um-x10 0,0243 e um-x100 0,1061). Ele generaliza para
outros tamanhos de clique? E qual e o teto de saturacao da VarP em
cada tamanho — o limiar fica perto do teto em algum deles, como
ficou a 0,0009 da morte de A no K6 da geodesica?

Resposta (19/11, tarde — decisao do Dan): NAO generaliza. A saida foi
normalizar a VarP pelo teto: VarPn = VarP / ((n-1)/n^2), limiar unico
0,36 (a razao do K6 preservada). Este script agora imprime as duas
colunas: a VarP bruta com o limiar antigo e a VarPn com o 0,36.

Teste: Kn completo uniforme; um rastro x10; um rastro x100; metade
dos rastros x10. VarP e veredito (ISC=1,00 sempre, entao decide a Var).

Rode: python3 robustez_varp.py (stdlib-only).
"""

import itertools

from cono_gym.grafo import GrafoCausal, UIF
from cono_gym.var_ponderada import (
    LIMIAR_VAR_PONDERADA,
    LIMIAR_VARP_NORMALIZADA,
    teto_varp,
    var_ponderada,
    var_ponderada_normalizada,
)


def kn(n, pesos):
    g = GrafoCausal()
    hs = []
    for i in range(n):
        u = UIF(f"K{i}", "Executor", "S")
        g.adicionar_uif(u)
        hs.append(u.hash_uif)
    for (i, j), peso in zip(itertools.combinations(range(n), 2), pesos):
        g.depositar_rastro(hs[i], hs[j], "CAUSA", peso=peso)
    return g


def linha(n, pesos):
    g = GrafoCausal()
    hs = []
    for i in range(n):
        u = UIF(f"K{i}", "Executor", "S")
        g.adicionar_uif(u)
        hs.append(u.hash_uif)
    m = n * (n - 1) // 2
    return g, m


def main():
    print(f"Limiar VarP v0.1: {LIMIAR_VAR_PONDERADA} | Limiar VarPn: {LIMIAR_VARP_NORMALIZADA}")
    print("== Kn: uniforme | um x10 | um x100 | metade x10 (VarP / VarPn) ==")
    for n in [4, 5, 6, 7, 8, 10]:
        m = n * (n - 1) // 2
        casos = {
            "uniforme": [1] * m,
            "um x10": [10] + [1] * (m - 1),
            "um x100": [100] + [1] * (m - 1),
            "um x1000": [1000] + [1] * (m - 1),
            "metade x10": [10] * (m // 2) + [1] * (m - m // 2),
        }
        out = []
        for nome, pesos in casos.items():
            g = kn(n, pesos)
            v = var_ponderada(g)
            vn = var_ponderada_normalizada(g)
            marca = "SIMB" if v <= LIMIAR_VAR_PONDERADA else "MORTO"
            marcan = "SIMB" if vn <= LIMIAR_VARP_NORMALIZADA else "MORTO"
            out.append(f"{nome}={v:.4f}/{vn:.3f} ({marca}/{marcan})")
        print(f"K{n} (m={m}): " + " | ".join(out))

    print()
    print("== teto: um rastro -> infinito (aprox. x1e6) vs (n-1)/n^2 ==")
    for n in [4, 5, 6, 8, 10]:
        m = n * (n - 1) // 2
        v = var_ponderada(kn(n, [10**6] + [1] * (m - 1)))
        print(f"K{n}: VarP teto ~= {v:.4f} | (n-1)/n^2 = {teto_varp(n):.4f}")


if __name__ == "__main__":
    main()
