"""Testes da variante SEGUNDO CRITÉRIO do cenário Isekai Zero
— A Party Causal.

Roda com: python3 -m unittest discover -s testes -v

Os valores dourados são o resultado registado da corrida com a
semente canónica (SEMENTE = 20261124) e FATOR_DECAIMENTO = 0,95:
se mudarem, alguma coisa na variante mudou — é regressão, não
ruído (o RNG tem semente fixa).

O resultado central desta variante é a resposta à pergunta que
a k variável deixou aberta: com um SEGUNDO CRITÉRIO — a quota
dos top-k — em conjunção com o JSD rich-club k(n), o controlo
separa-se COM MARGEM? A resposta é SIM no controlo e NÃO no
hub: a quota do controlo fica abaixo do limiar com folga
mínima 0,0433 (14x a folga do JSD, 0,003), mas a quota do hub
oscila à volta do limiar — a conjunção DESFAZ o veto a 1,05
(Símbolo válido) e deixa de nascer tirânico a 1,50 (primeiro
veto reclamado no tick 25, não no 17). O penhasco, o outro
candidato, nunca dispara em nenhum nível.
"""

import unittest

from cono_gym.causal import jsd_bits, prototipo_tirania
from cono_gym.espectro import LIMIAR_ISC, LIMIAR_VAR
from cono_gym.grafo import GrafoCausal, UIF
from cono_gym.party_causal import rodar_party_causal
from cono_gym.party_causal_veto_estado import (
    JSD_ESTADO,
    MIN_ARESTAS_JSD,
)
from cono_gym.party_causal_sora import (
    FATOR_AMPLIFICACAO,
    JOELHO_AMPLIFICACAO,
)
from cono_gym.party_causal_richclub import (
    JSD_RC_ESTADO,
    RICHCLUB_K,
    jsd_pesos_richclub,
    prototipo_richclub,
)
from cono_gym.party_causal_k_variavel import (
    TABELA_CALIBRACAO,
    jsd_pesos_richclub_k,
    k_variavel,
    limiar_estado_k,
    rodar_party_causal_k_variavel,
    sondar_k_variavel,
)
from cono_gym.party_causal_segundo_criterio import (
    TABELA_CALIBRACAO_2C,
    limiar_penhasco,
    limiar_quota,
    penhasco,
    quota_topk,
    rodar_party_causal_segundo_criterio,
    sondar_segundo_criterio,
)


def _grafo_pesos(n, pesos):
    """Grafo com n arestas e os pesos dados (só os pesos
    importam para a quota, o penhasco e a JSD — a topologia é
    uma cadeia de pares distintos)."""
    g = GrafoCausal()
    hs = []
    for i in range(n):
        u = UIF(serial=f"s{i}", tipo_agente="no", funcao_s=f"s-{i}")
        g.adicionar_uif(u)
        hs.append(u.hash_uif)
    pares = [(i, j) for i in range(n) for j in range(i + 1, n)][:n]
    for (a, b), p in zip(pares, pesos):
        g.depositar_rastro(hs[a], hs[b], "teste", p)
    return g


def _grafo_hub_perfeito(n):
    """Hub perfeito com k(n) arestas fortes: os top-k partilham
    0,9 e o resto partilha 0,1 — o protótipo rich-club como
    pesos reais. A quota é 0,9 e o JSD rich-club k(n) é 0,0."""
    k = k_variavel(n)
    pesos = [0.9 / k] * k + [0.1 / (n - k)] * (n - k)
    return _grafo_pesos(n, pesos)


def _grafo_uniforme(n):
    """Cluster uniforme: todas as arestas com o mesmo peso. A
    quota é k/n e o penhasco é 1,0."""
    return _grafo_pesos(n, [1.0] * n)


