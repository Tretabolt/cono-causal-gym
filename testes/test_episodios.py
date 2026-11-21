"""Testes do loop de episódios do CONO Causal Gym.

Os números aqui são o comportamento observado com semente 42 em 12
episódios — e cada um deles foi verificado à mão antes de virar teste,
não apenas fotografado. Se um número mudar, o teste deve doer: ele
protege um comportamento, não um retrato.

Roda com: python3 -m unittest discover -s testes -v
"""

import json
import unittest

from cono_gym.episodios import LoopEpisodios
from cono_gym.mcp_server import ConoGymServer, construir_cenario_duas_cliques


def _rodar(semente=42, n=12):
    grafo, grupos = construir_cenario_duas_cliques()
    servidor = ConoGymServer(grafo)
    loop = LoopEpisodios(servidor, clusters=grupos, semente=semente)
    return loop.rodar(n_episodios=n)


class TesteLoop(unittest.TestCase):
    def test_deterministico_mesma_semente(self):
        a = _rodar()
        b = _rodar()
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))

    def test_semente_diferente_muda_o_resultado(self):
        a = _rodar(semente=42)
        b = _rodar(semente=7)
        self.assertNotEqual(
            json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True)
        )

    def test_episodio_1_dois_simbolos_validos_sem_meta(self):
        rel = _rodar()
        ep1 = rel["episodios"][0]
        self.assertEqual(ep1["n_registrados"], 2)
        self.assertEqual(ep1["n_validos"], 2)
        self.assertEqual(ep1["h_causal"], 1.0)
        self.assertEqual(ep1["isc_global"], 1.0)
        self.assertFalse(ep1["meta_simbolo"])
        self.assertFalse(ep1["tensao_presente"])

    def test_meta_se_forma_no_episodio_4_e_permanece(self):
        # Com a VarP adotada (18/11), a história muda: A não morre mais
        # no episódio 4, então as duas condições coincidem — 2 Símbolos
        # válidos E tensão (Gini 0,321) — e o Meta-Símbolo se forma no
        # episódio 4, pela primeira vez no loop. H_causal é 1,0 bit e
        # ISC_Global é 1,0 em todos os episódios (2 válidos sempre).
        # (VarPn média no ep 4: 0,0975, abaixo do limiar 0,36.)
        # O Meta-Símbolo é persistente: uma vez formado, continua
        # existindo nos episódios 8-10 mesmo sem tensão.
        rel = _rodar()
        self.assertEqual(rel["resumo"]["episodio_meta"], 4)
        self.assertTrue(rel["resumo"]["meta_simbolo_formado"])
        for ep in rel["episodios"][:3]:
            self.assertFalse(ep["meta_simbolo"])
            self.assertEqual(ep["h_causal"], 1.0)
            self.assertEqual(ep["isc_global"], 1.0)
        for ep in rel["episodios"][3:]:
            self.assertTrue(ep["meta_simbolo"])
            self.assertEqual(ep["h_causal"], 1.0)
            self.assertEqual(ep["isc_global"], 1.0)

    def test_nenhum_simbolo_quebra(self):
        # Antes da VarP, um rastro pesado dentro de A empurrava a Var
        # acima de 0,25 no episódio 4 e A morria. Com a VarP (e depois
        # a VarPn), o mesmo rastro dá VarPn ~0,10 e A sobrevive:
        # estabilidade 1,0 nos dois.
        rel = _rodar()
        for ep in rel["episodios"]:
            self.assertEqual(ep["n_validos"], 2)
        self.assertAlmostEqual(
            rel["resumo"]["estabilidade_por_simbolo"]["simbolo-A"], 1.0
        )
        self.assertAlmostEqual(
            rel["resumo"]["estabilidade_por_simbolo"]["simbolo-B"], 1.0
        )
        self.assertAlmostEqual(rel["resumo"]["estabilidade_media"], 1.0)

    def test_simbolo_tudo_nunca_se_forma(self):
        # O grafo inteiro é esparso demais (ISC ~0,5-0,67 < 0,85).
        rel = _rodar()
        self.assertNotIn("simbolo-tudo", rel["resumo"]["simbolos_registrados"])

    def test_tensao_pisca_meta_permanece(self):
        # Episódios 8-10: o Gini cai abaixo de 0,30 e a tensão some,
        # mas o Meta-Símbolo continua — ele é persistente depois de
        # formado, não é reavaliado a cada episódio. Tensão em 6 dos 12.
        rel = _rodar()
        for ep in rel["episodios"][7:10]:
            self.assertFalse(ep["tensao_presente"])
            self.assertTrue(ep["meta_simbolo"])
        self.assertEqual(rel["resumo"]["episodios_com_tensao"], 6)

    def test_numeros_finais(self):
        rel = _rodar()
        resumo = rel["resumo"]
        self.assertAlmostEqual(resumo["gini_final"], 0.333, places=3)
        self.assertAlmostEqual(resumo["var_media_final"], 0.0827, places=4)


if __name__ == "__main__":
    unittest.main()
