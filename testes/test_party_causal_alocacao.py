"""Testes da análise ALOCAÇÃO DE DEPÓSITOS da Party Causal.

A instrumentação não muda a corrida: a raio ∞ a variante
instrumentada reproduz a base exactamente, como a POMDP, e em
todos os raios reproduz a POMDP. Os números da comparação
raio 2 vs controlo (e raio 1 como contraste) ficam fixos aqui —
incluindo o veredicto das três hipóteses.
"""

import unittest

from cono_gym import party_causal as pc
from cono_gym.party_causal_alocacao import (
    PARES_DO_KAEL,
    _EstadoAlocacao,
    classificar,
    ganho,
    rodar_party_causal_alocacao,
    sondar_alocacao,
    testar_hipoteses,
)
from cono_gym.party_causal_pomdp import rodar_party_causal_pomdp


def _evento(antes, depois, recusado=False):
    return {
        "tick": 1,
        "agente": "Lira",
        "par": ("Lira", "Ren"),
        "tipo": "teste",
        "peso_ofertado": depois if depois is not None else 0.5,
        "peso_antes": antes,
        "peso_depois": depois,
        "nova_aresta": antes is None and not recusado,
        "redundante": (not recusado) and antes is not None and depois == antes,
        "recusado": recusado,
    }


class TesteClassificacao(unittest.TestCase):
    def test_criador(self):
        ev = _evento(None, 0.45)
        self.assertEqual(classificar(ev), "criador")
        self.assertAlmostEqual(ganho(ev), 0.45)

    def test_reforco(self):
        ev = _evento(0.30, 0.45)
        self.assertEqual(classificar(ev), "reforco")
        self.assertAlmostEqual(ganho(ev), 0.15)

    def test_redundante(self):
        # Oferta menor ou igual ao peso actual: o peso não sobe.
        ev = _evento(0.50, 0.50)
        self.assertEqual(classificar(ev), "redundante")
        self.assertEqual(ganho(ev), 0.0)

    def test_redundante_no_teto(self):
        # Aresta já a 1,0: qualquer oferta é redundante.
        ev = _evento(1.0, 1.0)
        self.assertEqual(classificar(ev), "redundante")

    def test_recusado(self):
        ev = _evento(0.30, 0.30, recusado=True)
        self.assertEqual(classificar(ev), "recusado")
        self.assertEqual(ganho(ev), 0.0)


class TesteInstrumentacao(unittest.TestCase):
    def test_deposito_nao_incidente_recusado_e_registado(self):
        """A guarda da POMDP recusa o depósito, o registo marca-o
        como recusado e o grafo não muda."""
        est = _EstadoAlocacao(raio=1)
        est.tick = 5
        antes = est.peso("Lira", "Sora")
        self.assertIsNone(est.depositar("Ren", "Lira", "Sora", "teste", 0.5))
        self.assertEqual(len(est.eventos_deposito), 1)
        ev = est.eventos_deposito[0]
        self.assertTrue(ev["recusado"])
        self.assertEqual(ev["agente"], "Ren")
        self.assertEqual(ev["par"], ("Lira", "Sora"))
        self.assertEqual(est.peso("Lira", "Sora"), antes)
        self.assertEqual(est.depositos["Ren"], 0)

    def test_deposito_incidente_regista_antes_e_depois(self):
        est = _EstadoAlocacao(raio=1)
        est.tick = 5
        est.depositar("Sora", "Sora", "Ren", "teste", 0.8)
        ev = est.eventos_deposito[0]
        self.assertFalse(ev["recusado"])
        self.assertTrue(ev["nova_aresta"])
        self.assertEqual(ev["peso_antes"], None)
        self.assertEqual(ev["peso_depois"], 0.8)

    def test_instrumentacao_nao_muda_a_corrida(self):
        """Em todos os raios, a corrida instrumentada é a POMDP:
        mesmos checkpoints, mesmos eventos, mesmos contadores."""
        for raio in (1, 2, float("inf")):
            with self.subTest(raio=raio):
                inst = rodar_party_causal_alocacao(raio=raio)
                pomdp = rodar_party_causal_pomdp(raio=raio)
                self.assertEqual(
                    [
                        (c["tick"], c["n_arestas"], c["isc_local"], c["var_ponderada_normalizada"])
                        for c in inst["checkpoints"]
                    ],
                    [
                        (c["tick"], c["n_arestas"], c["isc_local"], c["var_ponderada_normalizada"])
                        for c in pomdp["checkpoints"]
                    ],
                )
                self.assertEqual(inst["eventos"], pomdp["eventos"])
                self.assertEqual(inst["trajetoria"], pomdp["trajetoria"])
                self.assertEqual(inst["criterios"], pomdp["criterios"])
                # O registo tem exactamente um evento por depósito
                # contado, e nenhum recusado em nenhum raio.
                self.assertEqual(
                    len(inst["eventos_deposito"]),
                    sum(inst["eventos"]["depositos_por_agente"].values()),
                )
                self.assertEqual(inst["alocacao"]["resumo"]["recusados"], 0)


