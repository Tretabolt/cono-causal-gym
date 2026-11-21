"""Invariância aplicada a ISC e Var — rascunho, não enviado ao GitHub.

Meta "Invariância como critério": uma quantidade é real só se sobrevive
à troca de representação, com o peso certo corrigindo a distorção.
Aqui a troca de representação é a reponderação dos rastros (e a
reordenação das UIFs) no gym — o grafo continua o mesmo, só os pesos
e os rótulos mudam.

Pergunta: ISC_Local e Var(λ) sobrevivem? Resultado (rodado 18/11):

  * Estrela K1,3: ISC 0,50 e Var 0,5000 em TODAS as ponderações —
    [1,1,1], [10,10,10], [10,1,1], [1,0.1,0.1], [100,1,1].
    O espectro do Laplaciano normalizado de uma estrela é sempre
    [0, 1, 1, 2], independente dos pesos. As duas métricas são
    completamente cegas aos pesos na estrela — confirma o achado
    de 14/11, agora no código do gym.
  * K6: escala uniforme (x5) não muda nada (ISC 1,00, Var 0,20).
    Mas UM rastro x10, resto 1: Var 0,20 -> 0,2882, cruzando o
    limiar 0,25 — o K6 deixa de ser Símbolo só por reponderar,
    mesma topologia, mesmas arestas. ISC fica 1,00 (cego).
  * Reordenação das UIFs: espectro idêntico nas 3 ordens testadas.

Leitura honesta: ISC sobrevive a toda reponderação porque é cego
(conta arestas, não pesos) — invariante, mas sem informação sobre
pesos. Var sobrevive à escala uniforme, mas NÃO à reponderação
relativa no K6 — e é cego na estrela. Nenhuma das duas é um
invariante limpo; o ponto cego depende da topologia.

Rode: python3 invariancia_isc_var.py (stdlib-only, sem dependências).
"""

import itertools

from cono_gym.espectro import espectro, isc_local, var_lambda
from cono_gym.grafo import GrafoCausal, UIF


def estrela(pesos, ordem=("C", "A", "B", "D")):
    """K1,3: centro C ligado a A, B, D com os pesos dados."""
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
    """K6 com os 15 pesos dados, na ordem das combinações."""
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
    esp = espectro(grafo)
    print(
        f"{nome}: ISC={isc_local(grafo):.3f} "
        f"Var={var_lambda(esp):.4f} "
        f"espectro={[round(x, 3) for x in esp]}"
    )


def main():
    print("== estrela K1,3: reponderacao ==")
    for nome, pesos in [
        ("[1, 1, 1]", [1, 1, 1]),
        ("x10 uniforme", [10, 10, 10]),
        ("[10, 1, 1]", [10, 1, 1]),
        ("[1, 0.1, 0.1]", [1, 0.1, 0.1]),
        ("[100, 1, 1]", [100, 1, 1]),
    ]:
        relatorio(f"estrela {nome}", estrela(pesos))

    print("== estrela: reordenacao das UIFs (pesos 7, 2, 0.5) ==")
    for ordem in [["C", "A", "B", "D"], ["A", "B", "D", "C"], ["D", "C", "B", "A"]]:
        relatorio(f"ordem {ordem}", estrela([7, 2, 0.5], ordem=ordem))

    print("== K6: reponderacao ==")
    relatorio("K6 uniforme", k6([1] * 15))
    relatorio("K6 x5 uniforme", k6([5] * 15))
    relatorio("K6 um peso 10, resto 1", k6([10] + [1] * 14))

    print()
    print("Conclusao: ISC cego a pesos em tudo; Var cega na estrela,")
    print("sensivel a reponderacao relativa no K6 (0,20 -> 0,288,")
    print("cruza o limiar 0,25 e o K6 deixa de ser Simbolo).")
    print()
    print("Leitura adotada em 19/11 (decisao do Dan, por delegacao):")
    print("a Var foi corrigida (VarP, depois VarPn <= 0,36); o ISC fica")
    print("topologico por decisao — uma contagem de arestas DEVE ser")
    print("invariante a reponderacao, e o peso vive na VarPn. ISC ve")
    print("QUANTA estrutura existe; VarPn ve COMO ela se distribui.")


if __name__ == "__main__":
    main()