class TesteCalibracao(unittest.TestCase):
    def test_tabela_calibracao_2c(self):
        # A tabela inteira, medida: k(n), limiar do JSD, limiar
        # da quota e limiar do penhasco, por n.
        self.assertEqual(
            TABELA_CALIBRACAO_2C,
            {
                5: (2, 0.1509, 0.5476, 2.1565),
                6: (2, 0.1708, 0.5372, 2.8281),
                7: (3, 0.1157, 0.6182, 2.7164),
                8: (3, 0.1323, 0.6020, 3.2247),
                9: (3, 0.1454, 0.5912, 3.7255),
                10: (4, 0.1129, 0.6363, 3.4222),
            },
        )
        # A coluna do JSD é a tabela da k variável.
        for n in range(5, 11):
            self.assertEqual(TABELA_CALIBRACAO_2C[n][0], TABELA_CALIBRACAO[n][0])
            self.assertEqual(TABELA_CALIBRACAO_2C[n][1], TABELA_CALIBRACAO[n][1])

    def test_limiar_quota_entre_uniforme_e_prototipo(self):
        # O limiar tem de ficar entre o uniforme (k/n) e o
        # protótipo (0,9) em todos os n — a mesma condição que
        # levou ao 0,113: se ficasse abaixo do uniforme, até um
        # cluster uniforme seria "tirânico".
        for n in range(5, 11):
            k = k_variavel(n)
            self.assertGreater(limiar_quota(n), k / n)
            self.assertLess(limiar_quota(n), 0.9)
            self.assertGreater(limiar_quota(n), 0.0)

    def test_limiar_penhasco_entre_uniforme_e_prototipo(self):
        # O mesmo, em escala log: o penhasco do uniforme é 1 e
        # o do protótipo é 9(n-k)/k.
        for n in range(5, 11):
            k = k_variavel(n)
            self.assertGreater(limiar_penhasco(n), 1.0)
            self.assertLess(limiar_penhasco(n), 9.0 * (n - k) / k)

    def test_hub_perfeito_mede_quota_09_e_jsd_zero(self):
        # O hub perfeito é o protótipo como pesos reais: quota
        # 0,9, JSD rich-club k(n) 0,0 e penhasco 9(n-k)/k — em
        # todos os n, porque o protótipo varia com n.
        for n in range(5, 11):
            g = _grafo_hub_perfeito(n)
            k = k_variavel(n)
            self.assertAlmostEqual(quota_topk(g), 0.9, places=3)
            self.assertAlmostEqual(jsd_pesos_richclub_k(g), 0.0, places=3)
            self.assertAlmostEqual(penhasco(g), 9.0 * (n - k) / k, places=3)
            self.assertGreater(quota_topk(g), limiar_quota(n))
            self.assertGreater(penhasco(g), limiar_penhasco(n))

    def test_uniforme_mede_quota_k_sobre_n_e_penhasco_1(self):
        # O uniforme é o outro extremo: quota k/n e penhasco
        # 1,0 — e fica sempre do lado limpo dos dois limiares.
        for n in range(5, 11):
            g = _grafo_uniforme(n)
            k = k_variavel(n)
            self.assertAlmostEqual(quota_topk(g), k / n, places=3)
            self.assertAlmostEqual(penhasco(g), 1.0, places=3)
            self.assertLess(quota_topk(g), limiar_quota(n))
            self.assertLess(penhasco(g), limiar_penhasco(n))

    def test_quota_e_penhasco_sem_arestas(self):
        g = GrafoCausal()
        self.assertIsNone(quota_topk(g))
        self.assertIsNone(penhasco(g))
        self.assertIsNone(jsd_pesos_richclub_k(g))


