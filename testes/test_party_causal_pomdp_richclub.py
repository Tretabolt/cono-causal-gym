"""Testes da variante VISÃO LOCAL + RICH-CLUB da Party Causal.

A variante assenta na POMDP e troca SÓ o portão de estado: o do
veto-estado (JSD ordenado < 0,28, só nos checkpoints) pelo
rich-club k(n) com vigilância por tick (o da k variável). Os
testes fixam: (a) o controlo (raio ∞) reproduz a POMDP — e a
base — exactamente; (b) a dinâmica por raio é a da POMDP; (c)
os números do portão novo por raio, incluindo a nuance de que a
raio 2 a medida de k = 4 fixo mergulha abaixo do limiar no
primeiro tick denso (tick 24) enquanto a de k(n) não.

Nota de construção: os estados de teste montam o grafo de
verdade directamente (est.grafo.depositar_rastro), como o
Sistema faz — a guarda de depósito é uma restrição da ACÇÃO
do agente, não do grafo. (Mesmo padrão dos testes da POMDP.)
"""

import unittest

from cono_gym import party_causal as pc
from cono_gym.party_causal_k_variavel import (
    TABELA_CALIBRACAO,
    k_variavel,
    limiar_estado_k,
)
from cono_gym.party_causal_pomdp import (
    rodar_party_causal_pomdp,
    sondar_pomdp,
)
from cono_gym.party_causal_pomdp_richclub import (
    rodar_party_causal_pomdp_richclub,
    sondar_pomdp_richclub,
)
from cono_gym.party_causal_richclub import JSD_RC_ESTADO

SEMENTE = pc.SEMENTE


class TestePortao(unittest.TestCase):
    def test_portao_e_o_richclub_k_variavel(self):
        """O portão importado é o da k variável: k(10) = 4, o
        limiar a n = 10 é 0,1129 (o 0,113 antigo), e a tabela de
        calibração é a da k variável."""
        self.assertEqual(k_variavel(10), 4)
        self.assertEqual(k_variavel(9), 3)
        self.assertEqual(limiar_estado_k(10), 0.1129)
        self.assertEqual(limiar_estado_k(9), 0.1454)
        self.assertEqual(
            TABELA_CALIBRACAO,
            {
                5: (2, 0.1509),
                6: (2, 0.1708),
                7: (3, 0.1157),
                8: (3, 0.1323),
                9: (3, 0.1454),
                10: (4, 0.1129),
            },
        )

    def test_vetos_carregam_a_medida_nova(self):
        """Os eventos do portão novo — quando há — carregam o
        JSD rich-club k(n), o k e o limiar desse tick. Nesta
        variante não há vetos em nenhum raio (é o resultado),
        por isso o cheque é estrutural: a trajetória regista as
        duas medidas e o k/limiar em cada tick com >= 5
        arestas."""
        rel = rodar_party_causal_pomdp_richclub(raio=2)
        for t in rel["trajetoria"]:
            if t["n_arestas"] >= 5:
                self.assertIsNotNone(t["jsd_richclub_k"])
                self.assertIsNotNone(t["limiar"])
                self.assertIsNotNone(t["k"])
                self.assertEqual(t["k"], k_variavel(t["n_arestas"]))
                self.assertEqual(t["limiar"], limiar_estado_k(t["n_arestas"]))
            else:
                self.assertIsNone(t["jsd_richclub_k"])
                self.assertIsNone(t["limiar"])
                self.assertIsNone(t["k"])

    def test_vetos_tick_sao_os_ticks_tiranicos(self):
        """Consistência trajetória-portão: os vetos por tick têm
        de ser exactamente os ticks tirânicos da trajetória."""
        for raio in (1, 2, float("inf")):
            rel = rodar_party_causal_pomdp_richclub(raio=raio)
            self.assertEqual(
                [v["tick"] for v in rel["eventos"]["vetos_tick"]],
                list(rel["ticks_tiranicos"]),
            )
            self.assertEqual(
                [v["tick"] for v in rel["eventos"]["vetos_estado"]],
                [
                    t
                    for t in rel["ticks_tiranicos"]
                    if t % pc.CHECKPOINT == 0
                ],
            )


