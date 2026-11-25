"""Testes da variante K VARIÁVEL COM n do cenário Isekai Zero
— A Party Causal.

Roda com: python3 -m unittest discover -s testes -v

Os valores dourados são o resultado registado da corrida com a
semente canónica (SEMENTE = 20261124) e FATOR_DECAIMENTO = 0,95:
se mudarem, alguma coisa na variante mudou — é regressão, não
ruído (o RNG tem semente fixa).

O resultado central desta variante é a resposta à pergunta que
a vigilância por tick deixou aberta: com k a variar com n —
k(n) = ceil(n/3), o rich club como o terço superior das
arestas — e o limiar recalibrado por n, o limiar sai do bairro
concorrido? A resposta é NÃO como alívio e SIM como veredicto:
o CONTROLO (1,00) deixa de mudar de veredicto — 0 vetos por
tick, válido por tick e por checkpoint — porque a n = 9 a
medida sobe ~0,06 (0,0997 -> 0,1643 no tick 32) enquanto o
limiar sobe só ~0,03 (0,113 -> 0,1454): o transiente escapa.
Mas a folga mínima acima do limiar na fase densa continua a
ser 0,003 (tick 37, 0,1159 contra 0,1129) — o bairro não
aliviou, mudou de lado: o limiar passou para lá do transiente,
e o cluster continua a roçar nele. Nos níveis amplificados os
Símbolos continuam inválidos por ambos os portões, mas a 1,05
o Símbolo já não nasce tirânico (o primeiro veto reclamado é
o tick 26, um depois do Símbolo no tick 25).
"""

import math
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
from cono_gym.party_causal_vigilia_tick import (
    rodar_party_causal_vigilia_tick,
)
from cono_gym.party_causal_k_variavel import (
    TABELA_CALIBRACAO,
    jsd_pesos_richclub_k,
    k_variavel,
    limiar_estado_k,
    prototipo_richclub_k,
    rodar_party_causal_k_variavel,
    sondar_k_variavel,
)


def _grafo_hub_4(n):
    """Grafo com n arestas: um hub perfeito de 4 arestas fortes
    (0,9/4 cada) e o resto fraco (0,1/(n-4) cada). Só os pesos
    importam para a JSD — a topologia é uma cadeia de pares
    distintos."""
    g = GrafoCausal()
    hs = []
    for i in range(n):
        u = UIF(serial=f"h{i}", tipo_agente="no", funcao_s=f"h-{i}")
        g.adicionar_uif(u)
        hs.append(u.hash_uif)
    pesos = [0.9 / 4] * 4 + [0.1 / (n - 4)] * (n - 4)
    pares = [(i, j) for i in range(n) for j in range(i + 1, n)][:n]
    for (a, b), p in zip(pares, pesos):
        g.depositar_rastro(hs[a], hs[b], "hub", p)
    return g


