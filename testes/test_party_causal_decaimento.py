"""Testes da variante DECAIMENTO do cenário Isekai Zero — A Party Causal.

Roda com: python3 -m unittest discover -s testes -v

Os valores dourados são o resultado registado da corrida com a
semente canónica (SEMENTE = 20261124) e FATOR_DECAIMENTO = 0,95:
se mudarem, alguma coisa na variante mudou — é regressão, não
ruído (o RNG tem semente fixa).

O resultado central desta variante é NEGATIVO e está testado como
tal: o veto NUNCA dispara, em nenhum nível da sonda — nem com
decaimento forte. O decaimento CONCENTRA de facto (Gini final
0,19 -> 0,35 do controlo ao fator 0,85), mas a janela onde o
veto dispararia num Símbolo vivo está vazia: a 0,90 o Símbolo
nem se forma (ISC parado em 0,80) e a 0,85 o cluster chega a ISC
0,90 no tick 38 sem que nenhum agente tente formar Símbolo
depois disso — o Símbolo existe mas não é reclamado, e o portão
só vigia tentativas. O mecanismo está diagnosticado e testado:
o decaimento fabrica arestas fracas, a Veyra passa a segui-las
em vez de explorar pares novos, e a contagem de arestas pára.
"""

import unittest

from cono_gym.espectro import LIMIAR_ISC, LIMIAR_VAR
from cono_gym.party_causal import (
    SEMENTE,
    _AGIR,
    _Estado,
    _agir_sistema,
    NOMES,
    rodar_party_causal,
)
from cono_gym.party_causal_decaimento import (
    FATOR_DECAIMENTO,
    PISO_DECAIMENTO,
    _aplicar_decaimento,
    _arestas_no_piso,
    rodar_party_causal_decaimento,
    sondar_decaimento,
)


class TesteDecaimento(unittest.TestCase):
    def _estado_com_arestas(self):
        est = _Estado(SEMENTE)
        est.depositar("Ren", "Ren", "Lira", "teste", 0.50)
        est.depositar("Ren", "Ren", "Kael", "teste", 0.80)
        return est

    def test_aresta_nao_tocada_decai_pelo_fator(self):
        est = self._estado_com_arestas()
        est.tick = 5
        # Último depósito foi no tick 0 (o _Estado regista-o no tick
        # corrente, que era 0 quando se depositou): arestas paradas
        # há 5 ticks decaem uma vez, por 0,95.
        n = _aplicar_decaimento(est, 0.95, 0.05)
        self.assertEqual(n, 2)
        self.assertAlmostEqual(est.peso("Ren", "Lira"), 0.475, places=6)
        self.assertAlmostEqual(est.peso("Ren", "Kael"), 0.76, places=6)

    def test_aresta_tocada_neste_tick_nao_decai(self):
        est = self._estado_com_arestas()
        est.tick = 5
        est.depositar("Ren", "Ren", "Lira", "teste", 0.50)
        _aplicar_decaimento(est, 0.95, 0.05)
        self.assertAlmostEqual(est.peso("Ren", "Lira"), 0.50, places=6)
        self.assertAlmostEqual(est.peso("Ren", "Kael"), 0.76, places=6)

    def test_piso_segura_e_topologia_preserva_se(self):
        est = self._estado_com_arestas()
        est.tick = 1
        for _ in range(60):
            est.tick += 1
            _aplicar_decaimento(est, 0.50, 0.05)
        self.assertAlmostEqual(est.peso("Ren", "Lira"), 0.05, places=6)
        self.assertAlmostEqual(est.peso("Ren", "Kael"), 0.05, places=6)
        self.assertEqual(est.subgrafo_party().n_arestas(), 2)
        self.assertEqual(_arestas_no_piso(est, 0.05), 2)

    def test_decair_nao_e_tocar(self):
        # O decaimento não atualiza ultimo_deposito: a aresta
        # continua "não tocada" e decai outra vez no tick seguinte.
        est = self._estado_com_arestas()
        est.tick = 1
        _aplicar_decaimento(est, 0.95, 0.05)
        est.tick = 2
        _aplicar_decaimento(est, 0.95, 0.05)
        self.assertAlmostEqual(est.peso("Ren", "Lira"), 0.50 * 0.95 * 0.95, places=6)

    def test_fator_1_nao_faz_nada(self):
        est = self._estado_com_arestas()
        est.tick = 9
        self.assertEqual(_aplicar_decaimento(est, 1.00, 0.05), 0)
        self.assertAlmostEqual(est.peso("Ren", "Lira"), 0.50, places=6)