class TesteControlo(unittest.TestCase):
    def test_fator_1_reproduz_a_k_variavel_na_dinamica(self):
        # A variante só troca o portão — a dinâmica (agentes,
        # RNG, amplificação, decaimento) é a da k variável, tick
        # a tick: ISC, VarPn, Gini, JSD ordenado e JSD rich-club
        # k(n) por checkpoint são idênticos, e os vetos por
        # tentativa também.
        var = rodar_party_causal_segundo_criterio(fator_amplificacao=1.00)
        ref = rodar_party_causal_k_variavel(fator_amplificacao=1.00)
        for b, v in zip(ref["checkpoints"], var["checkpoints"]):
            self.assertEqual(b["isc_local"], v["isc_local"])
            self.assertEqual(b["var_ponderada_normalizada"], v["var_ponderada_normalizada"])
            self.assertEqual(b["gini"], v["gini"])
            self.assertEqual(b["jsd_ordenado"], v["jsd_ordenado"])
            self.assertEqual(b["jsd_richclub_k"], v["jsd_richclub_k"])
            self.assertEqual(b["jsd_richclub"], v["jsd_richclub"])
        self.assertEqual(var["eventos"]["simbolo_tick"], 32)
        self.assertEqual(var["eventos"]["ren_verdadeiro"], 26)
        self.assertEqual(var["eventos"]["ren_falso"], 2)
        self.assertEqual(
            var["eventos"]["depositos_por_agente"],
            {"Ren": 3, "Lira": 30, "Kael": 19, "Sora": 31, "Veyra": 3},
        )
        self.assertEqual(var["eventos"]["vetos"], [])
        self.assertEqual(var["alavanca"]["total_amplificacoes"], 0)
        self.assertFalse(var["criterios"]["sora_amplificou"])

    def test_o_controlo_separa_com_margem_pela_quota(self):
        # A pergunta que a variante existe para responder: na
        # fase densa do controlo a quota fica sempre abaixo do
        # limiar, com folga mínima 0,0433 (tick 37, 0,593 contra
        # 0,6363) — 14x a folga do JSD (0,003). A conjunção não
        # inventa vetos no controlo: 0 por tick e 0 por
        # checkpoint, Símbolo válido por ambos os portões.
        var = rodar_party_causal_segundo_criterio(fator_amplificacao=1.00)
        self.assertEqual(var["ticks_tiranicos"], [])
        self.assertEqual(var["ticks_quota"], [])
        self.assertEqual(var["ticks_penhasco"], [])
        self.assertEqual(var["eventos"]["vetos_tick"], [])
        self.assertEqual(var["eventos"]["vetos_estado"], [])
        self.assertTrue(var["criterios"]["simbolo_valido"])
        self.assertTrue(var["criterios"]["simbolo_valido_checkpoint"])
        self.assertTrue(var["criterios"]["simbolo_valido_tick"])
        self.assertFalse(var["criterios"]["veredicto_muda"])
        self.assertFalse(var["criterios"]["segundo_criterio_disparou"])
        self.assertFalse(var["criterios"]["penhasco_dispararia"])
        margens = var["margens_dois_criterios"]
        self.assertAlmostEqual(margens["jsd_richclub_k"]["folga_min_acima"], 0.003, places=3)
        self.assertAlmostEqual(margens["quota_topk"]["folga_min_acima"], 0.0433, places=3)
        self.assertIsNone(margens["jsd_richclub_k"]["profundidade_max_veto"])
        self.assertIsNone(margens["quota_topk"]["profundidade_max_veto"])
        self.assertGreater(
            margens["quota_topk"]["folga_min_acima"],
            10 * margens["jsd_richclub_k"]["folga_min_acima"],
        )
        traj = {t["tick"]: t for t in var["trajetoria"]}
        self.assertAlmostEqual(traj[37]["quota_topk"], 0.593, places=3)
        self.assertEqual(traj[37]["limiar_quota"], 0.6363)
        self.assertAlmostEqual(
            traj[37]["limiar_quota"] - traj[37]["quota_topk"], 0.0433, places=3
        )
        # A quota do controlo por tick, na fase densa.
        self.assertEqual(
            [traj[t]["quota_topk"] for t in range(32, 41)],
            [0.4944, 0.5106, 0.5141, 0.522, 0.5289, 0.593, 0.5905, 0.5838, 0.5846],
        )

    def test_base_intacta_depois_da_variante(self):
        rodar_party_causal_segundo_criterio()
        base = rodar_party_causal()
        self.assertEqual(base["eventos"]["simbolo_tick"], 32)


