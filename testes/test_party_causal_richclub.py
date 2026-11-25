"""Testes da variante PROTÓTIPO DE TIRANIA DE RICH-CLUB do cenário
Isekai Zero — A Party Causal.

Roda com: python3 -m unittest discover -s testes -v

Os valores dourados são o resultado registado da corrida com a
semente canónica (SEMENTE = 20261124) e FATOR_DECAIMENTO = 0,95:
se mudarem, alguma coisa na variante mudou — é regressão, não
ruído (o RNG tem semente fixa).

O resultado central desta variante é POSITIVO — o primeiro da
série: com o protótipo rich-club (k = 4) e o limiar reescalado
(0,113), o veto por estado DISPARA sobre um Símbolo vivo. A 1,10
dispara 2 vezes (ticks 30 e 40) e o Símbolo (tick 28) é inválido;
os ticks tirânicos são 23–40 sem interrupção. No mesmo estado,
as duas medidas discordam de frente: no tick 40, JSD ordenado
0,4286 (limpo pela medida antiga) contra JSD rich-club 0,0812
(tirânico pela nova). O controlo (1,00) é transitoriamente
tirânico pela medida nova (ticks 32–36) mas o portão por
checkpoint não o apanha — a trajetória vê-o, o portão não.
"""

import unittest

from cono_gym.causal import jsd_bits, prototipo_tirania
from cono_gym.espectro import LIMIAR_ISC, LIMIAR_VAR
from cono_gym.party_causal import rodar_party_causal
from cono_gym.party_causal_tyranny import jsd_pesos_ordenado
from cono_gym.party_causal_veto_estado import (
    JSD_ESTADO,
    MIN_ARESTAS_JSD,
    rodar_party_causal_veto_estado,
)
from cono_gym.party_causal_sora import (
    FATOR_AMPLIFICACAO,
    JOELHO_AMPLIFICACAO,
    rodar_party_causal_sora,
    sondar_sora,
)
from cono_gym.party_causal_richclub import (
    JSD_RC_ESTADO,
    JSD_RC_UNIFORME,
    RICHCLUB_K,
    jsd_pesos_richclub,
    prototipo_richclub,
    rodar_party_causal_richclub,
    sondar_richclub,
)
import cono_gym.party_causal as pc


class TestePrototipo(unittest.TestCase):
    def test_forma_e_soma(self):
        proto = prototipo_richclub(10, 4)
        self.assertEqual(len(proto), 10)
        self.assertAlmostEqual(sum(proto), 1.0, places=9)
        self.assertEqual(proto[:4], [0.225] * 4)
        self.assertAlmostEqual(proto[4], 0.1 / 6, places=9)
        self.assertTrue(all(proto[i] == proto[0] for i in range(4)))
        self.assertTrue(all(proto[i] == proto[4] for i in range(4, 10)))

    def test_k_1_reproduz_o_prototipo_de_um_so_rastro(self):
        # A medida nova contém a antiga como caso particular: com
        # k = 1 o protótipo rich-club É o protótipo de Tirania.
        for n in (2, 5, 10):
            self.assertEqual(prototipo_richclub(n, 1), prototipo_tirania(n))

    def test_erros(self):
        for n, k in [(1, 1), (5, 5), (5, 6), (10, 0), (10, 10)]:
            with self.assertRaises(ValueError):
                prototipo_richclub(n, k)

    def test_uniforme_vs_richclub_abaixo_de_0_28(self):
        # O facto que obriga à reescala: até um cluster
        # perfeitamente uniforme está abaixo do limiar antigo
        # (0,2141 < 0,28) — o 0,28 sem reescala dispararia sempre.
        self.assertAlmostEqual(JSD_RC_UNIFORME, 0.2141, places=3)
        self.assertLess(JSD_RC_UNIFORME, JSD_ESTADO)

    def test_limiar_reescalado(self):
        # 0,28 x JSD(uniforme, richclub) / JSD(uniforme, tirania):
        # a mesma posição relativa do limiar antigo na escala nova.
        self.assertAlmostEqual(JSD_RC_ESTADO, 0.113, places=3)
        esperado = round(
            0.28
            * jsd_bits([0.1] * 10, prototipo_richclub(10, 4))
            / jsd_bits([0.1] * 10, prototipo_tirania(10)),
            3,
        )
        self.assertEqual(JSD_RC_ESTADO, esperado)
        # Verificação independente: o ponto médio uniforme <->
        # protótipo (0,107) vive no mesmo bairro.
        self.assertAlmostEqual(JSD_RC_UNIFORME / 2, 0.107, places=3)

    def test_hub_perfeito_e_zero(self):
        self.assertAlmostEqual(
            jsd_bits(prototipo_richclub(10, 4), prototipo_richclub(10, 4)),
            0.0,
            places=9,
        )

    def test_a_medida_nova_ve_o_hub_e_a_antiga_nao(self):
        # O hub da Sora a 1,50 (4 arestas a 0,95, as outras
        # 0,26–0,43): perto do protótipo rich-club, longe do de um
        # só rastro. E o inverso para um só rastro dominante.
        hub = [0.95, 0.95, 0.95, 0.95, 0.43, 0.38, 0.33, 0.30, 0.28, 0.26]
        # Um só rastro dominante a sério: a distribuição do próprio
        # protótipo (0,9 num bin, o resto a 0,011). Um rastro a
        # 0,95 contra nove a 0,30 é só 3x os outros — não é um
        # rastro dominante, e a comparação com ele sai ao contrário.
        um_trail = [0.9] + [0.1 / 9] * 9
        jsd_hub_rc = jsd_bits(sorted(hub, reverse=True), prototipo_richclub(10, 4))
        jsd_hub_1 = jsd_bits(sorted(hub, reverse=True), prototipo_tirania(10))
        jsd_trail_rc = jsd_bits(sorted(um_trail, reverse=True), prototipo_richclub(10, 4))
        jsd_trail_1 = jsd_bits(sorted(um_trail, reverse=True), prototipo_tirania(10))
        self.assertLess(jsd_hub_rc, 0.113)
        self.assertGreater(jsd_hub_1, 0.28)
        self.assertLess(jsd_trail_1, jsd_trail_rc)
        self.assertLess(jsd_hub_rc, jsd_trail_rc)

    def test_jsd_richclub_none_sem_arestas(self):
        est = pc._Estado(pc.SEMENTE)
        # O subgrafo da party começa sem arestas.
        self.assertIsNone(jsd_pesos_richclub(est.subgrafo_party()))


