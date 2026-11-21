"""Var ponderada — uma Var(λ) que enxerga os pesos.

Problema (18/11, teste de invariância): a Var do Laplaciano
normalizado é cega aos pesos na estrela — espectro sempre [0, 1, 1, 2]
— e hipersensível no K6, onde UM rastro x10 já empurra a Var de 0,20
para 0,2882 e mata o Símbolo. Nenhuma das duas é um invariante limpo.

Desenho: usar o Laplaciano COMBINATORIAL L = D - W, cujo espectro
escala com os pesos, e normalizar pelo traço (soma dos autovalores
= 2 x peso total). A divisão pelo traço tira a escala uniforme —
multiplicar todos os pesos por 5 não muda nada — mas mantém a
reponderação RELATIVA, que é a mudança real na distribuição causal.

    VarP = Var(λ_comb / tr(L))

Propriedades verificadas no experimento (var_ponderada_experimento.py):

  * Estrela: [1,1,1] -> 0,0625; x10 uniforme -> 0,0625 (invariante
    a escala); [10,1,1] -> 0,1328; [100,1,1] -> 0,1803. A cegueira
    da estrela acabou: a VarP cresce com a assimetria relativa.
  * K6: uniforme -> 0,0056; x5 uniforme -> 0,0056; um x2 -> 0,0061;
    um x5 -> 0,0115; um x10 -> 0,0243; um x100 -> 0,1061. Resposta
    suave e gradual — um rastro 10x mais pesado NÃO mata o Símbolo,
    ao contrário da Var antiga.
  * Reordenação das UIFs: VarP idêntica (o espectro é invariante
    por permutação por construção).

Limiar v0.1: LIMIAR_VAR_PONDERADA = 0,05. Calibração: é o meio
geométrico entre um-x10 (0,0243, ainda Símbolo) e um-x100 (0,1061,
não Símbolo) — sqrt(0,0243 x 0,1061) ≈ 0,051. Não é teorema, é
escolha v0.1, como o Gini 0,30.

NORMALIZAÇÃO (19/11, por decisão do Dan): o 0,05 não vale para todo
tamanho — um rastro x10 mata um K4 (0,0808), é tolerado num K6
(0,0243) e some num K10 (0,0036). A correção, como o r da integral
cilíndrica, pertence à QUANTIDADE, não ao limiar:

    VarPn = VarP / teto(n),  teto(n) = (n-1)/n²

O teto é o máximo possível da VarP num grafo com n nós: os
autovalores do Laplaciano combinatorial normalizado pelo traço vivem
em [0, 1], somam 1, e pelo menos um é 0 (L·1 = 0) — a variância é
máxima quando toda a massa está num só autovalor, e vale (n-1)/n².
O máximo é atingido no limite de um rastro dominante (peso → ∞).
Verificado numericamente em 19/11 (robustez_varp.py): K4 0,1875, K5
0,1600, K6 0,1389, K8 0,1094, K10 0,0900 — todos batem com (n-1)/n²,
e a base uniforme bate com 1/(n²(n-1)). A VarPn vive em [0, 1] e é
livre de tamanho; o limiar único é 0,36 — a razão do K6 preservada
(0,05/0,1389). A regra de emergência usa a VarPn desde 19/11.

Limites honestos:

  * A estrela continua nunca sendo Símbolo — pelo ISC (0,50 < 0,85),
    não pela Var. A VarP vê os pesos lá, mas não a salva.
  * A VarP responde mais à concentração num ÚNICO rastro do que a
    uma assimetria espalhada: metade dos rastros x10 dá 0,0160,
    menos que um só x10 (0,0243). Um autovalor dominante pesa mais
    que vários moderados.
  * O limiar 0,25 da Var antiga NÃO se transfere — a escala é outra
    (K6 uniforme: 0,0056, não 0,20). Quem adotar a VarP adota o 0,05.
  * A regra de emergência do gym usa a VarP NORMALIZADA desde 19/11,
    por decisão do Dan: avaliar_cluster decide por VarPn <= 0,36.
    A avaliar_cluster_ponderado continua existindo e concorda com ela.
"""

from .espectro import LIMIAR_ISC, _jacobi_autovalores, espectro, var_lambda
from .hasher import hash_simbolo

LIMIAR_VAR_PONDERADA = 0.05
LIMIAR_VARP_NORMALIZADA = 0.36  # 0,05/0,1389: a razão do K6 preservada


def laplaciano_combinatorial(adj):
    """L = D - W. O espectro escala com os pesos — por isso o passo
    seguinte normaliza pelo traço."""
    n = len(adj)
    lap = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                lap[i][j] = sum(adj[i])
            else:
                lap[i][j] = -adj[i][j]
    return lap


def espectro_ponderado(grafo):
    """Espectro do Laplaciano combinatorial, dividido pelo traço.
    Invariante a escala uniforme, sensível a reponderação relativa."""
    esp = _jacobi_autovalores(laplaciano_combinatorial(grafo.matriz_adjacencia()))
    traco = sum(esp)
    if traco == 0:
        return esp
    return [v / traco for v in esp]


def var_ponderada(grafo):
    """Variância do espectro ponderado. Mesma convenção da Var antiga
    (todos os autovalores, inclusive o 0), outro Laplaciano."""
    return var_lambda(espectro_ponderado(grafo))


def teto_varp(n_nos):
    """Teto da VarP num grafo com n nós: (n-1)/n². É o máximo
    possível — ver o argumento no docstring do módulo. n <= 1 não
    tem espectro com o que variar: teto 0."""
    n = n_nos
    if n <= 1:
        return 0.0
    return (n - 1) / (n * n)


def var_ponderada_normalizada(grafo):
    """VarP dividida pelo teto: vive em [0, 1] e é livre de tamanho.
    Um único limiar (0,36) vale para qualquer n. n <= 1: 0,0."""
    teto = teto_varp(grafo.n_nos())
    if teto == 0:
        return 0.0
    return var_ponderada(grafo) / teto


def avaliar_cluster_ponderado(grafo, serial_simbolo, limiar_isc=LIMIAR_ISC,
                              limiar_var_ponderada=LIMIAR_VARP_NORMALIZADA):
    """Avaliação pela VarP NORMALIZADA. Desde 19/11 ela concorda com
    avaliar_cluster — fica aqui como a forma explícita de avaliar pela
    VarPn, com o limiar próprio nomeado. A VarP bruta continua no
    relatório como diagnóstico."""
    esp = espectro_ponderado(grafo)
    isc = grafo.n_arestas() / grafo.max_arestas() if grafo.max_arestas() else 0.0
    var = var_lambda(esp)
    varn = var_ponderada_normalizada(grafo)
    eh_simbolo = isc >= limiar_isc and varn <= limiar_var_ponderada
    return {
        "serial": serial_simbolo,
        "nos": grafo.n_nos(),
        "arestas": grafo.n_arestas(),
        "isc_local": isc,
        "var_ponderada": var,
        "var_ponderada_normalizada": varn,
        "espectro_ponderado": esp,
        "simbolo": eh_simbolo,
        # O Hash_Símbolo é sobre o espectro NORMALIZADO, como em
        # avaliar_cluster — a identidade não muda com a Var.
        "hash_simbolo": hash_simbolo(serial_simbolo, espectro(grafo))
        if eh_simbolo
        else None,
    }