class TesteCorrida(unittest.TestCase):
    def test_deterministica(self):
        a = rodar_party_causal_segundo_criterio()
        b = rodar_party_causal_segundo_criterio()
        self.assertEqual(a, b)

    def test_outra_semente_muda_o_resultado(self):
        a = rodar_party_causal_segundo_criterio()
        b = rodar_party_causal_segundo_criterio(semente=1)
        self.assertNotEqual(a["checkpoints"], b["checkpoints"])

    def test_limiares_canonicos_usados(self):
        self.assertEqual(LIMIAR_ISC, 0.85)
        self.assertEqual(LIMIAR_VAR, 0.36)
        self.assertEqual(JSD_ESTADO, 0.28)
        self.assertEqual(MIN_ARESTAS_JSD, 5)
        self.assertEqual(FATOR_AMPLIFICACAO, 1.10)
        self.assertEqual(JOELHO_AMPLIFICACAO, 1.053)
        self.assertEqual(RICHCLUB_K, 4)
        self.assertEqual(JSD_RC_ESTADO, 0.113)
        rel = rodar_party_causal_segundo_criterio()
        for c in rel["checkpoints"]:
            self.assertEqual(
                c["simbolo"],
                c["isc_local"] >= 0.85 and c["var_ponderada_normalizada"] <= 0.36,
            )

    def test_resultado_dourado_semente_canonica(self):
        rel = rodar_party_causal_segundo_criterio()
        ev = rel["eventos"]
        self.assertEqual(ev["simbolo_tick"], 28)
        self.assertEqual(ev["ren_verdadeiro"], 28)
        self.assertEqual(ev["ren_falso"], 0)
        self.assertEqual(ev["veyra_verdadeiro"], 3)
        self.assertEqual(ev["tentativas_simbolo"], 10)
        self.assertEqual(
            ev["depositos_por_agente"],
            {"Ren": 2, "Lira": 32, "Kael": 16, "Sora": 29, "Veyra": 13},
        )
        self.assertEqual([v["tick"] for v in ev["vetos_estado"]], [30, 40])
        self.assertEqual(
            [v["tick"] for v in ev["vetos_tick"]],
            [28, 29, 30, 31, 32, 36, 37, 38, 39, 40],
        )
        self.assertEqual(rel["comparacao"]["primeiro_veto_tick"], 28)
        self.assertEqual(rel["comparacao"]["primeiro_veto_tick_reclamado"], 28)
        self.assertEqual(rel["comparacao"]["primeiro_veto_checkpoint_reclamado"], 30)
        self.assertTrue(rel["comparacao"]["simbolo_nasce_tiranico"])
        self.assertFalse(rel["criterios"]["simbolo_valido"])
        self.assertFalse(rel["criterios"]["simbolo_valido_tick"])
        self.assertFalse(rel["criterios"]["veredicto_muda"])
        self.assertEqual(
            rel["ticks_tiranicos"],
            [28, 29, 30, 31, 32, 36, 37, 38, 39, 40],
        )
        self.assertEqual(rel["ticks_tiranicos_jsd"], list(range(23, 41)))
        self.assertEqual(rel["ticks_quota"], rel["ticks_tiranicos"])
        self.assertEqual(rel["ticks_penhasco"], [])
        self.assertTrue(rel["criterios"]["segundo_criterio_disparou"])
        self.assertFalse(rel["criterios"]["penhasco_dispararia"])
        self.assertAlmostEqual(rel["quota_max"], 0.6838, places=3)
        self.assertEqual(rel["quota_max_tick"], 31)
        self.assertAlmostEqual(rel["penhasco_max"], 2.0946, places=3)
        self.assertEqual(rel["penhasco_max_tick"], 28)
        # A janela é intermitente: os buracos 33–35 estão na
        # lista do JSD sozinho mas não na da conjunção.
        for t in (33, 34, 35):
            self.assertIn(t, rel["ticks_tiranicos_jsd"])
            self.assertNotIn(t, rel["ticks_tiranicos"])

    def test_a_quota_tem_o_seu_proprio_bairro(self):
        # A honestidade do segundo critério: a folga mínima da
        # quota a 1,10 é 0,0021 (tick 27, 0,5891 contra 0,5912)
        # — mais fina do que a do JSD no controlo. A quota
        # separa o controlo, mas o hub oscila à volta do limiar.
        rel = rodar_party_causal_segundo_criterio()
        margens = rel["margens_dois_criterios"]
        self.assertAlmostEqual(margens["quota_topk"]["folga_min_acima"], 0.0021, places=3)
        self.assertAlmostEqual(margens["quota_topk"]["profundidade_max_veto"], 0.0475, places=3)
        traj = {t["tick"]: t for t in rel["trajetoria"]}
        self.assertAlmostEqual(traj[27]["quota_topk"], 0.5891, places=3)
        self.assertEqual(traj[27]["limiar_quota"], 0.5912)

    def test_criterios_da_base_continuam_a_passar(self):
        rel = rodar_party_causal_segundo_criterio()
        crit = rel["criterios"]
        self.assertTrue(crit["simbolo_formado"])
        self.assertTrue(crit["sucesso_parcial"])
        self.assertTrue(crit["sucesso_completo"])
        self.assertGreaterEqual(rel["jsd_min"], 0.22)
        self.assertGreaterEqual(rel["jsd_final"], 0.28)

    def test_jsd_canonico_e_h_causal_indefinidos(self):
        rel = rodar_party_causal_segundo_criterio()
        for c in rel["checkpoints"]:
            self.assertIsNone(c["jsd_canonico"])
            self.assertIsNone(c["h_causal"])

    def test_avaliacao_final_sem_checkpoint(self):
        # n_ticks = 25 não é múltiplo de 10: a avaliação final
        # corre fora dos checkpoints, sem dupla contagem e sem
        # rebentar. Sob a conjunção nada dispara — os vetos do
        # JSD sozinho nos ticks 23–25 não disparam porque a
        # quota está abaixo do limiar (0,5607 / 0,5748 / 0,5708
        # contra 0,5912) — e o Símbolo ainda não foi reclamado
        # (só no tick 28).
        rel = rodar_party_causal_segundo_criterio(n_ticks=25)
        self.assertEqual(len(rel["checkpoints"]), 2)
        self.assertEqual(rel["eventos"]["vetos_estado"], [])
        self.assertEqual(rel["eventos"]["vetos_tick"], [])
        self.assertEqual(rel["ticks_tiranicos"], [])
        self.assertEqual(rel["ticks_tiranicos_jsd"], [23, 24, 25])
        self.assertIsNone(rel["eventos"]["simbolo_tick"])
        self.assertFalse(rel["criterios"]["simbolo_valido"])
        self.assertFalse(rel["criterios"]["simbolo_valido_tick"])