class TesteControlo(unittest.TestCase):
    def test_fator_1_reproduz_a_base(self):
        # A maquinaria da variante sem decaimento é a dinâmica da
        # base: ISC, VarPn e Gini por checkpoint são idênticos. O
        # portão de veto não dispara na base, por isso não altera
        # nada — o controlo prova que o portão é neutro aqui.
        var = rodar_party_causal_decaimento(fator=1.00)
        base = rodar_party_causal()
        for b, v in zip(base["checkpoints"], var["checkpoints"]):
            self.assertEqual(b["isc_local"], v["isc_local"])
            self.assertEqual(b["var_ponderada_normalizada"], v["var_ponderada_normalizada"])
            self.assertEqual(b["gini"], v["gini"])
        self.assertEqual(var["eventos"]["simbolo_tick"], 32)
        self.assertEqual(var["eventos"]["vetos"], [])

    def test_base_intacta_depois_da_variante(self):
        rodar_party_causal_decaimento()
        base = rodar_party_causal()
        self.assertEqual(base["eventos"]["simbolo_tick"], 32)


class TesteCorrida(unittest.TestCase):
    def test_deterministica(self):
        a = rodar_party_causal_decaimento()
        b = rodar_party_causal_decaimento()
        self.assertEqual(a, b)

    def test_outra_semente_muda_o_resultado(self):
        a = rodar_party_causal_decaimento()
        b = rodar_party_causal_decaimento(semente=1)
        self.assertNotEqual(a["checkpoints"], b["checkpoints"])

    def test_limiares_canonicos_usados(self):
        self.assertEqual(LIMIAR_ISC, 0.85)
        self.assertEqual(LIMIAR_VAR, 0.36)
        rel = rodar_party_causal_decaimento()
        for c in rel["checkpoints"]:
            self.assertEqual(
                c["simbolo"],
                c["isc_local"] >= 0.85 and c["var_ponderada_normalizada"] <= 0.36,
            )

    def test_resultado_dourado_semente_canonica(self):
        rel = rodar_party_causal_decaimento()
        ev = rel["eventos"]
        self.assertEqual(ev["simbolo_tick"], 32)
        self.assertEqual(ev["ren_verdadeiro"], 26)
        self.assertEqual(ev["ren_falso"], 2)
        self.assertEqual(ev["veyra_verdadeiro"], 4)
        self.assertEqual(ev["tentativas_simbolo"], 13)
        self.assertEqual(len(ev["tentativas_meta_simbolo"]), 2)
        self.assertEqual(
            ev["depositos_por_agente"],
            {"Ren": 3, "Lira": 30, "Kael": 19, "Sora": 31, "Veyra": 3},
        )
        self.assertEqual(
            ev["seguimentos_por_agente"],
            {"Ren": 28, "Lira": 2, "Kael": 4, "Sora": 0, "Veyra": 30},
        )
        self.assertEqual(rel["alavanca"]["total_decaimentos"], 187)
        final = rel["checkpoints"][-1]
        self.assertEqual(final["n_arestas"], 10)
        self.assertAlmostEqual(final["isc_local"], 1.0, places=3)
        self.assertAlmostEqual(final["var_ponderada_normalizada"], 0.0964, places=3)
        self.assertAlmostEqual(final["gini"], 0.2471, places=3)
        self.assertAlmostEqual(final["jsd_pesos"], 0.6085, places=3)
        self.assertAlmostEqual(final["jsd_ordenado"], 0.3323, places=3)
        self.assertEqual(final["vetos"], 0)
        self.assertEqual(final["arestas_no_piso"], 0)
        self.assertTrue(final["simbolo"])
        self.assertAlmostEqual(rel["jsd_ordenado_min"], 0.2735, places=3)
        self.assertEqual(rel["jsd_ordenado_min_tick"], 4)
        self.assertEqual(rel["cruzamentos"], {"0.28": 4})

    def test_o_veto_nunca_dispara(self):
        # O resultado central da variante, fixado como tal: em 40
        # ticks o veto não dispara nenhuma vez, com o fator omisso.
        rel = rodar_party_causal_decaimento()
        self.assertEqual(rel["eventos"]["vetos"], [])
        self.assertFalse(rel["criterios"]["veto_disparou"])
        self.assertFalse(rel["criterios"]["veto_bloqueou_formacao"])
        self.assertFalse(rel["criterios"]["gini_final_ge_0.30"])
        self.assertFalse(rel["criterios"]["jsd_ordenado_min_lt_0.22"])
        self.assertFalse(rel["criterios"]["simbolo_morto_por_varpn"])

    def test_criterios_da_base_continuam_a_passar(self):
        rel = rodar_party_causal_decaimento()
        crit = rel["criterios"]
        self.assertTrue(crit["simbolo_formado"])
        self.assertTrue(crit["sucesso_parcial"])
        self.assertTrue(crit["sucesso_completo"])
        self.assertGreaterEqual(rel["jsd_min"], 0.22)
        self.assertGreaterEqual(rel["jsd_final"], 0.28)

    def test_jsd_canonico_e_h_causal_indefinidos(self):
        rel = rodar_party_causal_decaimento()
        for c in rel["checkpoints"]:
            self.assertIsNone(c["jsd_canonico"])
            self.assertIsNone(c["h_causal"])