class TesteCalibracao(unittest.TestCase):
    def test_regra_k_tabela(self):
        # k(n) = ceil(n/3): o rich club é o terço superior.
        self.assertEqual(
            {n: k_variavel(n) for n in range(5, 11)},
            {5: 2, 6: 2, 7: 3, 8: 3, 9: 3, 10: 4},
        )
        self.assertEqual(k_variavel(2), 1)
        self.assertEqual(k_variavel(3), 1)
        self.assertEqual(k_variavel(4), 2)
        for n in range(2, 11):
            self.assertGreaterEqual(k_variavel(n), 1)
            self.assertLess(k_variavel(n), n)

    def test_limiar_10_reproduz_o_richclub_antigo(self):
        # Regressão da recalibração: a n = 10 o protótipo com
        # k(n) É o rich-club k = 4 antigo, e o limiar é o 0,113
        # a menos do arredondamento.
        self.assertEqual(prototipo_richclub_k(10), prototipo_richclub(10, 4))
        self.assertEqual(prototipo_richclub_k(10), prototipo_richclub(10, RICHCLUB_K))
        self.assertEqual(limiar_estado_k(10), 0.1129)
        self.assertAlmostEqual(limiar_estado_k(10), JSD_RC_ESTADO, places=2)
        self.assertEqual(TABELA_CALIBRACAO[10], (4, 0.1129))

    def test_tabela_calibracao(self):
        # A tabela inteira, medida: k(n) e o limiar por n.
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

    def test_limiar_abaixo_do_uniforme_em_todos_os_n(self):
        # O limiar tem de ficar abaixo do JSD do uniforme, senão
        # até um cluster uniforme seria "tirânico" — a mesma
        # condição que levou ao 0,113.
        for n in range(5, 11):
            u = [1.0 / n] * n
            jsd_uniforme = jsd_bits(u, prototipo_richclub_k(n))
            self.assertLess(limiar_estado_k(n), jsd_uniforme)
            self.assertLess(limiar_estado_k(n), JSD_ESTADO)
            self.assertGreater(limiar_estado_k(n), 0.0)

    def test_k1_reproduz_a_tirania(self):
        # Consistência: com k = 1 o protótipo rich-club é o
        # protótipo de Tirania de um só rastro — e k(3) = 1.
        self.assertEqual(k_variavel(3), 1)
        self.assertEqual(prototipo_richclub_k(3), prototipo_tirania(3))
        self.assertEqual(prototipo_richclub_k(2), prototipo_tirania(2))

    def test_hub_perfeito_mede_zero_a_n10_e_nao_a_n9(self):
        # O preço medido da regra: um hub perfeito de 4 arestas
        # mede 0,0000 a n = 10 (k = 4) mas 0,0893 a n = 9 (k = 3)
        # e 0,0850 a n = 8 — a medida com k(n) é menos sensível
        # ao hub de 4 arestas quando n < 10, porque o protótipo
        # espera 3 dominantes e o hub tem 4. O hub continua a
        # ser apanhado em todos os n (abaixo do limiar), mas com
        # menos margem a n = 9: 0,1454 - 0,0893 = 0,0561, contra
        # 0,1129 a n = 10.
        for n, esperado in ((8, 0.0850), (9, 0.0893), (10, 0.0000)):
            jsd = jsd_pesos_richclub_k(_grafo_hub_4(n))
            self.assertAlmostEqual(jsd, esperado, places=3)
            self.assertLess(jsd, limiar_estado_k(n))
        self.assertAlmostEqual(
            limiar_estado_k(9) - jsd_pesos_richclub_k(_grafo_hub_4(9)),
            0.0561,
            places=3,
        )

    def test_ceil_e_nao_round(self):
        # A escolha documentada: round(n/3) daria k = 3 a n = 10
        # e limiar 0,1560 — não reproduziria o rich-club antigo.
        self.assertEqual(math.ceil(10 / 3), 4)
        self.assertEqual(round(10 / 3), 3)
        u = [0.1] * 10
        limiar_k3 = round(
            JSD_ESTADO
            * jsd_bits(u, prototipo_richclub(10, 3))
            / jsd_bits(u, prototipo_tirania(10)),
            4,
        )
        self.assertEqual(limiar_k3, 0.1560)
        self.assertNotAlmostEqual(limiar_k3, JSD_RC_ESTADO, places=2)