class TesteComparacao(unittest.TestCase):
    def test_a_1_05_o_simbolo_passa_a_ser_valido(self):
        # A 1,05 a quota nunca dispara na fase densa (máximo
        # 0,5687 contra limiar 0,5912, folga mínima 0,0225) —
        # a conjunção tem 0 vetos e o Símbolo (tick 25) passa a
        # ser VÁLIDO, quando sob o JSD sozinho era inválido. O
        # segundo critério DESFAZ um veto.
        rel = rodar_party_causal_segundo_criterio(fator_amplificacao=1.05)
        self.assertEqual(rel["eventos"]["simbolo_tick"], 25)
        self.assertEqual(rel["ticks_quota"], [])
        self.assertEqual(rel["ticks_tiranicos"], [])
        self.assertEqual(rel["eventos"]["vetos_estado"], [])
        self.assertEqual(rel["eventos"]["vetos_tick"], [])
        self.assertTrue(rel["criterios"]["simbolo_valido"])
        self.assertTrue(rel["criterios"]["simbolo_valido_tick"])
        self.assertFalse(rel["criterios"]["veredicto_muda"])
        self.assertFalse(rel["criterios"]["segundo_criterio_disparou"])
        margens = rel["margens_dois_criterios"]
        self.assertAlmostEqual(margens["quota_topk"]["folga_min_acima"], 0.0225, places=3)
        self.assertIsNone(margens["quota_topk"]["profundidade_max_veto"])
        self.assertAlmostEqual(rel["quota_max"], 0.6046, places=3)
        self.assertEqual(rel["quota_max_tick"], 11)

    def test_a_1_50_o_simbolo_ja_nao_nasce_tiranico(self):
        # A 1,50 o primeiro veto por tick reclamado é o tick 25
        # — o primeiro tick a n = 10 com a quota acima do
        # limiar — e não o 17, o tick do Símbolo. Só há 1 veto
        # por checkpoint (tick 30) em vez de 3: o tick 20 escapa
        # porque a quota está a 0,5373 (limiar 0,5912) e o tick
        # 40 escapa por 0,0001 (0,6362 contra 0,6363).
        rel = rodar_party_causal_segundo_criterio(fator_amplificacao=1.50)
        self.assertEqual(rel["eventos"]["simbolo_tick"], 17)
        self.assertEqual([v["tick"] for v in rel["eventos"]["vetos_estado"]], [30])
        self.assertEqual(
            [v["tick"] for v in rel["eventos"]["vetos_tick"]],
            [25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 38, 39],
        )
        self.assertEqual(rel["comparacao"]["primeiro_veto_tick"], 25)
        self.assertEqual(rel["comparacao"]["primeiro_veto_tick_reclamado"], 25)
        self.assertEqual(rel["comparacao"]["primeiro_veto_checkpoint_reclamado"], 30)
        self.assertFalse(rel["comparacao"]["simbolo_nasce_tiranico"])
        self.assertFalse(rel["criterios"]["simbolo_valido"])
        self.assertFalse(rel["criterios"]["simbolo_valido_tick"])
        traj = {t["tick"]: t for t in rel["trajetoria"]}
        self.assertAlmostEqual(traj[40]["quota_topk"], 0.6362, places=3)
        self.assertEqual(traj[40]["limiar_quota"], 0.6363)
        self.assertAlmostEqual(
            traj[40]["limiar_quota"] - traj[40]["quota_topk"], 0.0001, places=3
        )
        self.assertAlmostEqual(
            rel["margens_dois_criterios"]["quota_topk"]["folga_min_acima"],
            0.0001,
            places=3,
        )

    def test_nasce_tiranico_a_1_10_e_1_20(self):
        # A 1,10 e a 1,20 o Símbolo continua a nascer tirânico:
        # o primeiro veto reclamado é o próprio tick do Símbolo.
        for fator, simbolo in ((1.10, 28), (1.20, 21)):
            rel = rodar_party_causal_segundo_criterio(fator_amplificacao=fator)
            self.assertEqual(rel["eventos"]["simbolo_tick"], simbolo)
            self.assertEqual(
                rel["comparacao"]["primeiro_veto_tick_reclamado"], simbolo
            )
            self.assertTrue(rel["comparacao"]["simbolo_nasce_tiranico"])

    def test_a_1_20_a_janela_tambem_e_intermitente(self):
        # A 1,20 a conjunção dispara em 20, 21, 27 e 29–40 — com
        # buracos em 22–26 e 28, que estão na lista do JSD
        # sozinho. São 15 vetos por tick e 3 por checkpoint.
        rel = rodar_party_causal_segundo_criterio(fator_amplificacao=1.20)
        self.assertEqual(
            rel["ticks_tiranicos"],
            [20, 21, 27, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40],
        )
        self.assertEqual(rel["ticks_tiranicos_jsd"], list(range(20, 41)))
        self.assertEqual(len(rel["eventos"]["vetos_tick"]), 15)
        self.assertEqual(len(rel["eventos"]["vetos_estado"]), 3)
        for t in (22, 23, 24, 25, 26, 28):
            self.assertIn(t, rel["ticks_tiranicos_jsd"])
            self.assertNotIn(t, rel["ticks_tiranicos"])

    def test_o_penhasco_nunca_dispara_em_nenhum_nivel(self):
        # O outro candidato, testado e descartado: o penhasco
        # calibrado na mesma posição relativa nunca chega ao
        # limiar em nenhum nível — o máximo da sonda é 2,646
        # (a 1,20, contra limiar 3,4222). E a 1,50, ticks 19–24,
        # o penhasco k = 3 é exactamente 1,0: o hub tem QUATRO
        # arestas fortes mas k(9) = 3, por isso w_3 = w_4 = 0,95
        # e não há penhasco nenhum para medir.
        for fator in (1.00, 1.05, 1.10, 1.20, 1.50):
            rel = rodar_party_causal_segundo_criterio(fator_amplificacao=fator)
            self.assertEqual(rel["ticks_penhasco"], [])
            self.assertFalse(rel["criterios"]["penhasco_dispararia"])
        rel = rodar_party_causal_segundo_criterio(fator_amplificacao=1.20)
        self.assertAlmostEqual(rel["penhasco_max"], 2.646, places=3)
        rel = rodar_party_causal_segundo_criterio(fator_amplificacao=1.50)
        traj = {t["tick"]: t for t in rel["trajetoria"]}
        for t in range(19, 25):
            self.assertEqual(traj[t]["penhasco"], 1.0)
            self.assertEqual(traj[t]["k"], 3)

    def test_vetos_tick_sao_os_ticks_tiranicos(self):
        # Cheque de consistência entre o portão e a trajetória:
        # os ticks dos vetos por tick são exactamente os ticks
        # tirânicos da CONJUNÇÃO, em todos os níveis.
        for fator in (1.00, 1.05, 1.10, 1.20, 1.50):
            rel = rodar_party_causal_segundo_criterio(fator_amplificacao=fator)
            self.assertEqual(
                [v["tick"] for v in rel["eventos"]["vetos_tick"]],
                rel["ticks_tiranicos"],
            )

    def test_dinamica_identica_a_k_variavel(self):
        # A variante só troca o portão — a dinâmica é a da k
        # variável, tick a tick, em todos os níveis.
        for fator in (1.00, 1.05, 1.10, 1.50):
            sc = rodar_party_causal_segundo_criterio(fator_amplificacao=fator)
            kv = rodar_party_causal_k_variavel(fator_amplificacao=fator)
            self.assertEqual(
                sc["eventos"]["simbolo_tick"], kv["eventos"]["simbolo_tick"]
            )
            self.assertEqual(
                sc["eventos"]["depositos_por_agente"],
                kv["eventos"]["depositos_por_agente"],
            )
            self.assertEqual(
                sc["eventos"]["seguimentos_por_agente"],
                kv["eventos"]["seguimentos_por_agente"],
            )
            self.assertEqual(
                sc["alavanca"]["total_amplificacoes"],
                kv["alavanca"]["total_amplificacoes"],
            )
            self.assertEqual(sc["pesos_finais"], kv["pesos_finais"])
            self.assertEqual(
                [(t["n_arestas"], t["isc_local"]) for t in sc["trajetoria"]],
                [(t["n_arestas"], t["isc_local"]) for t in kv["trajetoria"]],
            )
            self.assertEqual(
                [t["jsd_richclub_k"] for t in sc["trajetoria"]],
                [t["jsd_richclub_k"] for t in kv["trajetoria"]],
            )


