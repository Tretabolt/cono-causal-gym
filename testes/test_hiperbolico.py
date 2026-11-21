"""Testes das coordenadas hiperbólicas do CONO Causal Gym.

O lugar que faltava: as UIFs ganham um ponto no Disco de Poincaré,
aprendido do grafo por minimização de estresse — nunca colocado à
mão. Os números abaixo são medidos pelo próprio embutimento, não
copiados de uma sonda externa.

Roda com: python3 -m unittest discover -s testes -v
"""

import math
import unittest

from cono_gym.episodios import _chamar
from cono_gym.grafo import GrafoCausal, UIF
from cono_gym.hiperbolico import (
    bola_contem,
    centro_e_raio,
    distancia_poincare,
    embutir,
    separacao,
)
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


class TesteDistanciaPoincare(unittest.TestCase):
    def test_basicos(self):
        self.assertAlmostEqual(distancia_poincare((0.0, 0.0), (0.0, 0.0)), 0.0)
        # d(0, p) = 2 * artanh(|p|)
        self.assertAlmostEqual(
            distancia_poincare((0.0, 0.0), (0.5, 0.0)),
            2.0 * math.atanh(0.5),
            places=6,
        )
        # Simetria.
        self.assertAlmostEqual(
            distancia_poincare((0.3, 0.4), (-0.2, 0.1)),
            distancia_poincare((-0.2, 0.1), (0.3, 0.4)),
            places=9,
        )
        # Perto da borda, a distância explode.
        self.assertGreater(
            distancia_poincare((0.0, 0.0), (0.99, 0.0)),
            distancia_poincare((0.0, 0.0), (0.5, 0.0)),
        )

    def test_anel_fica_mais_uniforme_perto_da_borda(self):
        # Pontos num anel de raio r: a razão máx/mín das distâncias
        # entre eles cai quando o anel se aproxima da borda — a
        # geometria hiperbólica achata as diferenças periféricas.
        def razao(r, n=6):
            pontos = [
                (r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n))
                for k in range(n)
            ]
            dists = [
                distancia_poincare(pontos[i], pontos[j])
                for i in range(n)
                for j in range(i + 1, n)
            ]
            return max(dists) / min(dists)

        self.assertGreater(razao(0.1), 1.8)
        self.assertLess(razao(0.9), 1.5)
        self.assertLess(razao(0.9), razao(0.1))


class TesteEmbutimento(unittest.TestCase):
    def test_estrela_folha_folha_maior_que_folha_centro(self):
        grafo, centro, folhas = _estrela()
        resultado = embutir(grafo)
        pontos = resultado["coordenadas"]
        d_fc = [
            distancia_poincare(pontos[centro], pontos[f]) for f in folhas
        ]
        d_ff = distancia_poincare(pontos[folhas[0]], pontos[folhas[1]])
        # As folhas ficam longe entre si, perto do centro — a
        # hierarquia aparece na geometria.
        self.assertGreater(d_ff, max(d_fc))
        razao = d_ff / max(d_fc)
        self.assertGreater(razao, 1.6)
        self.assertLess(razao, 2.0)
        self.assertLess(resultado["stress"], 0.01)

    def test_duas_cliques_formam_bolas_separadas(self):
        grafo, grupos = construir_cenario_duas_cliques()
        resultado = embutir(grafo)
        pontos = resultado["coordenadas"]
        _, raio_a = centro_e_raio([pontos[h] for h in grupos["A"]])
        _, raio_b = centro_e_raio([pontos[h] for h in grupos["B"]])
        sep = separacao(
            [pontos[h] for h in grupos["A"]],
            [pontos[h] for h in grupos["B"]],
        )
        self.assertLess(raio_a, 0.6)
        self.assertLess(raio_b, 0.6)
        self.assertGreater(sep, 1.0)
        self.assertGreater(sep / max(raio_a, raio_b), 2.0)

    def test_bola_contem_o_proprio_cluster_e_nao_o_outro(self):
        grafo, grupos = construir_cenario_duas_cliques()
        pontos = embutir(grafo)["coordenadas"]
        pts_a = [pontos[h] for h in grupos["A"]]
        pts_b = [pontos[h] for h in grupos["B"]]
        centro_a, raio_a = centro_e_raio(pts_a)
        self.assertTrue(all(bola_contem(centro_a, raio_a, p) for p in pts_a))
        self.assertFalse(any(bola_contem(centro_a, raio_a, p) for p in pts_b))

    def test_determinismo_por_semente(self):
        grafo, _ = construir_cenario_duas_cliques()
        a = embutir(grafo, semente=42)["coordenadas"]
        b = embutir(grafo, semente=42)["coordenadas"]
        c = embutir(grafo, semente=7)["coordenadas"]
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_todos_dentro_do_disco(self):
        grafo, _ = construir_cenario_duas_cliques()
        pontos = embutir(grafo)["coordenadas"]
        for x, y in pontos.values():
            self.assertLess(math.hypot(x, y), 1.0)


class TesteToolsHiperbolicas(unittest.TestCase):
    def test_embed_e_measure_pelas_tools(self):
        grafo, grupos = construir_cenario_duas_cliques()
        servidor = ConoGymServer(grafo)
        embutido = _chamar(servidor, "embed_hyperbolic", {})
        self.assertEqual(embutido["n_nos"], 12)
        self.assertLess(embutido["stress"], 0.1)
        medicao = _chamar(
            servidor,
            "measure_geometry",
            {"clusters": {"A": grupos["A"], "B": grupos["B"]}},
        )
        self.assertLess(medicao["clusters"]["A"]["raio"], 0.6)
        self.assertGreater(
            medicao["separacoes"]["A-B"]["razao_sep_raio"], 2.0
        )

    def test_measure_sem_embed_e_recusado(self):
        grafo, _ = construir_cenario_duas_cliques()
        servidor = ConoGymServer(grafo)
        with self.assertRaises(RuntimeError):
            _chamar(servidor, "measure_geometry", {})


if __name__ == "__main__":
    unittest.main()