class TesteControlo(unittest.TestCase):
    def test_fator_1_reproduz_o_veto_estado(self):
        # A maquinaria da variante sem amplificação é a dinâmica do
        # veto-estado: ISC, VarPn e Gini por checkpoint são
        # idênticos — e nenhum veto dispara EM CHECKPOINT. Isto
        # prova que a guarda da amplificação não toca na dinâmica.
        var = rodar_party_causal_richclub(fator_amplificacao=1.00)
        ref = rodar_party_causal_veto_estado()
        for b, v in zip(ref["checkpoints"], var["checkpoints"]):
            self.assertEqual(b["isc_local"], v["isc_local"])
            self.assertEqual(b["var_ponderada_normalizada"], v["var_ponderada_normalizada"])
            self.assertEqual(b["gini"], v["gini"])
            self.assertEqual(b["jsd_ordenado"], v["jsd_ordenado"])
        self.assertEqual(var["eventos"]["simbolo_tick"], 32)
        self.assertEqual(var["eventos"]["ren_verdadeiro"], 26)
        self.assertEqual(var["eventos"]["ren_falso"], 2)
        self.assertEqual(var["eventos"]["vetos"], [])
        self.assertEqual(var["eventos"]["vetos_estado"], [])
        self.assertEqual(var["alavanca"]["total_amplificacoes"], 0)
        self.assertTrue(var["criterios"]["simbolo_valido"])
        self.assertFalse(var["criterios"]["sora_amplificou"])

    def test_controlo_transitoriamente_tiranico_que_o_portao_nao_apanha(self):
        # A honestidade do controlo: pela medida nova, o cluster é
        # tirânico nos ticks 32–36 (ISC 0,90, JSDrc ~0,10) — mas o
        # portão por checkpoint não dispara: no checkpoint 30 o
        # ISC ainda é 0,80 e no 40 o JSDrc já recuperou para
        # 0,1232. A trajetória vê-o; o portão não.
        var = rodar_party_causal_richclub(fator_amplificacao=1.00)
        self.assertEqual(var["ticks_tiranicos"], [32, 33, 34, 35, 36])
        self.assertEqual(var["eventos"]["vetos_estado"], [])
        self.assertAlmostEqual(var["jsd_richclub_final"], 0.1232, places=3)
        self.assertGreater(var["jsd_richclub_final"], JSD_RC_ESTADO)
        # E o 0,28 sem reescala dispararia em todo o lado — até no
        # controlo (ticks 32–40): a prova de que a reescala não
        # era opcional.
        self.assertEqual(
            var["ticks_tiranicos_028"], [32, 33, 34, 35, 36, 37, 38, 39, 40]
        )
        self.assertTrue(var["criterios"]["limiar_0.28_sem_reescala_dispararia"])

    def test_base_intacta_depois_da_variante(self):
        rodar_party_causal_richclub()
        base = rodar_party_causal()
        self.assertEqual(base["eventos"]["simbolo_tick"], 32)