class TesteSonda(unittest.TestCase):
    def test_dose_resposta_dourada(self):
        linhas = {l["fator"]: l for l in sondar_segundo_criterio()}
        dourado = {
            # fator: (simbolo, ckpt, tick, primeiro_tick, valido, valido_tick, muda, conjuncao)
            1.00: (32, 0, 0, None, True, True, False, []),
            1.05: (25, 0, 0, None, True, True, False, []),
            1.10: (28, 2, 10, 28, False, False, False,
                   [28, 29, 30, 31, 32, 36, 37, 38, 39, 40]),
            1.20: (21, 3, 15, 20, False, False, False,
                   [20, 21, 27, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40]),
            1.50: (17, 1, 12, 25, False, False, False,
                   [25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 38, 39]),
        }
        for fator, (simbolo, ckpt, tick, primeiro, valido, valido_tick, muda, conj) in dourado.items():
            linha = linhas[fator]
            self.assertEqual(linha["simbolo_tick"], simbolo)
            self.assertEqual(linha["vetos_estado"], ckpt)
            self.assertEqual(linha["vetos_tick"], tick)
            self.assertEqual(linha["primeiro_veto_tick"], primeiro)
            self.assertEqual(linha["simbolo_valido"], valido)
            self.assertEqual(linha["simbolo_valido_tick"], valido_tick)
            self.assertEqual(linha["veredicto_muda"], muda)
            self.assertEqual(linha["ticks_tiranicos"], conj)

    def test_o_tick_apanha_antes_ou_ao_mesmo_tempo_que_o_checkpoint(self):
        # O portão por tick continua a chegar antes do de
        # checkpoint nos níveis amplificados — a conjunção não
        # lhe tirou a granularidade: a 1,10 chega no tick 28
        # contra 30 do checkpoint; a 1,50 no 25 contra 30.
        linhas = {l["fator"]: l for l in sondar_segundo_criterio()}
        for fator in (1.10, 1.20, 1.50):
            self.assertLessEqual(
                linhas[fator]["primeiro_veto_tick"],
                linhas[fator]["primeiro_veto_checkpoint"],
            )
        self.assertEqual(linhas[1.10]["primeiro_veto_tick"], 28)
        self.assertEqual(linhas[1.10]["primeiro_veto_checkpoint"], 30)
        self.assertEqual(linhas[1.50]["primeiro_veto_tick"], 25)
        self.assertEqual(linhas[1.50]["primeiro_veto_checkpoint"], 30)

    def test_quota_maxima_por_nivel(self):
        # A quota máxima é atingida na fase esparsa (tick 11) a
        # 1,05 e a 1,50 — é a condição ISC >= 0,85 que impede o
        # portão de disparar aí, não a quota. Na fase densa o
        # máximo fica a 1,20 (0,6873, tick 36).
        linhas = {l["fator"]: l for l in sondar_segundo_criterio()}
        self.assertAlmostEqual(linhas[1.00]["quota_max"], 0.593, places=3)
        self.assertEqual(linhas[1.00]["quota_max_tick"], 37)
        self.assertAlmostEqual(linhas[1.05]["quota_max"], 0.6046, places=3)
        self.assertEqual(linhas[1.05]["quota_max_tick"], 11)
        self.assertAlmostEqual(linhas[1.10]["quota_max"], 0.6838, places=3)
        self.assertEqual(linhas[1.10]["quota_max_tick"], 31)
        self.assertAlmostEqual(linhas[1.20]["quota_max"], 0.6873, places=3)
        self.assertEqual(linhas[1.20]["quota_max_tick"], 36)
        self.assertAlmostEqual(linhas[1.50]["quota_max"], 0.6914, places=3)
        self.assertEqual(linhas[1.50]["quota_max_tick"], 11)