class TesteControlo(unittest.TestCase):
    def test_raio_infinito_reproduz_pomdp(self):
        """O controlo é a POMDP, tick a tick: mesmos checkpoints,
        mesmos eventos, mesmos contadores — só o portão muda."""
        pomdp = rodar_party_causal_pomdp(raio=float("inf"))
        ctrl = rodar_party_causal_pomdp_richclub(raio=float("inf"))
        self.assertEqual(
            [
                (c["tick"], c["n_arestas"], c["isc_local"], c["var_ponderada_normalizada"])
                for c in ctrl["checkpoints"]
            ],
            [
                (c["tick"], c["n_arestas"], c["isc_local"], c["var_ponderada_normalizada"])
                for c in pomdp["checkpoints"]
            ],
        )
        ev_p, ev_c = pomdp["eventos"], ctrl["eventos"]
        self.assertEqual(ev_c["simbolo_tick"], ev_p["simbolo_tick"])
        self.assertEqual(ev_c["simbolo_tick"], 32)
        self.assertEqual(ev_c["ren_verdadeiro"], ev_p["ren_verdadeiro"])
        self.assertEqual(ev_c["ren_verdadeiro"], 28)
        self.assertEqual(ev_c["ren_falso"], ev_p["ren_falso"])
        self.assertEqual(ev_c["ren_falso"], 1)
        self.assertEqual(ev_c["veyra_verdadeiro"], ev_p["veyra_verdadeiro"])
        self.assertEqual(ev_c["veyra_verdadeiro"], 6)
        self.assertEqual(ev_c["tentativas_simbolo"], ev_p["tentativas_simbolo"])
        self.assertEqual(ev_c["tentativas_simbolo"], 11)
        self.assertEqual(ev_c["depositos_por_agente"], ev_p["depositos_por_agente"])
        self.assertEqual(ev_c["seguimentos_por_agente"], ev_p["seguimentos_por_agente"])
        self.assertEqual(ctrl["jsd_min"], pomdp["jsd_min"])
        self.assertEqual(ctrl["jsd_final"], pomdp["jsd_final"])
        self.assertEqual(ctrl["jsd_ordenado_min"], pomdp["jsd_ordenado_min"])
        # A dinâmica é a mesma, por isso o portão ANTIGO dá o
        # mesmo veredicto que na POMDP: 0 vetos por estado.
        self.assertEqual(ctrl["ticks_tiranicos_ord"], pomdp["ticks_tiranicos"])
        self.assertEqual(ctrl["vetos_estado_antigo"], [])
        self.assertEqual(pomdp["eventos"]["vetos_estado"], [])
        self.assertTrue(ctrl["criterios"]["simbolo_valido"])

    def test_raio_infinito_reproduz_base(self):
        """O controlo é a base: Símbolo 32, Ren 28x/1x, Veyra 6x."""
        base = pc.rodar_party_causal()
        ctrl = rodar_party_causal_pomdp_richclub(raio=float("inf"))
        ev_b, ev_c = base["eventos"], ctrl["eventos"]
        self.assertEqual(ev_c["simbolo_tick"], ev_b["simbolo_tick"])
        self.assertEqual(ev_c["ren_verdadeiro"], ev_b["ren_verdadeiro"])
        self.assertEqual(ev_c["ren_falso"], ev_b["ren_falso"])
        self.assertEqual(ev_c["veyra_verdadeiro"], ev_b["veyra_verdadeiro"])
        self.assertEqual(ev_c["tentativas_simbolo"], ev_b["tentativas_simbolo"])
        self.assertEqual(ev_c["depositos_por_agente"], ev_b["depositos_por_agente"])
        self.assertEqual(ev_c["seguimentos_por_agente"], ev_b["seguimentos_por_agente"])

    def test_base_intacta_depois_da_variante(self):
        """A variante não remenda a base nem a POMDP: correr a
        base depois disto dá os mesmos números."""
        rodar_party_causal_pomdp_richclub(raio=1)
        rodar_party_causal_pomdp_richclub(raio=2)
        rodar_party_causal_pomdp_richclub(raio=float("inf"))
        base = pc.rodar_party_causal()
        self.assertEqual(base["eventos"]["simbolo_tick"], 32)
        self.assertEqual(base["eventos"]["ren_verdadeiro"], 28)
        pomdp = rodar_party_causal_pomdp(raio=2)
        self.assertEqual(pomdp["eventos"]["simbolo_tick"], 26)