class TesteCorrida(unittest.TestCase):
    def test_deterministica(self):
        a = rodar_party_causal_richclub()
        b = rodar_party_causal_richclub()
        self.assertEqual(a, b)

    def test_outra_semente_muda_o_resultado(self):
        a = rodar_party_causal_richclub()
        b = rodar_party_causal_richclub(semente=1)
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
        rel = rodar_party_causal_richclub()
        for c in rel["checkpoints"]:
            self.assertEqual(
                c["simbolo"],
                c["isc_local"] >= 0.85 and c["var_ponderada_normalizada"] <= 0.36,
            )

    def test_resultado_dourado_semente_canonica(self):
        rel = rodar_party_causal_richclub()
        ev = rel["eventos"]
        self.assertEqual(ev["simbolo_tick"], 28)
        self.assertEqual(ev["ren_verdadeiro"], 28)
        self.assertEqual(ev["ren_falso"], 0)
        self.assertEqual(ev["veyra_verdadeiro"], 3)
        self.assertEqual(ev["tentativas_simbolo"], 10)
        self.assertEqual(len(ev["tentativas_meta_simbolo"]), 3)
        self.assertEqual(
            ev["depositos_por_agente"],
            {"Ren": 2, "Lira": 32, "Kael": 16, "Sora": 29, "Veyra": 13},
        )
        self.assertEqual(
            ev["seguimentos_por_agente"],
            {"Ren": 30, "Lira": 3, "Kael": 2, "Sora": 1, "Veyra": 21},
        )
        self.assertEqual(rel["alavanca"]["total_amplificacoes"], 96)
        self.assertEqual(rel["alavanca"]["acoes_amplificadoras"], 33)
        self.assertEqual(rel["alavanca"]["total_decaimentos"], 209)
        final = rel["checkpoints"][-1]
        self.assertEqual(final["n_arestas"], 10)
        self.assertAlmostEqual(final["isc_local"], 1.0, places=3)
        self.assertAlmostEqual(final["var_ponderada_normalizada"], 0.1039, places=3)
        self.assertAlmostEqual(final["gini"], 0.3007, places=3)
        self.assertAlmostEqual(final["jsd_pesos"], 0.44, places=3)
        self.assertAlmostEqual(final["jsd_ordenado"], 0.4286, places=3)
        self.assertAlmostEqual(final["jsd_richclub"], 0.0812, places=3)
        self.assertEqual(final["vetos"], 0)
        self.assertEqual(final["vetos_estado"], 2)
        self.assertEqual(final["arestas_no_piso"], 0)
        self.assertTrue(final["simbolo"])
        self.assertAlmostEqual(rel["jsd_richclub_min"], 0.0295, places=3)
        self.assertEqual(rel["jsd_richclub_min_tick"], 4)
        self.assertAlmostEqual(rel["jsd_ordenado_min"], 0.2611, places=3)
        self.assertEqual(rel["jsd_ordenado_min_tick"], 4)
        self.assertEqual(rel["cruzamentos"], {"rc_0.28_sem_reescala": 4, "rc_estado": 4})
        self.assertEqual([v["tick"] for v in ev["vetos_estado"]], [30, 40])
        self.assertEqual(
            [v["jsd_richclub"] for v in ev["vetos_estado"]], [0.063, 0.0812]
        )
        # No mesmo estado, a medida antiga diz "limpo" e a nova
        # diz "tirânico" — a comparação que a variante existe para
        # fazer.
        self.assertEqual(
            [v["jsd_ordenado"] for v in ev["vetos_estado"]], [0.4089, 0.4286]
        )
        self.assertEqual(
            rel["ticks_tiranicos"], list(range(23, 41))
        )
        self.assertFalse(rel["criterios"]["simbolo_valido"])
        self.assertTrue(rel["criterios"]["veto_estado_disparou"])
        self.assertTrue(rel["criterios"]["cluster_tiranico"])
        self.assertTrue(rel["criterios"]["sora_amplificou"])

    def test_o_veto_por_estado_dispara_com_o_fator_omisso(self):
        # O primeiro disparo da série: a 1,10 o portão rich-club
        # dispara 2 vezes e o Símbolo é inválido.
        rel = rodar_party_causal_richclub()
        self.assertEqual(len(rel["eventos"]["vetos_estado"]), 2)
        self.assertTrue(rel["criterios"]["veto_estado_disparou"])
        self.assertTrue(rel["criterios"]["cluster_tiranico"])
        self.assertFalse(rel["criterios"]["simbolo_valido"])
        self.assertEqual(rel["ticks_tiranicos"], list(range(23, 41)))

    def test_criterios_da_base_continuam_a_passar(self):
        rel = rodar_party_causal_richclub()
        crit = rel["criterios"]
        self.assertTrue(crit["simbolo_formado"])
        self.assertTrue(crit["sucesso_parcial"])
        self.assertTrue(crit["sucesso_completo"])
        self.assertGreaterEqual(rel["jsd_min"], 0.22)
        self.assertGreaterEqual(rel["jsd_final"], 0.28)

    def test_jsd_canonico_e_h_causal_indefinidos(self):
        rel = rodar_party_causal_richclub()
        for c in rel["checkpoints"]:
            self.assertIsNone(c["jsd_canonico"])
            self.assertIsNone(c["h_causal"])

    def test_avaliacao_final_sem_checkpoint(self):
        # n_ticks = 25 não é múltiplo de 10: a avaliação final corre
        # fora dos checkpoints, sem dupla contagem e sem rebentar.
        # E dispara: a 1,10 o tick 25 já é tirânico (ISC 0,90,
        # JSDrc 0,0819) — o Símbolo ainda não foi reclamado
        # (só no tick 28), por isso o veto é sobre um cluster
        # tirânico sem Símbolo.
        rel = rodar_party_causal_richclub(n_ticks=25)
        self.assertEqual(len(rel["checkpoints"]), 2)
        self.assertEqual(len(rel["eventos"]["vetos_estado"]), 1)
        self.assertEqual(rel["eventos"]["vetos_estado"][0]["tick"], 25)
        self.assertFalse(rel["eventos"]["vetos_estado"][0]["simbolo_reclamado"])
        self.assertEqual(rel["ticks_tiranicos"], [23, 24, 25])


