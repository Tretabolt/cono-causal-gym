"""Testes da variante VIGILÂNCIA POR TICK do cenário Isekai Zero
— A Party Causal.

Roda com: python3 -m unittest discover -s testes -v

Os valores dourados são o resultado registado da corrida com a
semente canónica (SEMENTE = 20261124) e FATOR_DECAIMENTO = 0,95:
se mudarem, alguma coisa na variante mudou — é regressão, não
ruído (o RNG tem semente fixa).

O resultado central desta variante é a resposta à pergunta que
a rich-club deixou aberta: o CONTROLO (1,00) é transitoriamente
tirânico pela trajetória (ticks 32–36) e o Símbolo é reclamado
no tick 32 — no meio do transiente — mas o portão por
checkpoint não o apanha. Com a vigilância por tick, o controlo
MUDA DE VEREDICTO: 5 vetos por tick (32–36), Símbolo inválido.
É a única mudança de veredicto da sonda — nos níveis
amplificados os veredictos não mudam (já eram inválidos), mas
a invalidação chega muito mais cedo: o Símbolo nasce tirânico
em todos os níveis, e sob a vigilância por tick nenhum Símbolo
é válido.
"""

import unittest

from cono_gym.espectro import LIMIAR_ISC, LIMIAR_VAR
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
    rodar_party_causal_richclub,
)
from cono_gym.party_causal_vigilia_tick import (
    rodar_party_causal_vigilia_tick,
    sondar_vigilia_tick,
)


class TesteControlo(unittest.TestCase):
    def test_fator_1_reproduz_a_richclub_nos_checkpoints(self):
        # A maquinaria da variante sem amplificação é a dinâmica da
        # rich-club: ISC, VarPn, Gini e os dois JSDs por checkpoint
        # são idênticos — e os vetos por checkpoint também. A única
        # diferença é o portão por tick, que corre em paralelo.
        var = rodar_party_causal_vigilia_tick(fator_amplificacao=1.00)
        ref = rodar_party_causal_richclub(fator_amplificacao=1.00)
        for b, v in zip(ref["checkpoints"], var["checkpoints"]):
            self.assertEqual(b["isc_local"], v["isc_local"])
            self.assertEqual(b["var_ponderada_normalizada"], v["var_ponderada_normalizada"])
            self.assertEqual(b["gini"], v["gini"])
            self.assertEqual(b["jsd_ordenado"], v["jsd_ordenado"])
            self.assertEqual(b["jsd_richclub"], v["jsd_richclub"])
            self.assertEqual(b["vetos_estado"], v["vetos_estado"])
        self.assertEqual(var["eventos"]["simbolo_tick"], 32)
        self.assertEqual(var["eventos"]["ren_verdadeiro"], 26)
        self.assertEqual(var["eventos"]["ren_falso"], 2)
        self.assertEqual(var["eventos"]["vetos"], [])
        self.assertEqual(var["eventos"]["vetos_estado"], [])
        self.assertEqual(var["alavanca"]["total_amplificacoes"], 0)
        self.assertTrue(var["criterios"]["simbolo_valido"])
        self.assertFalse(var["criterios"]["sora_amplificou"])

    def test_o_controlo_muda_de_veredicto(self):
        # A pergunta que a variante existe para responder: o
        # controlo, válido pelo checkpoint, é invalidado pela
        # vigilância por tick. 5 vetos por tick (32–36), o primeiro
        # no próprio tick em que o Símbolo é reclamado.
        var = rodar_party_causal_vigilia_tick(fator_amplificacao=1.00)
        self.assertEqual(var["ticks_tiranicos"], [32, 33, 34, 35, 36])
        self.assertEqual(
            [v["tick"] for v in var["eventos"]["vetos_tick"]],
            [32, 33, 34, 35, 36],
        )
        self.assertEqual(var["eventos"]["vetos_estado"], [])
        self.assertTrue(var["criterios"]["simbolo_valido"])
        self.assertTrue(var["criterios"]["simbolo_valido_checkpoint"])
        self.assertFalse(var["criterios"]["simbolo_valido_tick"])
        self.assertTrue(var["criterios"]["veredicto_muda"])
        self.assertTrue(var["comparacao"]["veredicto_muda"])
        self.assertEqual(var["comparacao"]["primeiro_veto_checkpoint"], None)
        self.assertEqual(var["comparacao"]["primeiro_veto_tick"], 32)
        self.assertEqual(var["comparacao"]["primeiro_veto_tick_reclamado"], 32)
        self.assertTrue(var["comparacao"]["simbolo_nasce_tiranico"])
        self.assertAlmostEqual(var["jsd_richclub_final"], 0.1232, places=3)
        self.assertGreater(var["jsd_richclub_final"], JSD_RC_ESTADO)

    def test_base_intacta_depois_da_variante(self):
        rodar_party_causal_vigilia_tick()
        base = rodar_party_causal()
        self.assertEqual(base["eventos"]["simbolo_tick"], 32)