class TesteControlo(unittest.TestCase):
    def test_fator_1_reproduz_a_vigilia_na_dinamica(self):
        # A variante só troca a medida — a dinâmica (agentes,
        # RNG, amplificação, decaimento) é a da vigília, tick a
        # tick: ISC, VarPn, Gini e JSD ordenado por checkpoint
        # são idênticos, e os vetos por tentativa também.
        var = rodar_party_causal_k_variavel(fator_amplificacao=1.00)
        ref = rodar_party_causal_vigilia_tick(fator_amplificacao=1.00)
        for b, v in zip(ref["checkpoints"], var["checkpoints"]):
            self.assertEqual(b["isc_local"], v["isc_local"])
            self.assertEqual(b["var_ponderada_normalizada"], v["var_ponderada_normalizada"])
            self.assertEqual(b["gini"], v["gini"])
            self.assertEqual(b["jsd_ordenado"], v["jsd_ordenado"])
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

    def test_o_controlo_ja_nao_muda_de_veredicto(self):
        # A pergunta que a variante existe para responder: com
        # k(n) o transiente do controlo escapa — 0 vetos por tick
        # e 0 por checkpoint — e o Símbolo é válido por ambos os
        # portões. A mudança de veredicto que a vigília comprou
        # desfaz-se com a medida nova.
        var = rodar_party_causal_k_variavel(fator_amplificacao=1.00)
        self.assertEqual(var["ticks_tiranicos"], [])
        self.assertEqual(var["eventos"]["vetos_tick"], [])
        self.assertEqual(var["eventos"]["vetos_estado"], [])
        self.assertTrue(var["criterios"]["simbolo_valido"])
        self.assertTrue(var["criterios"]["simbolo_valido_checkpoint"])
        self.assertTrue(var["criterios"]["simbolo_valido_tick"])
        self.assertFalse(var["criterios"]["veredicto_muda"])
        self.assertFalse(var["comparacao"]["veredicto_muda"])
        self.assertIsNone(var["comparacao"]["primeiro_veto_checkpoint"])
        self.assertIsNone(var["comparacao"]["primeiro_veto_tick"])
        self.assertIsNone(var["comparacao"]["primeiro_veto_tick_reclamado"])
        self.assertFalse(var["comparacao"]["simbolo_nasce_tiranico"])

    def test_o_transiente_escapa_a_n9(self):
        # O mecanismo, fixado tick a tick: nos ticks 32–36 o
        # cluster tem n = 9, k = 3 e limiar 0,1454. A medida
        # com k(n) sobe ~0,06 face à de k = 4 fixo (0,0997 ->
        # 0,1643 no tick 32) enquanto o limiar sobe só ~0,03
        # (0,113 -> 0,1454) — a medida move-se mais do que o
        # limiar, e o transiente passa para o lado limpo.
        var = rodar_party_causal_k_variavel(fator_amplificacao=1.00)
        traj = {t["tick"]: t for t in var["trajetoria"]}
        self.assertEqual(
            [traj[t]["jsd_richclub_k"] for t in (32, 33, 34, 35, 36)],
            [0.1643, 0.1608, 0.1585, 0.1551, 0.1538],
        )
        self.assertEqual(
            [traj[t]["jsd_richclub"] for t in (32, 33, 34, 35, 36)],
            [0.0997, 0.1031, 0.1045, 0.1039, 0.1044],
        )
        for t in (32, 33, 34, 35, 36):
            self.assertEqual(traj[t]["n_arestas"], 9)
            self.assertEqual(traj[t]["k"], 3)
            self.assertEqual(traj[t]["limiar"], 0.1454)
            self.assertGreater(traj[t]["jsd_richclub_k"], traj[t]["limiar"])
            self.assertLess(traj[t]["jsd_richclub"], JSD_RC_ESTADO)

    def test_o_bairro_nao_aliviou(self):
        # A honestidade do limiar novo: a folga mínima acima do
        # limiar na fase densa do controlo continua a ser 0,003
        # (tick 37, JSDrc_k 0,1159 contra limiar 0,1129) — a
        # mesma ordem da folga com k = 4 fixo (0,0029). O bairro
        # não aliviou, mudou de lado: o limiar passou para lá do
        # transiente, e o cluster continua a roçar nele, agora
        # por cima.
        var = rodar_party_causal_k_variavel(fator_amplificacao=1.00)
        margens = var["margens_bairro"]
        self.assertIsNone(margens["k_variavel"]["profundidade_max_veto"])
        self.assertAlmostEqual(margens["k_variavel"]["folga_min_acima"], 0.003, places=3)
        self.assertEqual(margens["k_variavel"]["n_ticks_densos"], 9)
        self.assertAlmostEqual(margens["k_fixo_4"]["profundidade_max_veto"], 0.0133, places=3)
        self.assertAlmostEqual(margens["k_fixo_4"]["folga_min_acima"], 0.0029, places=3)
        traj = {t["tick"]: t for t in var["trajetoria"]}
        self.assertAlmostEqual(traj[37]["jsd_richclub_k"], 0.1159, places=3)
        self.assertEqual(traj[37]["limiar"], 0.1129)
        self.assertAlmostEqual(
            traj[37]["jsd_richclub_k"] - traj[37]["limiar"], 0.003, places=3
        )

    def test_base_intacta_depois_da_variante(self):
        rodar_party_causal_k_variavel()
        base = rodar_party_causal()
        self.assertEqual(base["eventos"]["simbolo_tick"], 32)