class TesteComparacao(unittest.TestCase):
    def test_a_1_50_as_duas_medidas_discordam_no_mesmo_estado(self):
        # O hub a 1,50: as quatro arestas da Sora em 0,95, as outras
        # seis em 0,26–0,43. No estado final, a medida antiga lê
        # 0,4548 (limpo) e a nova 0,0748 (tirânico) — a mesma
        # distribuição, dois veredictos.
        rel = rodar_party_causal_richclub(fator_amplificacao=1.50)
        self.assertAlmostEqual(rel["jsd_ordenado_final"], 0.4548, places=3)
        self.assertAlmostEqual(rel["jsd_richclub_final"], 0.0748, places=3)
        self.assertGreater(rel["jsd_ordenado_final"], JSD_ESTADO)
        self.assertLess(rel["jsd_richclub_final"], JSD_RC_ESTADO)
        self.assertEqual(
            [p["peso"] for p in rel["pesos_finais"] if p["incidente_sora"]],
            [0.95, 0.95, 0.95, 0.95],
        )
        self.assertEqual(rel["ticks_tiranicos"], list(range(17, 41)))
        self.assertEqual(len(rel["eventos"]["vetos_estado"]), 3)
        self.assertFalse(rel["criterios"]["simbolo_valido"])

    def test_jsd_rc_abaixo_do_jsd_ord_quando_isc_passa_0_85(self):
        # Em todos os níveis, a partir do momento em que o ISC
        # passa 0,85, a medida nova está sempre abaixo da antiga:
        # o hub é mais visível para ela em todo o regime denso.
        for fator in (1.00, 1.05, 1.10, 1.20, 1.50):
            rel = rodar_party_causal_richclub(fator_amplificacao=fator)
            for t in rel["trajetoria"]:
                if t["isc_local"] >= 0.85:
                    self.assertLess(t["jsd_richclub"], t["jsd_ordenado"])

    def test_o_gini_nao_ve_o_hub(self):
        # O Gini fica registado como monitor secundário — e a 1,50
        # não chega a 0,30 no fim: a saturação uniformiza-o, como
        # na Sora. É a JSD rich-club que vê o hub, não o Gini.
        rel = rodar_party_causal_richclub(fator_amplificacao=1.50)
        final = rel["checkpoints"][-1]
        self.assertAlmostEqual(final["gini"], 0.2568, places=3)
        self.assertLess(final["gini"], 0.30)
        self.assertFalse(rel["criterios"]["gini_final_ge_0.30"])

    def test_dinamica_identica_a_sora(self):
        # A variante só troca a medida — a dinâmica (agentes, RNG,
        # amplificação, decaimento) é a da Sora, tick a tick.
        for fator in (1.00, 1.10, 1.50):
            rc = rodar_party_causal_richclub(fator_amplificacao=fator)
            sora = rodar_party_causal_sora(fator_amplificacao=fator)
            self.assertEqual(rc["eventos"]["simbolo_tick"], sora["eventos"]["simbolo_tick"])
            self.assertEqual(rc["eventos"]["depositos_por_agente"], sora["eventos"]["depositos_por_agente"])
            self.assertEqual(rc["eventos"]["seguimentos_por_agente"], sora["eventos"]["seguimentos_por_agente"])
            self.assertEqual(rc["alavanca"]["total_amplificacoes"], sora["alavanca"]["total_amplificacoes"])


