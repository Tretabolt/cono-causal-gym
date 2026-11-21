"""Coordenadas hiperbólicas para as UIFs do CONO Causal Gym.

Até o Espaço J (20/11) o grafo era só topologia: sabia quem conecta
com quem, mas não onde nada está. Aqui as UIFs ganham um lugar — um
ponto no Disco de Poincaré (o modelo do plano hiperbólico com
|p| < 1), aprendido do grafo, não colocado à mão.

A métrica: d(u, v) = arcosh(1 + 2|u-v|² / ((1-|u|²)(1-|v|²))).
Perto da borda do disco as distâncias explodem — é por isso que o
modelo expressa hierarquia: nós centrais ficam perto uns dos outros e
nós periféricos ficam longe entre si, mesmo com o mesmo número de
rastros.

O embutimento (v0.1): minimização de estresse. O alvo entre dois nós
é proporcional à distância de grafo (menor caminho, sem peso): t_ij =
escala * d_grafo(i, j). A perda é a média de (d_hiperbólico - t)²
sobre todos os pares. Otimização por descida de gradiente com
gradiente numérico (diferenças centrais), projeção para |p| <= 0,95,
e 3 reinícios com sementes derivadas — fica o de menor estresse. Tudo
determinístico por semente e só com a stdlib.

O que isto NÃO faz (limite honesto): não redefine o Símbolo. A
emergência continua ISC >= 0,85 E VarPn <= 0,36 (DEFINICOES.md). O
que existe é a medição: raio hiperbólico de um cluster (a maior
distância ao centro médio) e separação entre clusters. A proposta
"Símbolo = bola hiperbólica" está testada como medição, não adotada
como regra — é uma decisão do Dan, não deste módulo.
"""

import math
import random
from collections import deque

RAIO_MAXIMO = 0.95
ESCALA_PADRAO = 0.6
PASSOS_PADRAO = 200
TAXA_PADRAO = 0.08
REINICIOS_PADRAO = 3


def distancia_poincare(u, v):
    """Distância no Disco de Poincaré entre u=(x,y) e v=(x,y)."""
    ux, uy = u
    vx, vy = v
    nu2 = min(ux * ux + uy * uy, 0.999999)
    nv2 = min(vx * vx + vy * vy, 0.999999)
    dx, dy = ux - vx, uy - vy
    arg = 1.0 + 2.0 * (dx * dx + dy * dy) / ((1.0 - nu2) * (1.0 - nv2))
    return math.acosh(max(arg, 1.0))


def distancias_grafo(grafo):
    """Menor caminho (sem peso) entre todos os pares, por BFS.
    Retorna dict {(i, j): distância} sobre os índices de
    grafo.hashes(), e o maior valor finito encontrado."""
    hashes = grafo.hashes()
    n = len(hashes)
    adj = grafo.matriz_adjacencia()
    vizinhos = [
        [j for j in range(n) if adj[i][j] != 0.0] for i in range(n)
    ]
    dist = {}
    max_finita = 0
    for origem in range(n):
        vistos = {origem: 0}
        fila = deque([origem])
        while fila:
            atual = fila.popleft()
            for viz in vizinhos[atual]:
                if viz not in vistos:
                    vistos[viz] = vistos[atual] + 1
                    fila.append(viz)
        for destino in range(origem + 1, n):
            d = vistos.get(destino)
            if d is not None:
                dist[(origem, destino)] = d
                max_finita = max(max_finita, d)
    return dist, max_finita


def _perda(pontos, alvos):
    total = 0.0
    for (i, j), alvo in alvos.items():
        d = distancia_poincare(pontos[i], pontos[j])
        total += (d - alvo) ** 2
    return total / max(len(alvos), 1)


def _gradiente_numerico(pontos, alvos, h=1e-4):
    grad = [[0.0, 0.0] for _ in pontos]
    for i, (x, y) in enumerate(pontos):
        for k in (0, 1):
            p_mais = [list(p) for p in pontos]
            p_menos = [list(p) for p in pontos]
            p_mais[i][k] += h
            p_menos[i][k] -= h
            grad[i][k] = (
                _perda(p_mais, alvos) - _perda(p_menos, alvos)
            ) / (2.0 * h)
    return grad


def _projetar(ponto):
    x, y = ponto
    norma = math.hypot(x, y)
    if norma > RAIO_MAXIMO:
        fator = RAIO_MAXIMO / norma
        return (x * fator, y * fator)
    return (x, y)


def embutir(grafo, passos=PASSOS_PADRAO, taxa=TAXA_PADRAO,
            semente=42, escala=ESCALA_PADRAO, reinicios=REINICIOS_PADRAO):
    """Aprende um ponto no disco para cada UIF, do grafo.
    Retorna {"coordenadas": {hash: (x, y)}, "stress": float,
    "n_nos": int, "passos": int}."""
    hashes = grafo.hashes()
    n = len(hashes)
    if n == 0:
        return {"coordenadas": {}, "stress": 0.0, "n_nos": 0, "passos": passos}
    dist, max_finita = distancias_grafo(grafo)
    alvos = {}
    for (i, j), d in dist.items():
        alvos[(i, j)] = escala * d
    alvo_desconectado = escala * (max_finita + 2)
    for i in range(n):
        for j in range(i + 1, n):
            if (i, j) not in alvos:
                alvos[(i, j)] = alvo_desconectado

    melhor = None
    for reinicio in range(reinicios):
        rng = random.Random(semente + 1000 * reinicio)
        pontos = []
        for _ in range(n):
            angulo = rng.uniform(0.0, 2.0 * math.pi)
            raio = 0.5 * math.sqrt(rng.random())
            pontos.append((raio * math.cos(angulo), raio * math.sin(angulo)))
        for _ in range(passos):
            grad = _gradiente_numerico(pontos, alvos)
            pontos = [
                _projetar((x - taxa * gx, y - taxa * gy))
                for (x, y), (gx, gy) in zip(pontos, grad)
            ]
        perda = _perda(pontos, alvos)
        if melhor is None or perda < melhor[0]:
            melhor = (perda, pontos)
    perda, pontos = melhor
    return {
        "coordenadas": {
            h: (round(x, 6), round(y, 6))
            for h, (x, y) in zip(hashes, pontos)
        },
        "stress": round(perda, 6),
        "n_nos": n,
        "passos": passos,
    }


def centro_e_raio(pontos):
    """Centro médio (euclidiano) de um conjunto de pontos e o raio
    hiperbólico: a maior distância de Poincaré ao centro."""
    if not pontos:
        return (0.0, 0.0), 0.0
    cx = sum(p[0] for p in pontos) / len(pontos)
    cy = sum(p[1] for p in pontos) / len(pontos)
    centro = (cx, cy)
    raio = max(distancia_poincare(centro, p) for p in pontos)
    return centro, raio


def separacao(pontos_a, pontos_b):
    """A menor distância de Poincaré entre dois conjuntos de pontos."""
    if not pontos_a or not pontos_b:
        return None
    return min(
        distancia_poincare(a, b) for a in pontos_a for b in pontos_b
    )


def bola_contem(centro, raio, ponto):
    """O ponto está dentro da bola hiperbólica de centro e raio dados?"""
    return distancia_poincare(centro, ponto) <= raio