class TesteCorrida(unittest.TestCase):
    def test_deterministica(self):
        a = rodar_party_causal_k_variavel()
        b = rodar_party_causal_k_variavel()
        self.assertEqual(a, b)

    def test_outra_semente_muda_o_resultado(self):
        a = rodar_party_causal_k_variavel()
        b = rodar_party_causal_k_variavel(semente=1)
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
        rel = rodar_party_causal_k_variavel()
        for c in rel["checkpoints"]:
            self.assertEqual(
                c["simbolo"],
                c["isc_local"] >= 0.85 and c["var_ponderada_normalizada"] <= 0.36,
            )

    def test_resultado_dourado_semente_canonica(self):
        rel = rodar_party_causal_k_variavel()
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
            list(range(23, 41)),
        )
        self.assertEqual(rel["comparacao"]["primeiro_veto_tick"], 23)
        self.assertEqual(rel["comparacao"]["primeiro_veto_tick_reclamado"], 28)
        self.assertEqual(rel["comparacao"]["primeiro_veto_checkpoint_reclamado"], 30)
        self.assertTrue(rel["comparacao"]["simbolo_nasce_tiranico"])
        self.assertFalse(rel["criterios"]["simbolo_valido"])
        self.assertFalse(rel["criterios"]["simbolo_valido_tick"])
        self.assertFalse(rel["criterios"]["veredicto_muda"])
        self.assertEqual(rel["ticks_tiranicos"], list(range(23, 41)))
        # No checkpoint 30 o cluster tem n = 9 (k = 3, limiar
        # 0,1454); no 40 tem n = 10 (k = 4, limiar 0,1129).
        self.assertEqual(rel["checkpoints"][2]["n_arestas"], 9)
        self.assertEqual(rel["checkpoints"][2]["k"], 3)
        self.assertEqual(rel["checkpoints"][2]["limiar"], 0.1454)
        self.assertEqual(rel["checkpoints"][3]["n_arestas"], 10)
        self.assertEqual(rel["checkpoints"][3]["k"], 4)
        self.assertEqual(rel["checkpoints"][3]["limiar"], 0.1129)

    def test_criterios_da_base_continuam_a_passar(self):
        rel = rodar_party_causal_k_variavel()
        crit = rel["criterios"]
        self.assertTrue(crit["simbolo_formado"])
        self.assertTrue(crit["sucesso_parcial"])
        self.assertTrue(crit["sucesso_completo"])
        self.assertGreaterEqual(rel["jsd_min"], 0.22)
        self.assertGreaterEqual(rel["jsd_final"], 0.28)

    def test_jsd_canonico_e_h_causal_indefinidos(self):
        rel = rodar_party_causal_k_variavel()
        for c in rel["checkpoints"]:
            self.assertIsNone(c["jsd_canonico"])
            self.assertIsNone(c["h_causal"])

    def test_avaliacao_final_sem_checkpoint(self):
        # n_ticks = 25 não é múltiplo de 10: a avaliação final corre
        # fora dos checkpoints, sem dupla contagem e sem rebentar.
        # O portão por tick apanha 23, 24 e 25; o por checkpoint
        # apanha só o 25 (na avaliação final) — e o Símbolo ainda
        # não foi reclamado (só no tick 28), por isso nenhum dos
        # dois vetos o invalida.
        rel = rodar_party_causal_k_variavel(n_ticks=25)
        self.assertEqual(len(rel["checkpoints"]), 2)
        self.assertEqual([v["tick"] for v in rel["eventos"]["vetos_estado"]], [25])
        self.assertEqual(
            [v["tick"] for v in rel["eventos"]["vetos_tick"]], [23, 24, 25]
        )
        self.assertFalse(rel["eventos"]["vetos_estado"][0]["simbolo_reclamado"])
        self.assertEqual(rel["ticks_tiranicos"], [23, 24, 25])
        self.assertIsNone(rel["eventos"]["simbolo_tick"])
        self.assertFalse(rel["criterios"]["simbolo_valido"])
        self.assertFalse(rel["criterios"]["simbolo_valido_tick"])


