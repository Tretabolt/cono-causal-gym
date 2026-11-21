"""Testes do esqueleto do MVP do CONO Causal Gym.

Roda com: python3 -m unittest discover -s testes -v
"""

import unittest

from cono_gym.espectro import avaliar_cluster, espectro, isc_local, var_lambda
from cono_gym.grafo import GrafoCausal, UIF
from cono_gym.hasher import hash_rastro, hash_simbolo, hash_uif


def _grafo_completo(n):
    grafo = GrafoCausal()
    hs = []
    for i in range(n):
        uif = UIF(serial=f"k{i}", tipo_agente="no", funcao_s=f"no-{i}")
        grafo.adicionar_uif(uif)
        hs.append(uif.hash_uif)
    for i in range(n):
        for j in range(i + 1, n):
            grafo.depositar_rastro(hs[i], hs[j], "liga")
    return grafo


def _estrela():
    grafo = GrafoCausal()
    centro = UIF(serial="centro", tipo_agente="decisao", funcao_s="decisao")
    grafo.adicionar_uif(centro)
    hs = [centro.hash_uif]
    for nome in ("sol", "calor", "chuva"):
        uif = UIF(serial=nome, tipo_agente="sensor", funcao_s=nome)
        grafo.adicionar_uif(uif)
        grafo.depositar_rastro(uif.hash_uif, centro.hash_uif, "causa")
        hs.append(uif.hash_uif)
    return grafo


class TesteHasher(unittest.TestCase):
    def test_deterministico(self):
        self.assertEqual(
            hash_uif("s1", "agente", "f"), hash_uif("s1", "agente", "f")
        )

    def test_identidade_nao_depende_de_estado(self):
        # Não existe parâmetro de estado: a mesma identidade tem o mesmo
        # hash, qualquer que seja o estado mutável que venha depois.
        a = UIF(serial="s1", tipo_agente="agente", funcao_s="f")
        b = UIF(serial="s1", tipo_agente="agente", funcao_s="f")
        self.assertEqual(a.hash_uif, b.hash_uif)

    def test_serial_diferente_hash_diferente(self):
        self.assertNotEqual(
            hash_uif("s1", "agente", "f"), hash_uif("s2", "agente", "f")
        )

    def test_rastro_direcao_importa(self):
        self.assertNotEqual(
            hash_rastro("A", "B", "causa"), hash_rastro("B", "A", "causa")
        )

    def test_hash_simbolo_amarra_espectro(self):
        esp = [0.0, 1.0, 1.0, 2.0]
        self.assertNotEqual(
            hash_simbolo("sim", esp), hash_simbolo("sim", [0.0, 1.0, 1.0, 1.5])
        )


class TesteGrafo(unittest.TestCase):
    def test_deposito_repetido_atualiza_peso_sem_criar_aresta(self):
        grafo = GrafoCausal()
        a = UIF(serial="a", tipo_agente="t", funcao_s="a")
        b = UIF(serial="b", tipo_agente="t", funcao_s="b")
        grafo.adicionar_uif(a)
        grafo.adicionar_uif(b)
        grafo.depositar_rastro(a.hash_uif, b.hash_uif, "causa", peso=1.0)
        grafo.depositar_rastro(a.hash_uif, b.hash_uif, "causa", peso=2.5)
        self.assertEqual(grafo.n_arestas(), 1)
        adj = grafo.matriz_adjacencia()
        self.assertAlmostEqual(adj[0][1], 2.5)

    def test_sem_self_loop(self):
        grafo = GrafoCausal()
        a = UIF(serial="a", tipo_agente="t", funcao_s="a")
        grafo.adicionar_uif(a)
        with self.assertRaises(ValueError):
            grafo.depositar_rastro(a.hash_uif, a.hash_uif, "causa")

    def test_vizinhanca_raio_1_na_estrela(self):
        grafo = _estrela()
        centro = grafo.hashes()[0]
        vista = grafo.vizinhanca(centro, raio=1)
        self.assertEqual(len(vista), 4)  # centro + 3 sensores


class TesteEspectro(unittest.TestCase):
    def test_estrela_espectro_conhecido(self):
        esp = espectro(_estrela())
        self.assertEqual(len(esp), 4)
        for obtido, esperado in zip(esp, [0.0, 1.0, 1.0, 2.0]):
            self.assertAlmostEqual(obtido, esperado, places=9)

    def test_soma_dos_autovalores_e_n(self):
        for n in (4, 5, 6):
            self.assertAlmostEqual(sum(espectro(_grafo_completo(n))), n, places=9)

    def test_clique_4_espectro_conhecido(self):
        esp = espectro(_grafo_completo(4))
        for obtido, esperado in zip(esp, [0.0, 4 / 3, 4 / 3, 4 / 3]):
            self.assertAlmostEqual(obtido, esperado, places=9)

    def test_estrela_nao_e_simbolo(self):
        grafo = _estrela()
        self.assertAlmostEqual(isc_local(grafo), 0.50)
        self.assertAlmostEqual(var_lambda(espectro(grafo)), 0.50)
        rel = avaliar_cluster(grafo, "simbolo-estrela")
        self.assertFalse(rel["simbolo"])
        self.assertIsNone(rel["hash_simbolo"])

    def test_k5_e_simbolo_no_limite(self):
        grafo = _grafo_completo(5)
        self.assertAlmostEqual(isc_local(grafo), 1.0)
        self.assertAlmostEqual(var_lambda(espectro(grafo)), 0.25, places=9)
        rel = avaliar_cluster(grafo, "simbolo-k5")
        self.assertTrue(rel["simbolo"])
        self.assertIsNotNone(rel["hash_simbolo"])

    def test_k6_e_simbolo_folgado(self):
        grafo = _grafo_completo(6)
        self.assertAlmostEqual(var_lambda(espectro(grafo)), 0.20, places=9)
        rel = avaliar_cluster(grafo, "simbolo-k6")
        self.assertTrue(rel["simbolo"])


if __name__ == "__main__":
    unittest.main()
