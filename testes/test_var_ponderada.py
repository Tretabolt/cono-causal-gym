"""Testes da Var ponderada (cono_gym/var_ponderada.py).

A VarP = Var(λ_comb / tr(L)): invariante a escala uniforme, sensível
a reponderação relativa. Os números abaixo são os do experimento
rodado em 18/11 — se mudarem, o desenho mudou e o teste deve acusar.
"""

import itertools
import unittest

from cono_gym.espectro import avaliar_cluster
from cono_gym.grafo import GrafoCausal, UIF
from cono_gym.var_ponderada import (
    LIMIAR_VAR_PONDERADA,
    LIMIAR_VARP_NORMALIZADA,
    avaliar_cluster_ponderado,
    teto_varp,
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


class TesteVarPonderadaEstrela(unittest.TestCase):
    def test_uniforme(self):
        self.assertAlmostEqual(var_ponderada(estrela([1, 1, 1])), 0.0625, places=4)

    def test_escala_uniforme_nao_muda(self):
        self.assertAlmostEqual(
            var_ponderada(estrela([10, 10, 10])),
            var_ponderada(estrela([1, 1, 1])),
            places=6,
        )

    def test_reponderacao_relativa_muda(self):
        # A cegueira da estrela acabou: [10,1,1] ve 0,1328, não 0,0625.
        self.assertAlmostEqual(var_ponderada(estrela([10, 1, 1])), 0.1328, places=4)
        self.assertGreater(
            var_ponderada(estrela([10, 1, 1])), var_ponderada(estrela([1, 1, 1]))
        )

    def test_mesma_proporcao_mesmo_valor(self):
        # [1, 0.1, 0.1] é [10, 1, 1] dividido por 10: só a escala muda.
        self.assertAlmostEqual(
            var_ponderada(estrela([1, 0.1, 0.1])),
            var_ponderada(estrela([10, 1, 1])),
            places=6,
        )

    def test_assimetria_maior_var_maior(self):
        self.assertAlmostEqual(var_ponderada(estrela([100, 1, 1])), 0.1803, places=4)
        self.assertGreater(
            var_ponderada(estrela([100, 1, 1])), var_ponderada(estrela([10, 1, 1]))
        )

    def test_reordenacao_nao_muda(self):
        base = var_ponderada(estrela([7, 2, 0.5]))
        for ordem in [["A", "B", "D", "C"], ["D", "C", "B", "A"]]:
            self.assertAlmostEqual(
                var_ponderada(estrela([7, 2, 0.5], ordem=ordem)), base, places=6
            )


class TesteVarPonderadaK6(unittest.TestCase):
    def test_uniforme(self):
        self.assertAlmostEqual(var_ponderada(k6([1] * 15)), 0.0056, places=4)

    def test_escala_uniforme_nao_muda(self):
        self.assertAlmostEqual(
            var_ponderada(k6([5] * 15)), var_ponderada(k6([1] * 15)), places=6
        )

    def test_um_rastro_pesado_cresce_suave(self):
        # x2 quase não mexe; x5, x10 sobem devagar; x100 dispara.
        self.assertAlmostEqual(var_ponderada(k6([2] + [1] * 14)), 0.0061, places=4)
        self.assertAlmostEqual(var_ponderada(k6([5] + [1] * 14)), 0.0115, places=4)
        self.assertAlmostEqual(var_ponderada(k6([10] + [1] * 14)), 0.0243, places=4)
        self.assertAlmostEqual(var_ponderada(k6([100] + [1] * 14)), 0.1061, places=4)

    def test_limiar_005_separa_x10_de_x100(self):
        self.assertLess(var_ponderada(k6([10] + [1] * 14)), LIMIAR_VAR_PONDERADA)
        self.assertGreater(var_ponderada(k6([100] + [1] * 14)), LIMIAR_VAR_PONDERADA)


class TesteAvaliarClusterPonderado(unittest.TestCase):
    def test_k6_uniforme_eh_simbolo(self):
        rep = avaliar_cluster_ponderado(k6([1] * 15), "K6")
        self.assertTrue(rep["simbolo"])
        self.assertIsNotNone(rep["hash_simbolo"])

    def test_k6_um_x10_continua_simbolo(self):
        # O ponto do desenho, agora como regra vigente: a Var ANTIGA
        # (0,2882 > 0,25) matava o K6 aqui; a VarP (0,0243 <= 0,05)
        # não mata — e avaliar_cluster já usa a VarP desde 18/11.
        from cono_gym.espectro import espectro, var_lambda

        velha = var_lambda(espectro(k6([10] + [1] * 14)))
        self.assertAlmostEqual(velha, 0.2882, places=4)
        self.assertGreater(velha, 0.25)
        nova = avaliar_cluster(k6([10] + [1] * 14), "K6")
        self.assertTrue(nova["simbolo"])

    def test_k6_um_x100_nao_eh_simbolo(self):
        rep = avaliar_cluster_ponderado(k6([100] + [1] * 14), "K6")
        self.assertFalse(rep["simbolo"])

    def test_estrela_continua_fora_pelo_isc(self):
        # A VarP enxerga a estrela, mas o ISC 0,50 a mantém fora.
        rep = avaliar_cluster_ponderado(estrela([1, 1, 1]), "estrela")
        self.assertFalse(rep["simbolo"])
        self.assertAlmostEqual(rep["isc_local"], 0.5)


class TesteVarPonderadaNormalizada(unittest.TestCase):
    def test_teto_formula_fechada(self):
        # (n-1)/n², conferido contra os tetos medidos em robustez_varp.py.
        self.assertAlmostEqual(teto_varp(4), 0.1875, places=4)
        self.assertAlmostEqual(teto_varp(5), 0.1600, places=4)
        self.assertAlmostEqual(teto_varp(6), 0.1389, places=4)
        self.assertAlmostEqual(teto_varp(10), 0.0900, places=4)
        self.assertEqual(teto_varp(1), 0.0)

    def test_limiar_036_e_a_razao_do_k6(self):
        self.assertAlmostEqual(
            LIMIAR_VARP_NORMALIZADA, 0.05 / teto_varp(6), places=2
        )

    def test_k6_numeros_normalizados(self):
        self.assertAlmostEqual(
            var_ponderada_normalizada(k6([1] * 15)), 0.040, places=3
        )
        self.assertAlmostEqual(
            var_ponderada_normalizada(k6([10] + [1] * 14)), 0.175, places=3
        )
        self.assertAlmostEqual(
            var_ponderada_normalizada(k6([100] + [1] * 14)), 0.764, places=3
        )

    def test_um_limiar_vale_para_todo_tamanho(self):
        # O mesmo exagero (um x10) mata o K4 e poupa o K6 e o K10 —
        # porque num K4 ele é 1 de 6 arestas, num K10 é 1 de 45.
        # E um x100 mata o K10. Um só limiar, 0,36, decide tudo.
        def kn1(n, peso):
            g = GrafoCausal()
            hs = []
            for i in range(n):
                u = UIF(f"K{i}", "Executor", "S")
                g.adicionar_uif(u)
                hs.append(u.hash_uif)
            import itertools as _it

            for (i, j), p in zip(
                _it.combinations(range(n), 2), [peso] + [1] * (n * (n - 1) // 2 - 1)
            ):
                g.depositar_rastro(hs[i], hs[j], "CAUSA", peso=p)
            return g

        self.assertGreater(var_ponderada_normalizada(kn1(4, 10)), 0.36)
        self.assertLess(var_ponderada_normalizada(kn1(6, 10)), 0.36)
        self.assertLess(var_ponderada_normalizada(kn1(10, 10)), 0.36)
        self.assertGreater(var_ponderada_normalizada(kn1(10, 100)), 0.36)

    def test_avaliar_cluster_usa_a_normalizada(self):
        # A regra vigente decide pela VarPn: K6 com um x10 vive
        # (VarPn 0,175 <= 0,36) e o relatório carrega a normalizada.
        rep = avaliar_cluster(k6([10] + [1] * 14), "K6")
        self.assertTrue(rep["simbolo"])
        self.assertAlmostEqual(
            rep["var_ponderada_normalizada"], 0.175, places=3
        )


if __name__ == "__main__":
    unittest.main()
