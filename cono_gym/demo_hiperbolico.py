"""Demo das coordenadas hiperbólicas do CONO Causal Gym.

O lugar que faltava: cada UIF ganha um ponto no Disco de Poincaré,
aprendido do grafo por minimização de estresse. Mostra:

1. A estrela: folha-folha ~1,76× folha-centro — a hierarquia aparece
   na geometria.
2. Duas cliques K6: cada uma vira uma bola hiperbólica apertada, e a
   separação entre elas é mais de 3× o raio.
3. O anel: perto da borda do disco, as distâncias entre os pontos se
   uniformizam (razão máx/mín cai).

Roda com: python3 -m cono_gym.demo_hiperbolico
"""

import math

from cono_gym.episodios import _chamar
from cono_gym.grafo import GrafoCausal, UIF
from cono_gym.hiperbolico import distancia_poincare
from cono_gym.mcp_server import (
    ConoGymServer,
    construir_cenario_duas_cliques,
)


def _estrela():
    grafo = GrafoCausal()
    centro = UIF("c", "x", "c")
    grafo.adicionar_uif(centro)
    folhas = []
    for i in range(3):
        folha = UIF(f"f{i}", "x", "f")
        grafo.adicionar_uif(folha)
        folhas.append(folha.hash_uif)
        grafo.depositar_rastro(centro.hash_uif, folha.hash_uif, "liga", 1.0)
    return grafo, centro.hash_uif, folhas


def main():
    print("== Coordenadas hiperbólicas: o lugar das UIFs ==\n")

    print("-- 1. A estrela --")
    grafo, centro, folhas = _estrela()
    servidor = ConoGymServer(grafo)
    embutido = _chamar(servidor, "embed_hyperbolic", {})
    pontos = embutido["coordenadas"]
    d_fc = [
        distancia_poincare(pontos[centro], pontos[f]) for f in folhas
    ]
    d_ff = distancia_poincare(pontos[folhas[0]], pontos[folhas[1]])
    print(f"  stress: {embutido['stress']}")
    print(f"  folha-centro: {[round(d, 3) for d in d_fc]}")
    print(f"  folha-folha: {round(d_ff, 3)} (razão {round(d_ff / max(d_fc), 2)}×)")

    print("\n-- 2. Duas cliques K6 --")
    grafo2, grupos = construir_cenario_duas_cliques()
    servidor2 = ConoGymServer(grafo2)
    embutido2 = _chamar(servidor2, "embed_hyperbolic", {})
    print(f"  stress: {embutido2['stress']}")
    medicao = _chamar(
        servidor2,
        "measure_geometry",
        {"clusters": {"A": grupos["A"], "B": grupos["B"]}},
    )
    for nome, m in medicao["clusters"].items():
        print(
            f"  clique {nome}: centro {m['centro']}, raio {m['raio']}, n={m['n']}"
        )
    for par, s in medicao["separacoes"].items():
        print(
            f"  separação {par}: {s['separacao']} "
            f"(razão sep/raio {s['razao_sep_raio']}×)"
        )

    print("\n-- 3. O anel perto da borda --")

    def razao(r, n=6):
        pts = [
            (r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n))
            for k in range(n)
        ]
        dists = [
            distancia_poincare(pts[i], pts[j])
            for i in range(n)
            for j in range(i + 1, n)
        ]
        return max(dists) / min(dists)

    print(f"  razão máx/mín: r=0,1 -> {round(razao(0.1), 2)}; r=0,9 -> {round(razao(0.9), 2)}")


if __name__ == "__main__":
    main()
