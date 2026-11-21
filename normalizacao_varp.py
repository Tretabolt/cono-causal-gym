"""Normalizacao da VarP pelo teto — rascunho, nao enviado ao GitHub.

Pergunta (19/11, manha, continuacao do robustez_varp.py): o limiar
0,05 foi calibrado no K6 e nao generaliza — um rastro x10 mata um K4
(0,0808), e tolerado num K6 (0,0243) e some num K10 (0,0036). Existe
uma normalizacao por tamanho que deixe o veredito igual para o mesmo
exagero, seja qual for o tamanho do clique?

Candidato: r = VarP / teto(n), onde teto(n) e a VarP quando UM rastro
domina tudo (peso -> infinito). O teto tem forma fechada:

    teto(n) = (n-1) / n^2

verificada aqui contra x1e6 (diferenca ~1e-6) em K4..K10 — e, surpresa,
o mesmo teto vale para estrela, caminho e ciclo: em todas, um rastro
x1e6 da r = 1,000. Ou seja, r esta em [0, 1] e r = 1 significa "um
rastro possui tudo". O limiar vira fracao do teto: 0,05 / teto(6) =
0,36. Para K6, r <= 0,36 e EXATAMENTE VarP <= 0,05 — todos os
resultados do gym em K6 ficam intactos por construcao; a mudanca so
age em n != 6.

O que o teste mostra:

  * Participacao fixa de UM rastro (s = peso do rastro / peso total):
    r e quase constante entre tamanhos — s=0,5 -> r~0,25; s=0,667 ->
    r~0,43-0,44; s=0,8 -> r~0,63; s=0,9 -> r~0,80. O veredito sob
    r <= 0,36 passa a ser o mesmo em K4..K10 para o mesmo s.
  * O limiar 0,36 corresponde a um rastro com ~60,6% do peso total.
    E o meio geometrico da calibracao original em r: sqrt(0,175 x
    0,764) = 0,366 — o 0,36 e a mesma calibracao, reescrita.
  * Geodesica: os tres vereditos sobrevivem — morte de A (VarP
    0,0509 -> r 0,3665, margem 0,0065 em vez de 0,0009); aprovado
    0,06 -> r 0,432; rejeitado 0,005 -> r 0,036 (K6 uniforme r 0,040).
  * Limite honesto: a normalizacao conserta o caso de UM rastro
    dominante, nao a assimetria espalhada. Metade dos rastros x10
    continua dependendo do tamanho: r = 0,260 (K4) -> 0,048 (K10).
    A VarP responde a concentracao num unico rastro; espalhar o
    exagero por metade das arestas continua sendo "barato" para ela.

Nada aqui troca a regra adotada (ISC >= 0,85 e VarP <= 0,05). E uma
proposta a decidir: adotar r <= 0,36 no lugar de VarP <= 0,05.

Rode: python3 normalizacao_varp.py (stdlib-only).
"""

import itertools

from cono_gym.grafo import GrafoCausal, UIF
from cono_gym.var_ponderada import var_ponderada

LIMIAR_R = 0.36  # 0,05 / teto(6); para K6 equivale a VarP <= 0,05


def teto(n):
    """VarP maxima com um rastro dominante: (n-1)/n^2."""
    return (n - 1) / n ** 2


def r_varp(grafo):
    return var_ponderada(grafo) / teto(grafo.n_nos())


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


def grafo_topologia(n, arestas, pesos):
    g = GrafoCausal()
    hs = []
    for i in range(n):
        u = UIF(f"N{i}", "Executor", "S")
        g.adicionar_uif(u)
        hs.append(u.hash_uif)
    for (i, j), peso in zip(arestas, pesos):
        g.depositar_rastro(hs[i], hs[j], "CAUSA", peso=peso)
    return g


def main():
    print("== teto (n-1)/n^2 verificado contra um rastro x1e6 ==")
    for n in [4, 5, 6, 7, 8, 10]:
        m = n * (n - 1) // 2
        v = var_ponderada(kn(n, [10 ** 6] + [1] * (m - 1)))
        print(f"K{n}: teto={teto(n):.4f} x1e6={v:.4f} dif={abs(v - teto(n)):.1e}")

    print()
    print("== participacao fixa de UM rastro (s = peso/total) ==")
    for s in [0.5, 0.667, 0.8, 0.9]:
        partes = []
        for n in [4, 5, 6, 8, 10]:
            m = n * (n - 1) // 2
            w = s * (m - 1) / (1 - s)
            r = r_varp(kn(n, [w] + [1] * (m - 1)))
            marca = "SIMB" if r <= LIMIAR_R else "MORTO"
            partes.append(f"K{n}: r={r:.3f} ({marca})")
        print(f"s={s}: " + " | ".join(partes))

    print()
    print("== teto em outras topologias (um rastro x1e6 -> r) ==")
    for nome, fn in [
        ("estrela", lambda n: [(0, i) for i in range(1, n)]),
        ("caminho", lambda n: [(i, i + 1) for i in range(n - 1)]),
        ("ciclo", lambda n: [(i, (i + 1) % n) for i in range(n)]),
    ]:
        vals = []
        for n in [4, 6, 10]:
            ar = fn(n)
            r = r_varp(grafo_topologia(n, ar, [10 ** 6] + [1] * (len(ar) - 1)))
            vals.append(f"n={n}: r={r:.3f}")
        print(f"{nome}: " + " | ".join(vals))

    print()
    print("== geodesica sob r (K6, teto 0,1389) ==")
    print(f"morte de A: VarP 0,0509 -> r={0.0509 / teto(6):.4f} "
          f"(margem {0.0509 / teto(6) - LIMIAR_R:+.4f} do limiar 0,36)")
    print(f"aprovado: 0,06 -> r={0.06 / teto(6):.4f} | "
          f"rejeitado: 0,005 -> r={0.005 / teto(6):.4f} "
          f"(K6 uniforme r={0.0056 / teto(6):.4f})")

    print()
    print("== limite honesto: metade dos rastros x10 ainda depende de n ==")
    for n in [4, 5, 6, 8, 10]:
        m = n * (n - 1) // 2
        r = r_varp(kn(n, [10] * (m // 2) + [1] * (m - m // 2)))
        print(f"K{n}: r={r:.3f}")


if __name__ == "__main__":
    main()