class TesteComparacao(unittest.TestCase):
    def test_a_1_05_o_simbolo_ja_nao_nasce_tiranico(self):
        # A 1,05 o primeiro veto por tick reclamado é o tick 26,
        # UM depois do Símbolo (25): o Símbolo já não nasce
        # tirânico com k(n) — na vigília nascia (25). O tick 25
        # não está na lista de vetos: a n = 9 o JSDrc_k ainda
        # está acima do limiar 0,1454 nesse tick.
        rel = rodar_party_causal_k_variavel(fator_amplificacao=1.05)
        self.assertEqual(rel["eventos"]["simbolo_tick"], 25)
        self.assertEqual(rel["comparacao"]["primeiro_veto_tick"], 22)
        self.assertEqual(rel["comparacao"]["primeiro_veto_tick_reclamado"], 26)
        self.assertFalse(rel["comparacao"]["simbolo_nasce_tiranico"])
        self.assertEqual(rel["comparacao"]["vetos_tick"], 18)
        self.assertEqual(rel["comparacao"]["vetos_checkpoint"], 2)
        self.assertFalse(rel["criterios"]["simbolo_valido"])
        self.assertFalse(rel["criterios"]["simbolo_valido_tick"])

    def test_nasce_tiranico_a_1_10_1_20_1_50(self):
        # Nos outros níveis amplificados o Símbolo continua a
        # nascer tirânico: o primeiro veto reclamado é o próprio
        # tick do Símbolo.
        for fator, simbolo in ((1.10, 28), (1.20, 21), (1.50, 17)):
            rel = rodar_party_causal_k_variavel(fator_amplificacao=fator)
            self.assertEqual(rel["eventos"]["simbolo_tick"], simbolo)
            self.assertEqual(
                rel["comparacao"]["primeiro_veto_tick_reclamado"], simbolo
            )
            self.assertTrue(rel["comparacao"]["simbolo_nasce_tiranico"])

    def test_sob_k_variavel_nenhum_simbolo_amplificado_e_valido(self):
        # Nos níveis amplificados nenhum Símbolo é válido por
        # nenhum dos portões — a invalidação mantém-se, só o
        # controlo é que escapa.
        for fator in (1.05, 1.10, 1.20, 1.50):
            rel = rodar_party_causal_k_variavel(fator_amplificacao=fator)
            self.assertFalse(rel["criterios"]["simbolo_valido"])
            self.assertFalse(rel["criterios"]["simbolo_valido_tick"])

    def test_o_veredicto_nao_muda_em_nenhum_nivel(self):
        # Com k(n) o veredicto não muda em nenhum nível da sonda:
        # o controlo é válido pelos dois portões e os amplificados
        # são inválidos pelos dois. A mudança de veredicto que a
        # vigília introduziu desfaz-se por completo.
        linhas = {l["fator"]: l for l in sondar_k_variavel()}
        for fator in (1.00, 1.05, 1.10, 1.20, 1.50):
            self.assertFalse(linhas[fator]["veredicto_muda"])

    def test_vetos_tick_sao_os_ticks_tiranicos(self):
        # Cheque de consistência entre o portão e a trajetória: os
        # ticks dos vetos por tick são exactamente os ticks
        # tirânicos, em todos os níveis.
        for fator in (1.00, 1.05, 1.10, 1.20, 1.50):
            rel = rodar_party_causal_k_variavel(fator_amplificacao=fator)
            self.assertEqual(
                [v["tick"] for v in rel["eventos"]["vetos_tick"]],
                rel["ticks_tiranicos"],
            )

    def test_dinamica_identica_a_vigilia(self):
        # A variante só troca a medida — a dinâmica é a da
        # vigília, tick a tick, em todos os níveis.
        for fator in (1.00, 1.05, 1.10, 1.50):
            kv = rodar_party_causal_k_variavel(fator_amplificacao=fator)
            vt = rodar_party_causal_vigilia_tick(fator_amplificacao=fator)
            self.assertEqual(
                kv["eventos"]["simbolo_tick"], vt["eventos"]["simbolo_tick"]
            )
            self.assertEqual(
                kv["eventos"]["depositos_por_agente"],
                vt["eventos"]["depositos_por_agente"],
            )
            self.assertEqual(
                kv["eventos"]["seguimentos_por_agente"],
                vt["eventos"]["seguimentos_por_agente"],
            )
            self.assertEqual(
                kv["alavanca"]["total_amplificacoes"],
                vt["alavanca"]["total_amplificacoes"],
            )
            self.assertEqual(kv["pesos_finais"], vt["pesos_finais"])
            self.assertEqual(
                [(t["n_arestas"], t["isc_local"]) for t in kv["trajetoria"]],
                [(t["n_arestas"], t["isc_local"]) for t in vt["trajetoria"]],
            )


