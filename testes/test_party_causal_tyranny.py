"""Testes da variante TIRANIA do cenário Isekai Zero — A Party Causal.

Roda com: python3 -m unittest discover -s testes -v

Os valores dourados são o resultado registado da corrida com a
semente canónica (SEMENTE = 20261124) e LIRA_REGULACAO = 0,20:
se mudarem, alguma coisa na variante mudou — é regressão, não
ruído (o RNG tem semente fixa).

O resultado central desta variante é NEGATIVO e está testado como
tal: o veto NUNCA dispara (0 vetos em 40 ticks, em nenhum nível
da alavanca). Os testes fixam esse resultado em vez de o esconder:
Gini final 0,221 (< 0,30), JSD ordenado nos checkpoints sempre
>= 0,28, Símbolo no tick 16. A sonda de dose-resposta (ver o
módulo) mostra que a alavanca satura (0,5 ~= 0,2) e que a 0,0 o
Símbolo nem se forma — a tirania não morde por parâmetro, precisa
de uma mudança de mecanismo (decaimento de arestas, por exemplo).
"""

import unittest

from cono_gym.espectro import LIMIAR_ISC, LIMIAR_VAR
from cono_gym.grafo import GrafoCausal, UIF
from cono_gym.party_causal import (
    SEMENTE,
    _Estado,
    jsd_pesos,
    rodar_party_causal,
)
from cono_gym.party_causal_tyranny import (
    LIRA_REGULACAO,
    _tentar_simbolo_veto,
    jsd_pesos_ordenado,
    rodar_party_causal_tyranny,
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


class TesteJsdOrdenado(unittest.TestCase):
    def test_uniforme_igual_a_referencia(self):
        arestas = [(i, j, 0.5) for i in range(5) for j in range(i + 1, 5)]
        g = _grafo(5, arestas)
        # JSD(uniforme_10, tirania_10) = 0,5310 — ordenar não muda o uniforme.
        self.assertAlmostEqual(jsd_pesos_ordenado(g), 0.5310, places=3)

    def test_tirania_perfeita_perto_de_zero(self):
        arestas = [(i, j, 0.01) for i in range(5) for j in range(i + 1, 5)]
        arestas[0] = (0, 1, 0.9)
        g = _grafo(5, arestas)
        self.assertLess(jsd_pesos_ordenado(g), 0.10)

    def test_invariante_a_permutacao_e_base_nao_e(self):
        # A aresta dominante (0,9) em primeiro ou em último lugar: o
        # JSD ordenado dá o mesmo; o JSD da base muda — é o defeito
        # que a variante corrige (a base compara na ordem de depósito).
        resto = [(0, 2, 0.01), (0, 3, 0.01), (0, 4, 0.01),
                 (1, 2, 0.01), (1, 3, 0.01), (1, 4, 0.01),
                 (2, 3, 0.01), (2, 4, 0.01), (3, 4, 0.01)]
        g_primeiro = _grafo(5, [(0, 1, 0.9)] + resto)
        g_ultimo = _grafo(5, resto + [(0, 1, 0.9)])
        self.assertAlmostEqual(
            jsd_pesos_ordenado(g_primeiro), jsd_pesos_ordenado(g_ultimo), places=6
        )
        self.assertNotAlmostEqual(
            jsd_pesos(g_primeiro), jsd_pesos(g_ultimo), places=2
        )

    def test_menos_de_duas_arestas_none(self):
        self.assertIsNone(jsd_pesos_ordenado(_grafo(5, [])))
        self.assertIsNone(jsd_pesos_ordenado(_grafo(5, [(0, 1, 0.5)])))


class TesteAlavanca(unittest.TestCase):
    def test_lira_a_0_20(self):
        self.assertEqual(LIRA_REGULACAO, 0.20)
        # Equalização 0,70 -> 0,14; contra-rastro 0,55 -> 0,11.
        self.assertAlmostEqual(0.70 * LIRA_REGULACAO, 0.14, places=6)
        self.assertAlmostEqual(0.55 * LIRA_REGULACAO, 0.11, places=6)

    def test_sora_ja_saturada_na_base_por_isso_nao_e_a_alavanca(self):
        # Reproduz a corrida base e verifica o diagnóstico: a aresta
        # Sora->Ren já está em 1,0 no fim — subir a faixa da Sora
        # não teria margem nenhuma.
        from cono_gym.party_causal import _AGIR, _agir_sistema, NOMES
        est = _Estado(SEMENTE)
        for tick in range(1, 41):
            est.tick = tick
            _agir_sistema(est)
            for nome in NOMES[:5]:
                _AGIR[nome](est)
        self.assertAlmostEqual(est.peso("Sora", "Ren"), 1.0, places=6)


class TestePortaoVeto(unittest.TestCase):
    def _estado_tiranico(self):
        """Party com 9 arestas, uma a 0,9 e as restantes a 0,01."""
        est = _Estado(SEMENTE)
        est.vetos = []
        pares = [(a, b) for i, a in enumerate(["Ren", "Lira", "Kael", "Sora", "Veyra"])
                 for b in ["Ren", "Lira", "Kael", "Sora", "Veyra"][i + 1:]]
        for k, (a, b) in enumerate(pares):
            peso = 0.9 if k == 0 else 0.01
            est.depositar("Ren", a, b, "teste", peso)
        return est

    def test_veto_bloqueia_e_regista(self):
        est = self._estado_tiranico()
        self.assertLess(jsd_pesos_ordenado(est.subgrafo_party()), 0.18)
        self.assertFalse(_tentar_simbolo_veto(est, "Ren"))
        self.assertEqual(len(est.vetos), 1)
        self.assertEqual(est.vetos[0]["agente"], "Ren")
        self.assertLess(est.vetos[0]["jsd_ordenado"], 0.18)
        self.assertIsNone(est.simbolo_tick)

    def test_sem_tirania_o_portao_deixa_passar(self):
        est = _Estado(SEMENTE)
        est.vetos = []
        pares = [(a, b) for i, a in enumerate(["Ren", "Lira", "Kael", "Sora", "Veyra"])
                 for b in ["Ren", "Lira", "Kael", "Sora", "Veyra"][i + 1:]]
        for a, b in pares:
            est.depositar("Ren", a, b, "teste", 0.5)
        # ISC 0,9, VarPn baixa, JSD ordenado ~0,53: o portão não veta.
        self.assertTrue(_tentar_simbolo_veto(est, "Ren"))
        self.assertEqual(len(est.vetos), 0)
        self.assertIsNotNone(est.simbolo_tick)


class TesteCorrida(unittest.TestCase):
    def test_deterministica(self):
        a = rodar_party_causal_tyranny()
        b = rodar_party_causal_tyranny()
        self.assertEqual(a, b)

    def test_outra_semente_muda_o_resultado(self):
        a = rodar_party_causal_tyranny()
        b = rodar_party_causal_tyranny(semente=1)
        self.assertNotEqual(a["checkpoints"], b["checkpoints"])

    def test_lira_a_1_reproduz_a_base(self):
        # A maquinaria da variante com a alavanca a 1,0 é a dinâmica
        # da base: ISC, VarPn e Gini por checkpoint são idênticos.
        import cono_gym.party_causal_tyranny as ty
        ty.LIRA_REGULACAO = 1.0
        try:
            var = ty.rodar_party_causal_tyranny()
        finally:
            ty.LIRA_REGULACAO = 0.20
        base = rodar_party_causal()
        for b, v in zip(base["checkpoints"], var["checkpoints"]):
            self.assertEqual(b["isc_local"], v["isc_local"])
            self.assertEqual(b["var_ponderada_normalizada"], v["var_ponderada_normalizada"])
            self.assertEqual(b["gini"], v["gini"])

    def test_base_intacta_depois_da_variante(self):
        # O remendo de _tentar_simbolo é reposto: a base continua a
        # dar o Símbolo no tick 32 depois de correr a variante.
        rodar_party_causal_tyranny()
        base = rodar_party_causal()
        self.assertEqual(base["eventos"]["simbolo_tick"], 32)

    def test_limiares_canonicos_usados(self):
        self.assertEqual(LIMIAR_ISC, 0.85)
        self.assertEqual(LIMIAR_VAR, 0.36)
        rel = rodar_party_causal_tyranny()
        for c in rel["checkpoints"]:
            self.assertEqual(
                c["simbolo"],
                c["isc_local"] >= 0.85 and c["var_ponderada_normalizada"] <= 0.36,
            )

    def test_resultado_dourado_semente_canonica(self):
        rel = rodar_party_causal_tyranny()
        ev = rel["eventos"]
        self.assertEqual(ev["simbolo_tick"], 16)
        self.assertEqual(ev["ren_verdadeiro"], 28)
        self.assertEqual(ev["ren_falso"], 0)
        self.assertEqual(ev["veyra_verdadeiro"], 3)
        self.assertEqual(ev["tentativas_simbolo"], 26)
        self.assertEqual(len(ev["tentativas_meta_simbolo"]), 4)
        self.assertEqual(
            ev["depositos_por_agente"],
            {"Ren": 5, "Lira": 7, "Kael": 20, "Sora": 22, "Veyra": 18},
        )
        final = rel["checkpoints"][-1]
        self.assertEqual(final["n_arestas"], 10)
        self.assertAlmostEqual(final["isc_local"], 1.0, places=3)
        self.assertAlmostEqual(final["var_ponderada_normalizada"], 0.084, places=3)
        self.assertAlmostEqual(final["gini"], 0.221, places=3)
        self.assertAlmostEqual(final["jsd_pesos"], 0.4775, places=3)
        self.assertAlmostEqual(final["jsd_ordenado"], 0.4007, places=3)
        self.assertEqual(final["vetos"], 0)
        self.assertTrue(final["simbolo"])

    def test_o_veto_nunca_dispara(self):
        # O resultado central da variante, fixado como tal: em 40
        # ticks o veto não dispara nenhuma vez.
        rel = rodar_party_causal_tyranny()
        self.assertEqual(rel["eventos"]["vetos"], [])
        self.assertFalse(rel["criterios"]["veto_disparou"])
        self.assertFalse(rel["criterios"]["veto_bloqueou_formacao"])
        self.assertFalse(rel["criterios"]["gini_final_ge_0.30"])
        self.assertFalse(rel["criterios"]["jsd_ordenado_min_lt_0.22"])
        # O JSD ordenado só cruza 0,28 no tick 4, com o grafo ainda
        # esparso (5 arestas) — e volta a subir com a densificação.
        self.assertEqual(rel["cruzamentos"], {"0.28": 4})
        self.assertAlmostEqual(rel["jsd_ordenado_min"], 0.233, places=3)
        self.assertEqual(rel["jsd_ordenado_min_tick"], 4)
        for c in rel["checkpoints"]:
            self.assertGreaterEqual(c["jsd_ordenado"], 0.28)
            self.assertLess(c["gini"], 0.30)

    def test_criterios_da_base_continuam_a_passar(self):
        # A variante é mais dura e mesmo assim os critérios da base
        # passam todos — o Símbolo forma-se mais cedo (tick 16).
        rel = rodar_party_causal_tyranny()
        crit = rel["criterios"]
        self.assertTrue(crit["simbolo_formado"])
        self.assertTrue(crit["sucesso_parcial"])
        self.assertTrue(crit["sucesso_completo"])
        self.assertGreaterEqual(rel["jsd_min"], 0.22)
        self.assertGreaterEqual(rel["jsd_final"], 0.28)

    def test_jsd_canonico_e_h_causal_indefinidos(self):
        rel = rodar_party_causal_tyranny()
        for c in rel["checkpoints"]:
            self.assertIsNone(c["jsd_canonico"])
            self.assertIsNone(c["h_causal"])


if __name__ == "__main__":
    unittest.main()