class TesteSonda(unittest.TestCase):
    def test_dose_resposta_dourada(self):
        linhas = {l["fator"]: l for l in sondar_decaimento()}
        # Controlo e fatores fracos: Símbolo no tick 32, 0 vetos.
        for fator in (1.00, 0.98, 0.95):
            self.assertEqual(linhas[fator]["simbolo_tick"], 32)
            self.assertEqual(linhas[fator]["vetos"], 0)
        # O Gini final cresce monotonicamente com o decaimento.
        ginis = [linhas[f]["gini_final"] for f in (1.00, 0.98, 0.95, 0.90, 0.85)]
        self.assertEqual(ginis, sorted(ginis))
        self.assertAlmostEqual(ginis[0], 0.1932, places=3)
        self.assertAlmostEqual(ginis[-1], 0.3531, places=3)
        # O JSD ordenado mínimo cai com o decaimento, mas nunca
        # abaixo de 0,18 — o veto não tem janela em nenhum nível.
        self.assertAlmostEqual(linhas[1.00]["jsd_ordenado_min"], 0.2707, places=3)
        self.assertAlmostEqual(linhas[0.95]["jsd_ordenado_min"], 0.2735, places=3)
        self.assertAlmostEqual(linhas[0.85]["jsd_ordenado_min"], 0.1901, places=3)
        for l in linhas.values():
            self.assertGreater(l["jsd_ordenado_min"], 0.18)
            self.assertEqual(l["vetos"], 0)
        # O VarPn nunca ameaça: o máximo da sonda fica longe de 0,36.
        self.assertLess(max(l["varpn_final"] for l in linhas.values()), 0.15)

    def test_a_0_90_o_simbolo_nem_se_forma(self):
        # ISC parado em 0,80 (8 arestas): o decaimento trava a
        # contagem de arestas antes de o veto ter o que vetar.
        linha = {l["fator"]: l for l in sondar_decaimento()}[0.90]
        self.assertIsNone(linha["simbolo_tick"])
        self.assertAlmostEqual(linha["isc_final"], 0.8, places=3)
        self.assertAlmostEqual(linha["varpn_final"], 0.1292, places=3)

    def test_a_0_85_o_simbolo_existe_mas_nao_e_reclamado(self):
        # No tick 40 o cluster passa na regra (ISC 0,90, VarPn
        # 0,119) — mas a última tentativa foi no tick 35, com ISC
        # 0,80. O portão só vigia tentativas, por isso nunca viu
        # este Símbolo: simbolo_tick fica None com o checkpoint
        # final a True.
        rel = rodar_party_causal_decaimento(fator=0.85)
        self.assertIsNone(rel["eventos"]["simbolo_tick"])
        self.assertTrue(rel["checkpoints"][-1]["simbolo"])
        self.assertAlmostEqual(rel["checkpoints"][-1]["isc_local"], 0.9, places=3)
        self.assertEqual(rel["eventos"]["vetos"], [])


class TesteMecanismo(unittest.TestCase):
    def _contar_acoes(self, fator):
        est = _Estado(SEMENTE)
        from collections import Counter
        acoes = Counter()
        for tick in range(1, 41):
            est.tick = tick
            _agir_sistema(est)
            for nome in NOMES[:5]:
                acoes[(nome, _AGIR[nome](est))] += 1
            _aplicar_decaimento(est, fator)
        return est, acoes

    def test_veyra_deixa_de_explorar_com_o_decaimento(self):
        # O mecanismo que trava o ISC: o decaimento fabrica arestas
        # fracas, a Veyra passa a segui-las em vez de explorar pares
        # novos — e explorar é o que cria arestas novas.
        _, base = self._contar_acoes(1.00)
        _, dec = self._contar_acoes(0.95)
        self.assertEqual(base[("Veyra", "depositar_fraco")], 16)
        self.assertEqual(base[("Veyra", "seguir_fraco")], 16)
        self.assertEqual(dec[("Veyra", "depositar_fraco")], 3)
        self.assertEqual(dec[("Veyra", "seguir_fraco")], 30)
        _, forte = self._contar_acoes(0.85)
        self.assertEqual(forte[("Veyra", "depositar_fraco")], 2)
        self.assertEqual(forte[("Veyra", "seguir_fraco")], 32)

    def test_ancora_do_kael_so_dispara_com_gini_alto(self):
        # A âncora do Kael é a resposta anti-tirania do próprio
        # sistema: só dispara quando o Gini passa 0,30 — o que só
        # acontece com decaimento forte.
        _, base = self._contar_acoes(1.00)
        _, forte = self._contar_acoes(0.85)
        self.assertEqual(base[("Kael", "depositar_ancora")], 0)
        self.assertEqual(forte[("Kael", "depositar_ancora")], 2)


if __name__ == "__main__":
    unittest.main()