class TesteSonda(unittest.TestCase):
    def test_dose_resposta_dourada(self):
        linhas = {l["fator"]: l for l in sondar_richclub()}
        dourado = {
            # fator: (Símbolo, vetos_estado, ticks_tiranicos, Gini final,
            #         JSDrc mín, JSDrc final, JSDord final, VarPn, amplificações)
            1.00: (32, 0, list(range(32, 37)), 0.2471, 0.0257, 0.1232, 0.3323, 0.0964, 0),
            1.05: (25, 3, list(range(20, 41)), 0.291, 0.0267, 0.074, 0.3271, 0.1154, 107),
            1.10: (28, 2, list(range(23, 41)), 0.3007, 0.0295, 0.0812, 0.4286, 0.1039, 96),
            1.20: (21, 3, list(range(20, 41)), 0.2765, 0.0301, 0.0678, 0.4509, 0.105, 85),
            1.50: (17, 3, list(range(17, 41)), 0.2568, 0.0317, 0.0748, 0.4548, 0.0996, 90),
        }
        for fator, (tick, vetos, tiranicos, gini, rc_min, rc_fin, ord_fin, varpn, ampl) in dourado.items():
            linha = linhas[fator]
            self.assertEqual(linha["simbolo_tick"], tick)
            self.assertEqual(linha["vetos_tentativa"], 0)
            self.assertEqual(linha["vetos_estado"], vetos)
            self.assertEqual(linha["ticks_tiranicos"], tiranicos)
            self.assertAlmostEqual(linha["gini_final"], gini, places=3)
            self.assertAlmostEqual(linha["jsd_richclub_min"], rc_min, places=3)
            self.assertEqual(linha["jsd_richclub_min_tick"], 4)
            self.assertAlmostEqual(linha["jsd_richclub_final"], rc_fin, places=3)
            self.assertAlmostEqual(linha["jsd_ordenado_final"], ord_fin, places=3)
            self.assertAlmostEqual(linha["varpn_final"], varpn, places=3)
            self.assertEqual(linha["total_amplificacoes"], ampl)

    def test_o_veto_dispara_em_todos_os_niveis_amplificados(self):
        for fator in (1.05, 1.10, 1.20, 1.50):
            rel = rodar_party_causal_richclub(fator_amplificacao=fator)
            self.assertGreater(len(rel["eventos"]["vetos_estado"]), 0)
            self.assertTrue(rel["criterios"]["veto_estado_disparou"])
            self.assertFalse(rel["criterios"]["simbolo_valido"])

    def test_a_janela_tiranica_fica_aberta_nos_niveis_amplificados(self):
        # Nos níveis amplificados a janela abre no Símbolo ou antes
        # e fica aberta até ao tick 40 — concentração e integração
        # coexistem. No controlo é só um transiente de 5 ticks
        # (32–36) que depois fecha. O primeiro tick não é monótono
        # no fator (20 -> 23 -> 20), por isso o teste fixa a
        # estrutura, não a ordem.
        linhas = {l["fator"]: l for l in sondar_richclub()}
        self.assertEqual(linhas[1.00]["ticks_tiranicos"], [32, 33, 34, 35, 36])
        for fator in (1.05, 1.10, 1.20, 1.50):
            linha = linhas[fator]
            self.assertLessEqual(linha["ticks_tiranicos"][0], linha["simbolo_tick"])
            self.assertEqual(linha["ticks_tiranicos"][-1], 40)


if __name__ == "__main__":
    unittest.main()