class TesteCorrida(unittest.TestCase):
    def test_deterministica(self):
        a = rodar_party_causal_vigilia_tick()
        b = rodar_party_causal_vigilia_tick()
        self.assertEqual(a, b)

    def test_outra_semente_muda_o_resultado(self):
        a = rodar_party_causal_vigilia_tick()
        b = rodar_party_causal_vigilia_tick(semente=1)
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
        rel = rodar_party_causal_vigilia_tick()
        for c in rel["checkpoints"]:
            self.assertEqual(
                c["simbolo"],
                c["isc_local"] >= 0.85 and c["var_ponderada_normalizada"] <= 0.36,
            )

    def test_resultado_dourado_semente_canonica(self):
        rel = rodar_party_causal_vigilia_tick()
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
        self.assertEqual(final["vetos_tick"], 18)
        self.assertEqual(final["arestas_no_piso"], 0)
        self.assertTrue(final["simbolo"])
        self.assertAlmostEqual(rel["jsd_richclub_min"], 0.0295, places=3)
        self.assertEqual(rel["jsd_richclub_min_tick"], 4)
        self.assertAlmostEqual(rel["jsd_ordenado_min"], 0.2611, places=3)
        self.assertEqual(rel["jsd_ordenado_min_tick"], 4)
        self.assertEqual(rel["cruzamentos"], {"rc_0.28_sem_reescala": 4, "rc_estado": 4})
        # Os dois portões, lado a lado: o checkpoint dispara 2
        # vezes (30 e 40); o tick, 18 vezes (23–40).
        self.assertEqual([v["tick"] for v in ev["vetos_estado"]], [30, 40])
        self.assertEqual(
            [v["jsd_richclub"] for v in ev["vetos_estado"]], [0.063, 0.0812]
        )
        self.assertEqual(
            [v["jsd_ordenado"] for v in ev["vetos_estado"]], [0.4089, 0.4286]
        )
        self.assertEqual(
            [v["tick"] for v in ev["vetos_tick"]], list(range(23, 41))
        )
        self.assertEqual(rel["ticks_tiranicos"], list(range(23, 41)))
        self.assertEqual(
            rel["comparacao"],
            {
                "vetos_checkpoint": 2,
                "vetos_tick": 18,
                "primeiro_veto_checkpoint": 30,
                "primeiro_veto_tick": 23,
                "primeiro_veto_tick_reclamado": 28,
                "primeiro_veto_checkpoint_reclamado": 30,
                "simbolo_nasce_tiranico": True,
                "veredicto_muda": False,
                "simbolo_valido_checkpoint": False,
                "simbolo_valido_tick": False,
            },
        )
        self.assertFalse(rel["criterios"]["simbolo_valido"])
        self.assertFalse(rel["criterios"]["simbolo_valido_checkpoint"])
        self.assertFalse(rel["criterios"]["simbolo_valido_tick"])
        self.assertFalse(rel["criterios"]["veredicto_muda"])
        self.assertTrue(rel["criterios"]["veto_estado_disparou"])
        self.assertTrue(rel["criterios"]["veto_tick_disparou"])
        self.assertTrue(rel["criterios"]["cluster_tiranico"])
        self.assertTrue(rel["criterios"]["sora_amplificou"])

    def test_criterios_da_base_continuam_a_passar(self):
        rel = rodar_party_causal_vigilia_tick()
        crit = rel["criterios"]
        self.assertTrue(crit["simbolo_formado"])
        self.assertTrue(crit["sucesso_parcial"])
        self.assertTrue(crit["sucesso_completo"])
        self.assertGreaterEqual(rel["jsd_min"], 0.22)
        self.assertGreaterEqual(rel["jsd_final"], 0.28)

    def test_jsd_canonico_e_h_causal_indefinidos(self):
        rel = rodar_party_causal_vigilia_tick()
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
        rel = rodar_party_causal_vigilia_tick(n_ticks=25)
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
    def test_a_1_50_o_tick_apanha_o_simbolo_no_proprio_tick(self):
        # A 1,50 a janela abre no tick 17, o próprio tick do
        # Símbolo: o portão por tick apanha-o logo ali; o por
        # checkpoint só no 20. 24 vetos por tick contra 3 por
        # checkpoint.
        rel = rodar_party_causal_vigilia_tick(fator_amplificacao=1.50)
        self.assertEqual(rel["eventos"]["simbolo_tick"], 17)
        self.assertEqual(rel["comparacao"]["primeiro_veto_tick"], 17)
        self.assertEqual(rel["comparacao"]["primeiro_veto_tick_reclamado"], 17)
        self.assertEqual(rel["comparacao"]["primeiro_veto_checkpoint"], 20)
        self.assertEqual(rel["comparacao"]["vetos_tick"], 24)
        self.assertEqual(rel["comparacao"]["vetos_checkpoint"], 3)
        self.assertTrue(rel["comparacao"]["simbolo_nasce_tiranico"])
        self.assertFalse(rel["criterios"]["simbolo_valido"])
        self.assertFalse(rel["criterios"]["simbolo_valido_tick"])

    def test_o_simbolo_nasce_tiranico_em_todos_os_niveis(self):
        # Em todos os níveis o primeiro veto por tick reclamado é
        # o próprio tick do Símbolo: o Símbolo é reclamado num
        # estado já tirânico, em toda a sonda.
        for fator in (1.00, 1.05, 1.10, 1.20, 1.50):
            rel = rodar_party_causal_vigilia_tick(fator_amplificacao=fator)
            self.assertEqual(
                rel["comparacao"]["primeiro_veto_tick_reclamado"],
                rel["eventos"]["simbolo_tick"],
            )
            self.assertTrue(rel["comparacao"]["simbolo_nasce_tiranico"])

    def test_sob_a_vigilia_por_tick_nenhum_simbolo_e_valido(self):
        # Sob a vigilância por tick, nenhum Símbolo da sonda é
        # válido — nem o do controlo, que o checkpoint deixava
        # passar.
        for fator in (1.00, 1.05, 1.10, 1.20, 1.50):
            rel = rodar_party_causal_vigilia_tick(fator_amplificacao=fator)
            self.assertFalse(rel["criterios"]["simbolo_valido_tick"])

    def test_o_veredicto_so_muda_no_controlo(self):
        # A única mudança de veredicto da sonda é a do controlo:
        # nos níveis amplificados o Símbolo já era inválido por
        # checkpoint, e continua inválido por tick.
        linhas = {l["fator"]: l for l in sondar_vigilia_tick()}
        self.assertTrue(linhas[1.00]["veredicto_muda"])
        for fator in (1.05, 1.10, 1.20, 1.50):
            self.assertFalse(linhas[fator]["veredicto_muda"])
            self.assertFalse(linhas[fator]["simbolo_valido"])
            self.assertFalse(linhas[fator]["simbolo_valido_tick"])

    def test_vetos_tick_sao_os_ticks_tiranicos(self):
        # Cheque de consistência entre o portão e a trajetória: os
        # ticks dos vetos por tick são exactamente os ticks
        # tirânicos, em todos os níveis. Se isto falhasse, o portão
        # e a trajetória estariam a medir coisas diferentes.
        for fator in (1.00, 1.05, 1.10, 1.20, 1.50):
            rel = rodar_party_causal_vigilia_tick(fator_amplificacao=fator)
            self.assertEqual(
                [v["tick"] for v in rel["eventos"]["vetos_tick"]],
                rel["ticks_tiranicos"],
            )

    def test_o_bairro_concorrido_medido(self):
        # A honestidade do limiar: os vetos do controlo disparam
        # com JSDrc 0,0997–0,1045 — a 0,0085–0,0133 do limiar
        # 0,113 — e os ticks 37–40 ficam logo acima dele
        # (0,1159–0,1244). O portão por tick não inventa sinal:
        # apanha um transiente que a medida já assinala — mas
        # expõe que o limiar atravessa os valores da fase densa
        # do controlo, e um portão por tick dispara em pequenas
        # depressões abaixo dele.
        rel = rodar_party_causal_vigilia_tick(fator_amplificacao=1.00)
        traj = {t["tick"]: t for t in rel["trajetoria"]}
        jsd_vetos = [traj[v["tick"]]["jsd_richclub"] for v in rel["eventos"]["vetos_tick"]]
        self.assertEqual(len(jsd_vetos), 5)
        self.assertAlmostEqual(min(jsd_vetos), 0.0997, places=3)
        self.assertAlmostEqual(max(jsd_vetos), 0.1045, places=3)
        for jsd in jsd_vetos:
            self.assertLess(jsd, JSD_RC_ESTADO)
            self.assertGreater(JSD_RC_ESTADO - jsd, 0.0)
            self.assertLess(JSD_RC_ESTADO - jsd, 0.014)
        for tick in (37, 38, 39, 40):
            self.assertGreater(traj[tick]["jsd_richclub"], JSD_RC_ESTADO)
            self.assertLess(traj[tick]["jsd_richclub"] - JSD_RC_ESTADO, 0.012)
        # E o JSDrc final do controlo (0,1232) está acima do
        # limiar — é por isso que o checkpoint 40 não dispara.
        self.assertAlmostEqual(rel["jsd_richclub_final"], 0.1232, places=3)

    def test_dinamica_identica_a_richclub(self):
        # A variante só troca a granularidade da vigilância — a
        # dinâmica (agentes, RNG, amplificação, decaimento) é a da
        # rich-club, tick a tick.
        for fator in (1.00, 1.10, 1.50):
            vt = rodar_party_causal_vigilia_tick(fator_amplificacao=fator)
            rc = rodar_party_causal_richclub(fator_amplificacao=fator)
            self.assertEqual(vt["eventos"]["simbolo_tick"], rc["eventos"]["simbolo_tick"])
            self.assertEqual(vt["eventos"]["depositos_por_agente"], rc["eventos"]["depositos_por_agente"])
            self.assertEqual(vt["eventos"]["seguimentos_por_agente"], rc["eventos"]["seguimentos_por_agente"])
            self.assertEqual(vt["alavanca"]["total_amplificacoes"], rc["alavanca"]["total_amplificacoes"])
            self.assertEqual(vt["eventos"]["vetos_estado"], rc["eventos"]["vetos_estado"])
            self.assertEqual(vt["ticks_tiranicos"], rc["ticks_tiranicos"])