class TesteControlo(unittest.TestCase):
    def test_raio_infinito_reproduz_base(self):
        """O controlo instrumentado é a base: mesmos checkpoints,
        mesmos eventos, mesmos depósitos e seguimentos."""
        base = pc.rodar_party_causal()
        ctrl = rodar_party_causal_alocacao(raio=float("inf"))
        self.assertEqual(
            [
                (c["tick"], c["n_arestas"], c["isc_local"], c["var_ponderada_normalizada"])
                for c in ctrl["checkpoints"]
            ],
            [
                (c["tick"], c["n_arestas"], c["isc_local"], c["var_ponderada_normalizada"])
                for c in base["checkpoints"]
            ],
        )
        ev_b, ev_c = base["eventos"], ctrl["eventos"]
        self.assertEqual(ev_c["simbolo_tick"], ev_b["simbolo_tick"])
        self.assertEqual(ev_c["simbolo_tick"], 32)
        self.assertEqual(ev_c["ren_verdadeiro"], 28)
        self.assertEqual(ev_c["ren_falso"], 1)
        self.assertEqual(ev_c["veyra_verdadeiro"], 6)
        self.assertEqual(ev_c["tentativas_simbolo"], 11)
        self.assertEqual(
            ev_c["depositos_por_agente"],
            {"Ren": 2, "Lira": 32, "Kael": 14, "Sora": 27, "Veyra": 19},
        )
        self.assertEqual(ev_c["depositos_por_agente"], ev_b["depositos_por_agente"])
        self.assertEqual(ev_c["seguimentos_por_agente"], ev_b["seguimentos_por_agente"])
        self.assertEqual(ctrl["jsd_min"], base["jsd_min"])
        self.assertEqual(ctrl["jsd_final"], base["jsd_final"])
        self.assertEqual(ctrl["eventos"]["vetos_estado"], [])
        self.assertTrue(ctrl["criterios"]["simbolo_valido"])

    def test_base_intacta_depois_da_variante(self):
        rodar_party_causal_alocacao(raio=1)
        rodar_party_causal_alocacao(raio=float("inf"))
        base = pc.rodar_party_causal()
        self.assertEqual(base["eventos"]["simbolo_tick"], 32)
        self.assertEqual(base["eventos"]["ren_verdadeiro"], 28)