class TesteSonda(unittest.TestCase):
    def test_dose_resposta_dourada(self):
        linhas = {l["fator"]: l for l in sondar_k_variavel()}
        dourado = {
            1.00: (32, 0, 0, None, True, True, False, []),
            1.05: (25, 2, 18, 22, False, False, False, [22, 23, 24, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40]),
            1.10: (28, 2, 18, 23, False, False, False, list(range(23, 41))),
            1.20: (21, 3, 21, 20, False, False, False, list(range(20, 41))),
            1.50: (17, 3, 24, 17, False, False, False, list(range(17, 41))),
        }
        for fator, (simbolo, ckpt, tick, primeiro, valido, valido_tick, muda, tiranicos) in dourado.items():
            linha = linhas[fator]
            self.assertEqual(linha["simbolo_tick"], simbolo)
            self.assertEqual(linha["vetos_estado"], ckpt)
            self.assertEqual(linha["vetos_tick"], tick)
            self.assertEqual(linha["primeiro_veto_tick"], primeiro)
            self.assertEqual(linha["simbolo_valido"], valido)
            self.assertEqual(linha["simbolo_valido_tick"], valido_tick)
            self.assertEqual(linha["veredicto_muda"], muda)
            self.assertEqual(linha["ticks_tiranicos"], tiranicos)

    def test_o_tick_apanha_antes_ou_ao_mesmo_tempo_que_o_checkpoint(self):
        # O portão por tick continua a chegar antes do de
        # checkpoint nos níveis amplificados (a 1,20 chega ao
        # mesmo tempo, 20) — a granularidade não perdeu o seu
        # valor, só o controlo é que já não tem nada para apanhar.
        linhas = {l["fator"]: l for l in sondar_k_variavel()}
        for fator in (1.05, 1.10, 1.20, 1.50):
            self.assertLessEqual(
                linhas[fator]["primeiro_veto_tick"],
                linhas[fator]["primeiro_veto_checkpoint"],
            )
        self.assertEqual(linhas[1.20]["primeiro_veto_tick"], 20)
        self.assertEqual(linhas[1.20]["primeiro_veto_checkpoint"], 20)

    def test_o_controlo_e_o_unico_sem_veto(self):
        # Só o controlo escapa a ambos os portões; todos os
        # níveis amplificados têm vetos por tick e por checkpoint.
        linhas = {l["fator"]: l for l in sondar_k_variavel()}
        self.assertEqual(linhas[1.00]["vetos_estado"], 0)
        self.assertEqual(linhas[1.00]["vetos_tick"], 0)
        for fator in (1.05, 1.10, 1.20, 1.50):
            self.assertGreater(linhas[fator]["vetos_estado"], 0)
            self.assertGreater(linhas[fator]["vetos_tick"], 0)
