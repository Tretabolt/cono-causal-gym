"""Espectro de Laplace normalizado e emergência de Símbolo.

Um cluster vira Símbolo quando ISC_Local >= 0.85 E VarPn <= 0.36,
onde VarPn é a Var ponderada NORMALIZADA (cono_gym/var_ponderada.py):
a variância do espectro do Laplaciano COMBINATORIAL dividido pelo
traço, dividida ainda pelo teto (n-1)/n².

A regra mudou duas vezes: antes era Var(λ) do Laplaciano normalizado
<= 0,25 (cega aos pesos na estrela, hipersensível no K6); em 18/11
virou VarP <= 0,05 (vê os pesos, resposta gradual); em 19/11 virou
VarPn <= 0,36, porque o 0,05 não valia para todo tamanho — um rastro
x10 mata um K4, é tolerado num K6 e some num K10. O 0,36 é a razão do
K6 preservada (0,05/0,1389), então nada muda para o K6.

O que NÃO mudou: o Hash_Símbolo continua calculado sobre o espectro
do Laplaciano NORMALIZADO (a identidade do Símbolo, pela especificação
do Dan), e a var_lambda antiga e a VarP bruta continuam no relatório
como diagnóstico — só não decidem mais nada.

ISC É TOPOLÓGICO POR DECISÃO (19/11, Dan delegou: "me aconselhe e
execute"). O teste de invariância mostrou o ISC em 1,00 sob qualquer
reponderação — invariante porque é cego. A decisão é aceitar isso
como limite conhecido, não como defeito a corrigir: ISC_Local é uma
contagem (arestas válidas / arestas possíveis), e uma medida de
densidade DEVE ser invariante a reponderação — se mudasse com os
pesos, estaria medindo outra coisa. Cada tentativa de ponderar o ISC
ou reproduz a contagem (continua cego) ou vira uma medida disfarçada
de uniformidade — que é exatamente o que a VarPn já mede — ou exige
um corte arbitrário de peso para a validade, sem a correção de
princípio que a Var teve (traço + teto). No gym não existe um acerto
externo como o VAI/FICA da rede-pulsos para definir validade por
ablação (C3), então não há o que ponderar o ISC com. A divisão de
trabalho fica explícita: o ISC vê QUANTA estrutura existe (topologia),
a VarPn vê COMO ela está distribuída (geometria) — juntas, cobrem o
que nenhuma cobre sozinha. Condição de reabertura: se o gym ganhar
um critério externo de acerto, o ISC pode herdar sensibilidade a
peso pela validade C3; o caminho fica aberto, não fechado.

O espectro é calculado em Python puro (método de Jacobi para matrizes
simétricas), sem nenhuma dependência externa — o gym é stdlib-only,
como os outros dois repos.

Cuidado honesto, herdado do MNHI 3.0: ISC = 1.0 sozinho é uma armadilha.
Um grafo completo e estagnado tem ISC 1.0 e Var baixa, mas não aprende
nada. Por isso a emergência aqui é só o primeiro passo: a tensão
diversidade × coerência (pesos log-normais vs homogeneidade) ainda não
está medida neste esqueleto.
"""

from .hasher import hash_simbolo

LIMIAR_ISC = 0.85
LIMIAR_VAR = 0.36  # limiar da VarP NORMALIZADA desde 19/11 (0,05 em 18/11; 0,25 antes)


def _jacobi_autovalores(a, tol=1e-12, max_varreduras=100):
    """Autovalores de uma matriz simétrica pelo método de Jacobi."""
    n = len(a)
    m = [linha[:] for linha in a]
    for _ in range(max_varreduras):
        fora = sum(m[i][j] ** 2 for i in range(n) for j in range(n) if i != j)
        if fora < tol:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                apq = m[p][q]
                if abs(apq) < 1e-15:
                    continue
                app, aqq = m[p][p], m[q][q]
                tau = (aqq - app) / (2 * apq)
                t = (1 if tau >= 0 else -1) / (abs(tau) + (tau * tau + 1) ** 0.5)
                c = 1 / (1 + t * t) ** 0.5
                s = t * c
                for k in range(n):
                    akp, akq = m[k][p], m[k][q]
                    m[k][p] = c * akp - s * akq
                    m[k][q] = s * akp + c * akq
                for k in range(n):
                    apk, aqk = m[p][k], m[q][k]
                    m[p][k] = c * apk - s * aqk
                    m[q][k] = s * apk + c * aqk
    return sorted(m[i][i] for i in range(n))


def laplaciano_normalizado(adj):
    """L = I - D^(-1/2) A D^(-1/2). Nó isolado tem linha zerada."""
    n = len(adj)
    graus = [sum(linha) for linha in adj]
    inv_raiz = [0.0 if g == 0 else 1.0 / g**0.5 for g in graus]
    lap = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                lap[i][j] = 1.0 if graus[i] > 0 else 0.0
            else:
                lap[i][j] = -inv_raiz[i] * adj[i][j] * inv_raiz[j]
    return lap


def espectro(grafo):
    """Espectro ordenado do Laplaciano normalizado do grafo."""
    return _jacobi_autovalores(laplaciano_normalizado(grafo.matriz_adjacencia()))


def isc_local(grafo):
    """Arestas existentes / arestas possíveis."""
    maximo = grafo.max_arestas()
    return grafo.n_arestas() / maximo if maximo else 0.0


def var_lambda(espectro_ordenado):
    """Variância do espectro. Média é sempre 1 num grafo sem nós isolados."""
    n = len(espectro_ordenado)
    media = sum(espectro_ordenado) / n
    return sum((v - media) ** 2 for v in espectro_ordenado) / n


def avaliar_cluster(grafo, serial_simbolo, limiar_isc=LIMIAR_ISC, limiar_var=LIMIAR_VAR):
    """Avalia se o cluster inteiro forma um Símbolo. Retorna o relatório
    completo, com ou sem Símbolo — o NÃO também é resultado.
    Os limiares são parâmetros porque o Meta-Símbolo pode mudá-los por
    geodésica: a auditoria precisa avaliar o mesmo estado sob duas regras.

    Desde 19/11 o veredito usa a VarP NORMALIZADA (VarPn <= limiar_var).
    A var_lambda antiga e a VarP bruta ficam no relatório só como
    diagnóstico. O espectro normalizado continua no relatório porque o
    Hash_Símbolo é calculado sobre ele. O import é adiado porque
    var_ponderada importa deste módulo (ciclo)."""
    from .var_ponderada import (
        espectro_ponderado,
        var_ponderada,
        var_ponderada_normalizada,
    )

    esp = espectro(grafo)
    isc = isc_local(grafo)
    var_antiga = var_lambda(esp)
    esp_pond = espectro_ponderado(grafo)
    var = var_ponderada(grafo)
    varn = var_ponderada_normalizada(grafo)
    eh_simbolo = isc >= limiar_isc and varn <= limiar_var
    return {
        "serial": serial_simbolo,
        "nos": grafo.n_nos(),
        "arestas": grafo.n_arestas(),
        "isc_local": isc,
        "var_lambda": var_antiga,
        "var_ponderada": var,
        "var_ponderada_normalizada": varn,
        "espectro": esp,
        "espectro_ponderado": esp_pond,
        "simbolo": eh_simbolo,
        "hash_simbolo": hash_simbolo(serial_simbolo, esp) if eh_simbolo else None,
    }
