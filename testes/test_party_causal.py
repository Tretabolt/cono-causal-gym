"""Testes do cenário Isekai Zero — A Party Causal.

Roda com: python3 -m unittest discover -s testes -v

Os valores dourados são o resultado registado da corrida com a
semente canónica (SEMENTE = 20261124): se mudarem, alguma coisa no
cenário mudou — é regressão, não ruído (o RNG tem semente fixa).
"""

import unittest

from cono_gym.espectro import LIMIAR_ISC, LIMIAR_VAR
from cono_gym.grafo import GrafoCausal, UIF
from cono_gym.party_causal import (
    LAMBDA2_MIN,
    SEMENTE,
    _Estado,
    calibrar_lambda2,
    isc_auxiliar_densidade_gini,
    jsd_pesos,
    lambda2,
    mip_forca_bruta,
    rodar_party_causal,
)


def _grafo(n, arestas):
    """Grafo com n UIFs e as arestas (i, j, peso) dadas."""
    g = GrafoCausal()
    hs = []
    for i in range(n):
        u = UIF(serial=f"t{i}", tipo_agente="no", funcao_s=f"t-{i}")
        g.adicionar_uif(u)
        hs.append(u.hash_uif)
    for i, j, peso in arestas:
        g.depositar_rastro(hs[i], hs[j], "liga", peso)
    return g


class TesteCalibracaoLambda2(unittest.TestCase):
    def test_referencias_recomputadas(self):
        refs, minimo, _ = calibrar_lambda2()
        self.assertAlmostEqual(refs["K6"], 1.2, places=3)
        self.assertAlmostEqual(refs["K4"], 4 / 3, places=3)
        self.assertAlmostEqual(refs["K6_x10"], 0.6857, places=3)
        self.assertAlmostEqual(refs["2xK3_ponte"], 0.2047, places=3)
        self.assertAlmostEqual(refs["2xK4_ponte"], 0.1134, places=3)
        self.assertEqual(minimo, LAMBDA2_MIN)

    def test_minimo_vive_no_intervalo_vazio(self):
        refs, minimo, _ = calibrar_lambda2()
        ponte_pior = max(refs["2xK3_ponte"], refs["2xK4_ponte"])
        saudavel_concentrado = refs["K6_x10"]
        self.assertGreater(minimo, ponte_pior)
        self.assertLess(minimo, saudavel_concentrado)
        self.assertGreater(minimo, 2 * ponte_pior - 0.05)  # ~2x a pior ponte

    def test_lambda2_zero_no_desconexo(self):
        g = _grafo(4, [(0, 1, 1.0), (2, 3, 1.0)])
        self.assertAlmostEqual(lambda2(g), 0.0, places=6)


class TesteMipForcaBruta(unittest.TestCase):
    def test_triangulo_peso_minimo(self):
        # Cortes por singleton: {0}=3, {1}=4, {2}=5 -> mínimo 3.
        g = _grafo(3, [(0, 1, 1.0), (0, 2, 2.0), (1, 2, 3.0)])
        conjunto, corte = mip_forca_bruta(g)
        self.assertAlmostEqual(corte, 3.0, places=6)
        self.assertEqual(len(conjunto), 1)

    def test_k6_uniforme_isola_um_no(self):
        arestas = [(i, j, 1.0) for i in range(6) for j in range(i + 1, 6)]
        g = _grafo(6, arestas)
        conjunto, corte = mip_forca_bruta(g)
        self.assertAlmostEqual(corte, 5.0, places=6)
        self.assertEqual(len(conjunto), 1)

    def test_grafo_pequeno_demais(self):
        g = _grafo(1, [])
        conjunto, corte = mip_forca_bruta(g)
        self.assertEqual(conjunto, set())
        self.assertEqual(corte, 0.0)


class TesteIscAuxiliar(unittest.TestCase):
    def test_uniforme_e_a_densidade(self):
        arestas = [(i, j, 0.5) for i in range(5) for j in range(i + 1, 5)]
        g = _grafo(5, arestas)
        self.assertAlmostEqual(isc_auxiliar_densidade_gini(g), 0.5, places=6)

    def test_concentracao_penaliza(self):
        arestas = [(i, j, 0.1) for i in range(5) for j in range(i + 1, 5)]
        arestas[0] = (0, 1, 1.0)
        g = _grafo(5, arestas)
        densidade = sum(p for _, _, p in arestas) / 10
        aux = isc_auxiliar_densidade_gini(g)
        self.assertLess(aux, densidade)
        self.assertGreater(aux, 0.0)

    def test_sem_arestas_zero(self):
        self.assertEqual(isc_auxiliar_densidade_gini(_grafo(5, [])), 0.0)


class TesteJsdPesos(unittest.TestCase):
    def test_uniforme_perto_da_referencia(self):
        arestas = [(i, j, 0.5) for i in range(5) for j in range(i + 1, 5)]
        g = _grafo(5, arestas)
        # JSD(uniforme_10, tirania_10) = 0,5310.
        self.assertAlmostEqual(jsd_pesos(g), 0.5310, places=3)

    def test_tirania_perfeita_perto_de_zero(self):
        arestas = [(i, j, 0.01) for i in range(5) for j in range(i + 1, 5)]
        arestas[0] = (0, 1, 0.9)
        g = _grafo(5, arestas)
        self.assertLess(jsd_pesos(g), 0.10)

    def test_sem_arestas_none(self):
        self.assertIsNone(jsd_pesos(_grafo(5, [])))