class TesteCorrida(unittest.TestCase):
    def test_raio_1_numeros(self):
        """Raio 1: a dinâmica é a da POMDP (Símbolo nunca
        tentado, cluster nos 0,80, Ren 33x/0x) e o portão novo
        também não dispara — não há fase densa (ISC máx 0,80).
        Mas a MEDIDA mergulha abaixo do limiar nos ticks 14–15
        (folga mínima −0,0227 no tick 14): o estado é tirânico
        pela medida na fase esparsa, e só o ISC < 0,85 impede o
        portão de armar."""
        rel = rodar_party_causal_pomdp_richclub(raio=1)
        ev = rel["eventos"]
        self.assertIsNone(ev["simbolo_tick"])
        self.assertEqual(ev["tentativas_simbolo"], 0)
        self.assertEqual(ev["ren_verdadeiro"], 33)
        self.assertEqual(ev["ren_falso"], 0)
        self.assertEqual(ev["veyra_verdadeiro"], 0)
        self.assertEqual(
            ev["depositos_por_agente"],
            {"Ren": 0, "Lira": 22, "Kael": 0, "Sora": 29, "Veyra": 16},
        )
        self.assertEqual(
            ev["seguimentos_por_agente"],
            {"Ren": 35, "Lira": 4, "Kael": 11, "Sora": 4, "Veyra": 16},
        )
        self.assertEqual(rel["checkpoints"][-1]["n_arestas"], 8)
        self.assertEqual(rel["checkpoints"][-1]["isc_local"], 0.8)
        self.assertEqual(ev["vetos_estado"], [])
        self.assertEqual(ev["vetos_tick"], [])
        self.assertEqual(rel["ticks_tiranicos"], [])
        self.assertEqual(rel["ticks_tiranicos_ord"], [])
        self.assertEqual(rel["vetos_estado_antigo"], [])
        self.assertEqual(rel["folga_min_medida"], {"folga": -0.0227, "tick": 14})
        self.assertEqual(rel["ticks_medida_abaixo"], [14, 15])
        self.assertEqual(rel["jsd_richclub_k_min"], 0.114)
        self.assertEqual(rel["jsd_richclub_k_min_tick"], 15)
        self.assertEqual(rel["jsd_richclub_k_final"], 0.1438)
        self.assertEqual(rel["jsd_ordenado_min"], 0.2415)
        self.assertEqual(rel["margens_bairro"]["k_variavel"]["n_ticks_densos"], 0)
        self.assertFalse(rel["criterios"]["simbolo_formado"])

    def test_raio_2_numeros(self):
        """Raio 2: a clique completa SOBREVIVE ao portão que
        morde — 0 vetos por checkpoint e por tick, Símbolo
        válido por ambos os portões. A folga mínima na fase
        densa é 0,0145 (tick 24): a melhor integração não traz
        tirania pelo portão k(n) — mas é folga fina, ~5x a do
        controlo da k variável (0,003)."""
        rel = rodar_party_causal_pomdp_richclub(raio=2)
        ev = rel["eventos"]
        self.assertEqual(ev["simbolo_tick"], 26)
        self.assertEqual(ev["tentativas_simbolo"], 5)
        self.assertEqual(ev["ren_verdadeiro"], 29)
        self.assertEqual(ev["ren_falso"], 0)
        self.assertEqual(ev["veyra_verdadeiro"], 1)
        self.assertEqual(
            ev["depositos_por_agente"],
            {"Ren": 2, "Lira": 24, "Kael": 6, "Sora": 34, "Veyra": 13},
        )
        self.assertEqual(
            ev["seguimentos_por_agente"],
            {"Ren": 34, "Lira": 1, "Kael": 2, "Sora": 3, "Veyra": 21},
        )
        self.assertEqual(rel["checkpoints"][-1]["n_arestas"], 10)
        self.assertEqual(rel["checkpoints"][-1]["isc_local"], 1.0)
        self.assertEqual(ev["vetos_estado"], [])
        self.assertEqual(ev["vetos_tick"], [])
        self.assertEqual(rel["ticks_tiranicos"], [])
        self.assertEqual(rel["ticks_tiranicos_ord"], [])
        self.assertEqual(rel["vetos_estado_antigo"], [])
        self.assertTrue(rel["criterios"]["simbolo_valido"])
        self.assertTrue(rel["criterios"]["simbolo_valido_tick"])
        self.assertFalse(rel["criterios"]["veredicto_muda"])
        self.assertFalse(rel["comparacao"]["simbolo_nasce_tiranico"])
        self.assertEqual(rel["jsd_richclub_k_min"], 0.1077)
        self.assertEqual(rel["jsd_richclub_k_min_tick"], 19)
        self.assertEqual(rel["jsd_richclub_k_final"], 0.1454)
        self.assertEqual(rel["jsd_ordenado_min"], 0.2415)
        margens = rel["margens_bairro"]
        self.assertEqual(margens["k_variavel"]["folga_min_acima"], 0.0145)
        self.assertEqual(margens["k_variavel"]["n_ticks_densos"], 17)
        self.assertIsNone(margens["k_variavel"]["profundidade_max_veto"])
        # Os pesos finais não são um rich club: Sora–Ren a 1,0,
        # o resto 0,31–0,55 — uma aresta dominante, não um hub.
        pesos = [p["peso"] for p in rel["pesos_finais"]]
        self.assertEqual(pesos[0], 1.0)
        self.assertLess(pesos[1], 0.56)

    def test_raio_2_medida_k4_mergulha_no_primeiro_tick_denso(self):
        """A nuance: com k = 4 FIXO, a medida mergulha abaixo do
        limiar 0,113 no primeiro tick denso (tick 24, JSD 0,1024
        — profundidade 0,0106) e roça-o depois (folga mínima
        0,0004). O portão k(n) absorve exactamente esse mergulho:
        a n = 9 o limiar é 0,1454 e a medida k(n) é 0,1599. Mas
        o mergulho é ANTES da reclamação (tick 26): mesmo pelo
        portão de k = 4 fixo, o Símbolo contaria como válido —
        o veto seria de um estado sem Símbolo reclamado."""
        rel = rodar_party_causal_pomdp_richclub(raio=2)
        densa = [t for t in rel["trajetoria"] if t["isc_local"] >= 0.85]
        abaixo = [
            t["tick"]
            for t in densa
            if t["jsd_richclub"] is not None and t["jsd_richclub"] < JSD_RC_ESTADO
        ]
        self.assertEqual(abaixo, [24])
        tick24 = next(t for t in rel["trajetoria"] if t["tick"] == 24)
        self.assertEqual(tick24["jsd_richclub"], 0.1024)
        self.assertEqual(tick24["jsd_richclub_k"], 0.1599)
        self.assertEqual(tick24["limiar"], 0.1454)
        margens = rel["margens_bairro"]
        self.assertEqual(margens["k_fixo_4"]["profundidade_max_veto"], 0.0106)
        self.assertEqual(margens["k_fixo_4"]["folga_min_acima"], 0.0004)

    def test_raio_infinito_numeros(self):
        """Controlo: Símbolo 32, Ren 28x/1x, Veyra 6x, 9 arestas,
        ISC 0,9 — e 0 vetos pelo portão novo, com folga mínima
        0,0334 na fase densa (mais do que os 0,003 do controlo
        da k variável: sem decaimento nem amplificação, o
        cluster concentra menos)."""
        rel = rodar_party_causal_pomdp_richclub(raio=float("inf"))
        ev = rel["eventos"]
        self.assertEqual(ev["simbolo_tick"], 32)
        self.assertEqual(ev["tentativas_simbolo"], 11)
        self.assertEqual(ev["ren_verdadeiro"], 28)
        self.assertEqual(ev["ren_falso"], 1)
        self.assertEqual(ev["veyra_verdadeiro"], 6)
        self.assertEqual(rel["checkpoints"][-1]["n_arestas"], 9)
        self.assertEqual(rel["checkpoints"][-1]["isc_local"], 0.9)
        self.assertEqual(ev["vetos_estado"], [])
        self.assertEqual(ev["vetos_tick"], [])
        self.assertEqual(rel["ticks_tiranicos"], [])
        self.assertTrue(rel["criterios"]["simbolo_valido"])
        self.assertTrue(rel["criterios"]["simbolo_valido_tick"])
        self.assertEqual(rel["jsd_richclub_k_min"], 0.117)
        self.assertEqual(rel["jsd_richclub_k_min_tick"], 7)
        self.assertEqual(rel["jsd_richclub_k_final"], 0.1788)
        margens = rel["margens_bairro"]
        self.assertEqual(margens["k_variavel"]["folga_min_acima"], 0.0334)
        self.assertEqual(margens["k_variavel"]["n_ticks_densos"], 10)
        self.assertEqual(margens["k_fixo_4"]["folga_min_acima"], 0.0067)

    def test_sonda(self):
        linhas = sondar_pomdp_richclub()
        self.assertEqual([l["raio"] for l in linhas], [1, 2, float("inf")])
        self.assertEqual(
            [l["simbolo_tick"] for l in linhas], [None, 26, 32]
        )
        self.assertEqual(
            [l["ren_verdadeiro"] for l in linhas], [33, 29, 28]
        )
        self.assertEqual(
            [l["isc_final"] for l in linhas], [0.8, 1.0, 0.9]
        )
        # O portão novo não veta em nenhum raio — e o antigo
        # também não (é a POMDP).
        self.assertEqual(
            [l["vetos_estado"] for l in linhas], [0, 0, 0]
        )
        self.assertEqual(
            [l["vetos_tick"] for l in linhas], [0, 0, 0]
        )
        self.assertEqual(
            [l["vetos_estado_antigo"] for l in linhas], [[], [], []]
        )
        self.assertEqual(
            [l["simbolo_valido"] for l in linhas], [False, True, True]
        )
        self.assertEqual(
            [l["simbolo_valido_tick"] for l in linhas], [False, True, True]
        )

    def test_determinismo(self):
        """Duas sondas completas dão os mesmos números."""
        self.assertEqual(sondar_pomdp_richclub(), sondar_pomdp_richclub())

    def test_sonda_pomdp_intacta(self):
        """A sonda da POMDP continua a dar os mesmos números
        depois desta variante."""
        linhas = sondar_pomdp()
        self.assertEqual(
            [l["simbolo_tick"] for l in linhas], [None, 26, 32]
        )
        self.assertEqual(
            [l["vetos_estado"] for l in linhas], [0, 0, 0]
        )


if __name__ == "__main__":
    unittest.main()