class TesteComparacao(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.linhas = sondar_alocacao()
        cls.por_raio = {l["raio"]: l for l in cls.linhas}

    def test_sonda(self):
        self.assertEqual([l["raio"] for l in self.linhas], [1, 2, float("inf")])
        self.assertEqual(
            [l["simbolo_tick"] for l in self.linhas], [None, 26, 32]
        )
        self.assertEqual(
            [l["resumo"]["total_aceites"] for l in self.linhas], [67, 79, 94]
        )

    def test_totais_por_classe(self):
        """79 contra 94: os 15 depósitos a menos são −17
        redundantes, +1 criador e +1 reforço — a raio 2 ganha
        MAIS peso total (3,79 contra 3,76) com menos depósitos."""
        esperado = {
            1: {"criadores": 8, "reforcos": 6, "redundantes": 53,
                "quota_redundante": 0.791, "ganho_total": 2.8385},
            2: {"criadores": 11, "reforcos": 6, "redundantes": 62,
                "quota_redundante": 0.7848, "ganho_total": 3.7917},
            float("inf"): {"criadores": 10, "reforcos": 5, "redundantes": 79,
                           "quota_redundante": 0.8404, "ganho_total": 3.7629},
        }
        for raio, esp in esperado.items():
            with self.subTest(raio=raio):
                resumo = self.por_raio[raio]["resumo"]
                for chave, valor in esp.items():
                    self.assertAlmostEqual(resumo[chave], valor, places=4)

    def test_onde_vem_que_vem_os_15_a_menos(self):
        """Por agente: Lira −8, Kael −8, Sora +7, Veyra −6, Ren 0.
        Por redundância: Lira −11, Kael −8, Sora +9, Veyra −7."""
        r2 = self.por_raio[2]
        ctrl = self.por_raio[float("inf")]
        self.assertEqual(
            {n: r2["depositos"][n] - ctrl["depositos"][n] for n in pc.NOMES[:5]},
            {"Ren": 0, "Lira": -8, "Kael": -8, "Sora": 7, "Veyra": -6},
        )
        red_r2 = {
            n: v["redundantes"]
            for n, v in r2["por_agente"].items()
        }
        red_ctrl = {
            n: v["redundantes"]
            for n, v in ctrl["por_agente"].items()
        }
        self.assertEqual(
            {n: red_r2[n] - red_ctrl[n] for n in pc.NOMES[:5]},
            {"Ren": 0, "Lira": -11, "Kael": -8, "Sora": 9, "Veyra": -7},
        )

    def test_redundancia_concentra_se_na_sora_ren(self):
        """A raio 2 a redundância concentra-se numa só aresta:
        Ren–Sora leva 34 depósitos, 32 redundantes (43% do
        total). No controlo espalha-se: Kael–Lira 14, Lira–Veyra
        13, Kael–Sora 13, Ren–Sora 23."""
        r2 = self.por_raio[2]["por_aresta"][("Ren", "Sora")]
        self.assertEqual((r2["total"], r2["redundantes"]), (34, 32))
        ctrl = self.por_raio[float("inf")]["por_aresta"]
        self.assertEqual(
            {p: ctrl[p]["redundantes"] for p in
             [("Kael", "Lira"), ("Lira", "Veyra"), ("Kael", "Sora"), ("Ren", "Sora")]},
            {("Kael", "Lira"): 14, ("Lira", "Veyra"): 13,
             ("Kael", "Sora"): 13, ("Ren", "Sora"): 23},
        )

    def test_pares_do_kael(self):
        """Kael–Ren nasce a raio 2 no tick 22 (Ren), 9 ticks
        antes do controlo (31, Ren); Kael–Sora nasce a raio 2
        no tick 24 (Kael) — no controlo nasce no tick 2 (Kael,
        o filtro vê o falso forte global) — e a raio 1 nunca
        nasce nenhum dos dois."""
        r1 = self.por_raio[1]
        r2 = self.por_raio[2]
        ctrl = self.por_raio[float("inf")]
        for par in PARES_DO_KAEL:
            self.assertIsNone(r1["primeiro_deposito_por_par"][par])
        self.assertEqual(r2["por_aresta"][("Kael", "Ren")]["primeiro_tick"], 22)
        self.assertEqual(r2["por_aresta"][("Kael", "Ren")]["primeiro_agente"], "Ren")
        self.assertEqual(ctrl["por_aresta"][("Kael", "Ren")]["primeiro_tick"], 31)
        self.assertEqual(r2["por_aresta"][("Kael", "Sora")]["primeiro_tick"], 24)
        self.assertEqual(r2["por_aresta"][("Kael", "Sora")]["primeiro_agente"], "Kael")
        self.assertEqual(ctrl["por_aresta"][("Kael", "Sora")]["primeiro_tick"], 2)
        self.assertEqual(ctrl["por_aresta"][("Kael", "Sora")]["primeiro_agente"], "Kael")

    def test_nascimento_das_ultimas_arestas(self):
        """A 9.ª aresta nasce a raio 2 no tick 24 (Kael–Sora) e
        no controlo no tick 31 (Kael–Ren); a 10.ª nasce a raio 2
        no tick 38 (Lira–Ren) e no controlo nunca. O Símbolo
        segue a 9.ª aresta por 2 ticks a raio 2 (26) e por 1 no
        controlo (32)."""
        r2 = self.por_raio[2]["nascimento"]
        ctrl = self.por_raio[float("inf")]["nascimento"]
        self.assertEqual(r2[9], 24)
        self.assertEqual(ctrl[9], 31)
        self.assertEqual(r2[10], 38)
        self.assertIsNone(ctrl[10])
        self.assertIsNone(self.por_raio[1]["nascimento"][9])

    def test_raio_1_numeros(self):
        """A raio 1: 67 depósitos, 53 redundantes (quota 0,791) —
        a Sora martela Ren–Sora 27 vezes sem efeito; Ren e Kael
        depositam 0 vezes."""
        r1 = self.por_raio[1]
        self.assertEqual(r1["depositos"], {"Ren": 0, "Lira": 22, "Kael": 0, "Sora": 29, "Veyra": 16})
        self.assertEqual(r1["por_aresta"][("Ren", "Sora")]["redundantes"], 27)
        self.assertEqual(r1["resumo"]["agente_top"], "Sora")
        self.assertEqual(r1["resumo"]["aresta_top"], ("Ren", "Sora"))

    def test_criador_sistema(self):
        """O 11.º criador a raio 2 é Veyra→Sistema (periferia,
        tick 33); no controlo o criador é no tick 19. A raio 1
        não há nenhum — a Veyra nunca chega à periferia."""
        for raio, tick_esperado in ((2, 33), (float("inf"), 19)):
            rel = rodar_party_causal_alocacao(raio=raio)
            criadores = [
                e for e in rel["eventos_deposito"]
                if "Sistema" in e["par"] and e["nova_aresta"]
            ]
            self.assertEqual(len(criadores), 1)
            self.assertEqual(criadores[0]["tick"], tick_esperado)
            self.assertEqual(criadores[0]["agente"], "Veyra")
        rel1 = rodar_party_causal_alocacao(raio=1)
        self.assertEqual(
            [e for e in rel1["eventos_deposito"] if "Sistema" in e["par"]], []
        )


class TesteHipotese(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hip = testar_hipoteses(sondar_alocacao())

    def test_hipotese_a_redundancia(self):
        """(a) CONFIRMA-SE: 62 redundantes a raio 2 contra 79 no
        controlo (−17); a quota baixa de 0,8404 para 0,7848."""
        h = self.hip["hipotese_a_redundancia"]
        self.assertTrue(h["confirma"])
        self.assertEqual(h["redundantes_raio_2"], 62)
        self.assertEqual(h["redundantes_controlo"], 79)
        self.assertEqual(h["diferenca"], -17)

    def test_hipotese_b_pares_do_kael(self):
        """(b) CONFIRMA-SE: os dois pares que faltam a raio 1
        nascem a raio 2 (22 e 24) e nunca a raio 1."""
        h = self.hip["hipotese_b_pares_do_kael"]
        self.assertTrue(h["confirma"])
        self.assertEqual(
            h["primeiro_deposito"][("Kael", "Ren")],
            {"raio_1": None, "raio_2": 22, "controlo": 31},
        )
        self.assertEqual(
            h["primeiro_deposito"][("Kael", "Sora")],
            {"raio_1": None, "raio_2": 24, "controlo": 2},
        )

    def test_hipotese_c_timing(self):
        """(c) CONFIRMA-SE: a 9.ª aresta nasce 7 ticks mais cedo
        a raio 2 (24 contra 31) e o Símbolo segue-a (26 contra
        32)."""
        h = self.hip["hipotese_c_timing"]
        self.assertTrue(h["confirma"])
        self.assertEqual(h["tick_9_arestas_raio_2"], 24)
        self.assertEqual(h["tick_9_arestas_controlo"], 31)
        self.assertEqual(h["tick_10_arestas_raio_2"], 38)
        self.assertIsNone(h["tick_10_arestas_controlo"])
        self.assertEqual((h["simbolo_raio_2"], h["simbolo_controlo"]), (26, 32))

    def test_diferenca_15_depositos(self):
        d = self.hip["diferenca_depositos_raio_2_vs_controlo"]
        self.assertEqual(d["total"], -15)
        self.assertEqual(d["redundantes"], -17)
        self.assertEqual(d["reforcos"], 1)
        self.assertEqual(d["criadores"], 1)


class TesteDeterminismo(unittest.TestCase):
    def test_duas_sondas_iguais(self):
        self.assertEqual(sondar_alocacao(), sondar_alocacao())


if __name__ == "__main__":
    unittest.main()