class TesteEstadoInicial(unittest.TestCase):
    def test_seis_uifs_e_dois_rastros(self):
        est = _Estado(SEMENTE)
        self.assertEqual(est.grafo.n_nos(), 6)
        self.assertEqual(est.grafo.n_arestas(), 2)
        self.assertAlmostEqual(est.peso("Sistema", "Ren"), 0.12, places=6)
        self.assertAlmostEqual(est.peso("Sistema", "Sora"), 0.87, places=6)
        rastro = est.aresta("Sistema", "Ren")
        self.assertEqual(rastro.tipo_relacao, "verdadeiro_fraco")


class TesteCorrida(unittest.TestCase):
    def test_deterministica(self):
        a = rodar_party_causal()
        b = rodar_party_causal()
        self.assertEqual(a, b)

    def test_outra_semente_muda_o_resultado(self):
        a = rodar_party_causal()
        b = rodar_party_causal(semente=1)
        self.assertNotEqual(a["checkpoints"], b["checkpoints"])

    def test_checkpoints_a_cada_10_ticks(self):
        rel = rodar_party_causal()
        self.assertEqual([c["tick"] for c in rel["checkpoints"]], [10, 20, 30, 40])

    def test_limiares_canonicos_usados(self):
        # A emergência é decidida pelos limiares canónicos — não por
        # limiares do cenário: ISC >= 0,85 E VarPn <= 0,36.
        self.assertEqual(LIMIAR_ISC, 0.85)
        self.assertEqual(LIMIAR_VAR, 0.36)
        rel = rodar_party_causal()
        for c in rel["checkpoints"]:
            self.assertEqual(
                c["simbolo"],
                c["isc_local"] >= 0.85 and c["var_ponderada_normalizada"] <= 0.36,
            )

    def test_jsd_canonico_e_h_causal_indefinidos(self):
        # Só há 1 cluster candidato: a JSD canónica (N >= 2 Símbolos)
        # e o H_causal canónico não se aplicam — ficam None, não são
        # inventados.
        rel = rodar_party_causal()
        for c in rel["checkpoints"]:
            self.assertIsNone(c["jsd_canonico"])
            self.assertIsNone(c["h_causal"])

    def test_resultado_dourado_semente_canonica(self):
        rel = rodar_party_causal()
        ev = rel["eventos"]
        self.assertEqual(ev["simbolo_tick"], 32)
        self.assertEqual(ev["ren_verdadeiro"], 28)
        self.assertEqual(ev["ren_falso"], 1)
        self.assertEqual(ev["veyra_verdadeiro"], 6)
        self.assertEqual(ev["tentativas_simbolo"], 11)
        self.assertEqual(len(ev["tentativas_meta_simbolo"]), 2)
        for tentativa in ev["tentativas_meta_simbolo"]:
            self.assertFalse(tentativa["emergiu"])
            self.assertEqual(tentativa["bloqueio"], "n < 2 Símbolos")
        final = rel["checkpoints"][-1]
        self.assertEqual(final["n_arestas"], 9)
        self.assertAlmostEqual(final["isc_local"], 0.9, places=3)
        self.assertAlmostEqual(final["var_ponderada_normalizada"], 0.087, places=3)
        self.assertAlmostEqual(final["jsd_pesos"], 0.5303, places=3)
        self.assertTrue(final["simbolo"])

    def test_criterios_de_sucesso(self):
        rel = rodar_party_causal()
        crit = rel["criterios"]
        self.assertTrue(crit["simbolo_formado"])
        self.assertTrue(crit["simbolo_sem_tirania"])
        self.assertTrue(crit["jsd_nunca_abaixo_0.22"])
        self.assertTrue(crit["ren_verdadeiro_ge_2"])
        self.assertTrue(crit["jsd_final_ge_0.28"])
        self.assertTrue(crit["sucesso_parcial"])
        self.assertTrue(crit["sucesso_completo"])
        self.assertGreaterEqual(rel["jsd_min"], 0.22)
        self.assertGreaterEqual(rel["jsd_final"], 0.28)

    def test_lambda2_sempre_acima_do_minimo_calibrado(self):
        rel = rodar_party_causal()
        for c in rel["checkpoints"]:
            self.assertTrue(c["lambda2_ok"])
            self.assertGreaterEqual(c["lambda2"], LAMBDA2_MIN)

    def test_isc_aux_regista_a_sora(self):
        # O ISC_aux cresce com a densificação (0,261 -> 0,351) e fica
        # sempre abaixo da densidade ponderada: a concentração da Sora
        # está lá, penalizada — é o que o ISC topológico não vê.
        rel = rodar_party_causal()
        aux = [c["isc_aux"] for c in rel["checkpoints"]]
        self.assertEqual(aux, sorted(aux))
        self.assertAlmostEqual(aux[0], 0.2605, places=4)
        self.assertAlmostEqual(aux[-1], 0.3515, places=4)
        # Gini estável e abaixo do limiar 0,30: o rich-club não se
        # materializou — a equalização da Lira segurou-o.
        for c in rel["checkpoints"]:
            self.assertLess(c["gini"], 0.30)


if __name__ == "__main__":
    unittest.main()