class TesteSonda(unittest.TestCase):
    def test_dose_resposta_dourada(self):
        linhas = {l["fator"]: l for l in sondar_vigilia_tick()}
        dourado = {
            # fator: (Símbolo, vetos_estado, vetos_tick, 1º tick,
            #         1º ckpt, 1º ckpt reclamado, válido ckpt,
            #         válido tick, muda, último tick tirânico, Gini,
            #         JSDrc mín, JSDrc final, JSDord final, VarPn, ampl)
            1.00: (32, 0, 5, 32, None, None, True, False, True, 36, 0.2471, 0.0257, 0.1232, 0.3323, 0.0964, 0),
            1.05: (25, 3, 21, 20, 20, 30, False, False, False, 40, 0.291, 0.0267, 0.074, 0.3271, 0.1154, 107),
            1.10: (28, 2, 18, 23, 30, 30, False, False, False, 40, 0.3007, 0.0295, 0.0812, 0.4286, 0.1039, 96),
            1.20: (21, 3, 21, 20, 20, 30, False, False, False, 40, 0.2765, 0.0301, 0.0678, 0.4509, 0.105, 85),
            1.50: (17, 3, 24, 17, 20, 20, False, False, False, 40, 0.2568, 0.0317, 0.0748, 0.4548, 0.0996, 90),
        }
        for fator, (tick, vest, vtick, p_tick, p_ckpt, p_ckpt_recl, val, val_tick, muda, ult_tir, gini, rc_min, rc_fin, ord_fin, varpn, ampl) in dourado.items():
            linha = linhas[fator]
            self.assertEqual(linha["simbolo_tick"], tick)
            self.assertEqual(linha["vetos_tentativa"], 0)
            self.assertEqual(linha["vetos_estado"], vest)
            self.assertEqual(linha["vetos_tick"], vtick)
            self.assertEqual(linha["primeiro_veto_tick"], p_tick)
            self.assertEqual(linha["primeiro_veto_checkpoint"], p_ckpt)
            self.assertEqual(linha["primeiro_veto_tick_reclamado"], tick)
            self.assertEqual(linha["primeiro_veto_checkpoint_reclamado"], p_ckpt_recl)
            self.assertTrue(linha["simbolo_nasce_tiranico"])
            self.assertEqual(linha["simbolo_valido"], val)
            self.assertEqual(linha["simbolo_valido_tick"], val_tick)
            self.assertEqual(linha["veredicto_muda"], muda)
            self.assertEqual(linha["ticks_tiranicos"][0], p_tick)
            # A janela tirânica fecha-se no controlo (32–36) e fica
            # aberta até ao fim nos níveis amplificados.
            self.assertEqual(linha["ticks_tiranicos"][-1], ult_tir)
            self.assertAlmostEqual(linha["gini_final"], gini, places=3)
            self.assertAlmostEqual(linha["jsd_richclub_min"], rc_min, places=3)
            self.assertEqual(linha["jsd_richclub_min_tick"], 4)
            self.assertAlmostEqual(linha["jsd_richclub_final"], rc_fin, places=3)
            self.assertAlmostEqual(linha["jsd_ordenado_final"], ord_fin, places=3)
            self.assertAlmostEqual(linha["varpn_final"], varpn, places=3)
            self.assertEqual(linha["total_amplificacoes"], ampl)

    def test_a_invalidação_chega_mais_cedo_em_todos_os_niveis(self):
        # O primeiro veto por tick reclamado é o próprio tick do
        # Símbolo em todos os níveis; o primeiro por checkpoint
        # RECLAMADO chega 2–9 ticks depois (ou nunca, no
        # controlo). A vigilância por tick não muda só o veredicto
        # do controlo — muda QUANDO cada Símbolo é invalidado.
        # (O primeiro veto por checkpoint a secas pode ser anterior
        # ao Símbolo — a 1,05 e 1,20 o checkpoint 20 dispara sobre
        # um cluster tirânico ainda sem Símbolo — por isso a
        # comparação é entre os primeiros vetos RECLAMADOS.)
        linhas = {l["fator"]: l for l in sondar_vigilia_tick()}
        for fator, linha in linhas.items():
            self.assertEqual(
                linha["primeiro_veto_tick_reclamado"], linha["simbolo_tick"]
            )
            if linha["primeiro_veto_checkpoint_reclamado"] is not None:
                self.assertGreater(
                    linha["primeiro_veto_checkpoint_reclamado"],
                    linha["primeiro_veto_tick_reclamado"],
                )
        self.assertIsNone(linhas[1.00]["primeiro_veto_checkpoint_reclamado"])
        self.assertEqual(linhas[1.10]["primeiro_veto_checkpoint_reclamado"], 30)
        self.assertEqual(linhas[1.10]["primeiro_veto_tick_reclamado"], 28)
        self.assertEqual(linhas[1.05]["primeiro_veto_checkpoint"], 20)
        self.assertEqual(linhas[1.05]["primeiro_veto_checkpoint_reclamado"], 30)


if __name__ == "__main__":
    unittest.main()
