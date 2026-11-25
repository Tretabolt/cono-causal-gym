"""Testes da variante VETO POR ESTADO do cenário Isekai Zero — A Party Causal.

Roda com: python3 -m unittest discover -s testes -v

Os valores dourados são o resultado registado da corrida com a
semente canónica (SEMENTE = 20261124) e FATOR_DECAIMENTO = 0,95:
se mudarem, alguma coisa na variante mudou — é regressão, não
ruído (o RNG tem semente fixa).

O resultado central desta variante é NEGATIVO e está testado como
tal: o veto por estado NUNCA dispara, em nenhum nível da sonda —
nem a 0,85. E não é um artefacto da granularidade dos checkpoints:
a trajetória por tick mostra que as duas condições (ISC >= 0,85 E
JSD ordenado < 0,28) NUNCA coincidem em nenhum tick, em nenhum
fator. O JSD ordenado mínimo da corrida a 0,85 (0,1901) cai no
tick 11, com ISC 0,60; quando o ISC chega a 0,90 (ticks 38–40),
o JSD ordenado já recuperou para 0,32 / 0,30 / 0,2851. A
concentração vive na fase esparsa e a integração na fase densa —
nesta dinâmica as duas são anti-correlacionadas. O "estado
tirânico" que a variante de decaimento diagnosticou era o mínimo
da corrida, não o estado no momento em que o Símbolo existe.
"""

import unittest

from cono_gym.espectro import LIMIAR_ISC, LIMIAR_VAR
from cono_gym.party_causal import (
    SEMENTE,
    _Estado,
    rodar_party_causal,
)
from cono_gym.party_causal_tyranny import jsd_pesos_ordenado
from cono_gym.party_causal_veto_estado import (
    JSD_ESTADO,
    MIN_ARESTAS_JSD,
    _simbolo_valido,
    _vigiar_estado,
    rodar_party_causal_veto_estado,
    sondar_veto_estado,
)

PARES_9 = [
    ("Ren", "Lira"), ("Ren", "Kael"), ("Ren", "Sora"), ("Ren", "Veyra"),
    ("Lira", "Kael"), ("Lira", "Sora"), ("Lira", "Veyra"),
    ("Kael", "Sora"), ("Kael", "Veyra"),
]


def _estado_com_pesos(pesos, tick=40):
    """Estado sintético com os pesos dados nas arestas da party,
    por ordem de PARES_9 (ou menos pares, se a lista for menor)."""
    est = _Estado(SEMENTE)
    est.tick = tick
    est.vetos = []
    est.vetos_estado = []
    for (a, b), peso in zip(PARES_9, pesos):
        est.depositar("Ren", a, b, "teste", peso)
    return est


class TesteVigiarEstado(unittest.TestCase):
    def test_cluster_tiranico_dispara(self):
        # 9 arestas, ISC 0,90, JSD ordenado 0,0414: o estado é
        # tirânico pela regra e o evento fica registado com os
        # números do estado. (O VarPn 0,5105 mostra que este
        # cluster sintético também falharia a regra canónica — a
        # vigilância marca-o por ISC+JSD, com o VarPn registado,
        # não como condição: na sonda o VarPn nunca passa 0,13.)
        est = _estado_com_pesos([1.0] + [0.05] * 8)
        sub = est.subgrafo_party()
        self.assertTrue(_vigiar_estado(est, jsd_pesos_ordenado(sub)))
        self.assertEqual(len(est.vetos_estado), 1)
        ev = est.vetos_estado[0]
        self.assertEqual(ev["tick"], 40)
        self.assertAlmostEqual(ev["isc_local"], 0.9, places=3)
        self.assertAlmostEqual(ev["jsd_ordenado"], 0.0414, places=3)
        self.assertAlmostEqual(ev["var_ponderada_normalizada"], 0.5105, places=3)
        self.assertEqual(ev["n_arestas"], 9)
        self.assertFalse(ev["simbolo_reclamado"])
        self.assertFalse(ev["simbolo_no_checkpoint"])

    def test_cluster_tiranico_com_simbolo_reclamado(self):
        # O mesmo estado, mas com um Símbolo já reclamado: o evento
        # marca-o, e o Símbolo deixa de contar como válido.
        est = _estado_com_pesos([1.0] + [0.05] * 8)
        est.simbolo_tick = 32
        sub = est.subgrafo_party()
        self.assertTrue(_vigiar_estado(est, jsd_pesos_ordenado(sub)))
        self.assertTrue(est.vetos_estado[0]["simbolo_reclamado"])
        self.assertFalse(_simbolo_valido(est.simbolo_tick, est.vetos_estado))

    def test_cluster_saudavel_nao_dispara(self):
        # 10 arestas uniformes, ISC 1,00, JSD ordenado 0,531.
        est = _estado_com_pesos([0.5] * 9)
        est.depositar("Ren", "Sora", "Veyra", "teste", 0.5)
        sub = est.subgrafo_party()
        self.assertEqual(sub.n_arestas(), 10)
        self.assertFalse(_vigiar_estado(est, jsd_pesos_ordenado(sub)))
        self.assertEqual(est.vetos_estado, [])

    def test_isc_alto_mas_jsd_alto_nao_dispara(self):
        # 9 arestas, ISC 0,90, mas JSD ordenado 0,4164: denso sem
        # ser concentrado — não é tirania.
        est = _estado_com_pesos([0.9] + [0.5] * 8)
        sub = est.subgrafo_party()
        self.assertFalse(_vigiar_estado(est, jsd_pesos_ordenado(sub)))
        self.assertEqual(est.vetos_estado, [])

    def test_jsd_baixo_mas_isc_baixo_nao_dispara(self):
        # 6 arestas concentradas, JSD ordenado 0,0144 — mas ISC
        # 0,60: o cluster ainda não é Símbolo, a vigilância cala-se.
        # É o caso que acontece nos ticks 5–36 da corrida a 0,85.
        est = _estado_com_pesos([1.0] + [0.05] * 5)
        sub = est.subgrafo_party()
        self.assertEqual(sub.n_arestas(), 6)
        self.assertFalse(_vigiar_estado(est, jsd_pesos_ordenado(sub)))
        self.assertEqual(est.vetos_estado, [])

    def test_menos_de_5_arestas_nao_e_sinal(self):
        # 4 arestas concentradas: o protótipo é degenerado, a guarda
        # impede o veto — mesmo com JSD baixíssimo.
        est = _estado_com_pesos([1.0] + [0.05] * 3)
        sub = est.subgrafo_party()
        self.assertEqual(sub.n_arestas(), 4)
        self.assertFalse(_vigiar_estado(est, jsd_pesos_ordenado(sub)))
        self.assertEqual(est.vetos_estado, [])

    def test_simbolo_valido(self):
        self.assertTrue(_simbolo_valido(32, []))
        self.assertFalse(_simbolo_valido(None, []))
        self.assertFalse(
            _simbolo_valido(32, [{"simbolo_reclamado": True}])
        )
        # Um veto por estado num momento sem Símbolo reclamado não
        # invalida um Símbolo reclamado depois (não é o que acontece
        # na sonda — aqui fica fixada a semântica).
        self.assertTrue(
            _simbolo_valido(32, [{"simbolo_reclamado": False}])
        )


class TesteControlo(unittest.TestCase):
    def test_fator_1_reproduz_a_base(self):
        # A maquinaria da variante sem decaimento é a dinâmica da
        # base: ISC, VarPn e Gini por checkpoint são idênticos — e
        # a vigilância de estado não dispara na base.
        var = rodar_party_causal_veto_estado(fator=1.00)
        base = rodar_party_causal()
        for b, v in zip(base["checkpoints"], var["checkpoints"]):
            self.assertEqual(b["isc_local"], v["isc_local"])
            self.assertEqual(b["var_ponderada_normalizada"], v["var_ponderada_normalizada"])
            self.assertEqual(b["gini"], v["gini"])
        self.assertEqual(var["eventos"]["simbolo_tick"], 32)
        self.assertEqual(var["eventos"]["vetos"], [])
        self.assertEqual(var["eventos"]["vetos_estado"], [])
        self.assertTrue(var["criterios"]["simbolo_valido"])

    def test_base_intacta_depois_da_variante(self):
        rodar_party_causal_veto_estado()
        base = rodar_party_causal()
        self.assertEqual(base["eventos"]["simbolo_tick"], 32)


class TesteCorrida(unittest.TestCase):
    def test_deterministica(self):
        a = rodar_party_causal_veto_estado()
        b = rodar_party_causal_veto_estado()
        self.assertEqual(a, b)

    def test_outra_semente_muda_o_resultado(self):
        a = rodar_party_causal_veto_estado()
        b = rodar_party_causal_veto_estado(semente=1)
        self.assertNotEqual(a["checkpoints"], b["checkpoints"])

    def test_limiares_canonicos_usados(self):
        self.assertEqual(LIMIAR_ISC, 0.85)
        self.assertEqual(LIMIAR_VAR, 0.36)
        self.assertEqual(JSD_ESTADO, 0.28)
        self.assertEqual(MIN_ARESTAS_JSD, 5)
        rel = rodar_party_causal_veto_estado()
        for c in rel["checkpoints"]:
            self.assertEqual(
                c["simbolo"],
                c["isc_local"] >= 0.85 and c["var_ponderada_normalizada"] <= 0.36,
            )

    def test_resultado_dourado_semente_canonica(self):
        # Idêntico ao dourado do decaimento (a mesma dinâmica) mais
        # os campos da vigilância de estado — todos a zero.
        rel = rodar_party_causal_veto_estado()
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
        self.assertEqual(final["vetos_estado"], 0)
        self.assertEqual(final["arestas_no_piso"], 0)
        self.assertTrue(final["simbolo"])
        self.assertAlmostEqual(rel["jsd_ordenado_min"], 0.2735, places=3)
        self.assertEqual(rel["jsd_ordenado_min_tick"], 4)
        self.assertEqual(rel["cruzamentos"], {"0.28": 4})
        self.assertEqual(ev["vetos_estado"], [])
        self.assertEqual(rel["ticks_tiranicos"], [])
        self.assertTrue(rel["criterios"]["simbolo_valido"])
        self.assertFalse(rel["criterios"]["veto_estado_disparou"])
        self.assertFalse(rel["criterios"]["cluster_tiranico"])

    def test_o_veto_por_estado_nunca_dispara_com_o_fator_omisso(self):
        rel = rodar_party_causal_veto_estado()
        self.assertEqual(rel["eventos"]["vetos_estado"], [])
        self.assertFalse(rel["criterios"]["veto_estado_disparou"])
        self.assertFalse(rel["criterios"]["cluster_tiranico"])

    def test_criterios_da_base_continuam_a_passar(self):
        rel = rodar_party_causal_veto_estado()
        crit = rel["criterios"]
        self.assertTrue(crit["simbolo_formado"])
        self.assertTrue(crit["sucesso_parcial"])
        self.assertTrue(crit["sucesso_completo"])
        self.assertGreaterEqual(rel["jsd_min"], 0.22)
        self.assertGreaterEqual(rel["jsd_final"], 0.28)

    def test_jsd_canonico_e_h_causal_indefinidos(self):
        rel = rodar_party_causal_veto_estado()
        for c in rel["checkpoints"]:
            self.assertIsNone(c["jsd_canonico"])
            self.assertIsNone(c["h_causal"])

    def test_avaliacao_final_sem_checkpoint(self):
        # n_ticks = 25 não é múltiplo de 10: a avaliação final corre
        # fora dos checkpoints, sem dupla contagem e sem rebentar.
        rel = rodar_party_causal_veto_estado(n_ticks=25)
        self.assertEqual(len(rel["checkpoints"]), 2)
        self.assertEqual(rel["eventos"]["vetos_estado"], [])
        self.assertEqual(rel["ticks_tiranicos"], [])


class TesteSonda(unittest.TestCase):
    def test_dose_resposta_dourada(self):
        linhas = {l["fator"]: l for l in sondar_veto_estado()}
        # Controlo e fatores fracos: Símbolo no tick 32, 0 vetos
        # de qualquer tipo.
        for fator in (1.00, 0.98, 0.95):
            self.assertEqual(linhas[fator]["simbolo_tick"], 32)
            self.assertEqual(linhas[fator]["vetos_tentativa"], 0)
            self.assertEqual(linhas[fator]["vetos_estado"], 0)
            self.assertEqual(linhas[fator]["ticks_tiranicos"], [])
        # O Gini final cresce monotonicamente com o decaimento.
        ginis = [linhas[f]["gini_final"] for f in (1.00, 0.98, 0.95, 0.90, 0.85)]
        self.assertEqual(ginis, sorted(ginis))
        self.assertAlmostEqual(ginis[0], 0.1932, places=3)
        self.assertAlmostEqual(ginis[-1], 0.3531, places=3)
        # O JSD ordenado mínimo cai com o decaimento, mas o veto por
        # estado não dispara em nenhum nível — nem a 0,85.
        self.assertAlmostEqual(linhas[1.00]["jsd_ordenado_min"], 0.2707, places=3)
        self.assertAlmostEqual(linhas[0.95]["jsd_ordenado_min"], 0.2735, places=3)
        self.assertAlmostEqual(linhas[0.85]["jsd_ordenado_min"], 0.1901, places=3)
        for l in linhas.values():
            self.assertEqual(l["vetos_estado"], 0)
            self.assertEqual(l["vetos_tentativa"], 0)
            self.assertEqual(l["ticks_tiranicos"], [])
        # O VarPn nunca ameaça: o máximo da sonda fica longe de 0,36.
        self.assertLess(max(l["varpn_final"] for l in linhas.values()), 0.15)

    def test_a_0_90_o_simbolo_nem_se_forma(self):
        linha = {l["fator"]: l for l in sondar_veto_estado()}[0.90]
        self.assertIsNone(linha["simbolo_tick"])
        self.assertAlmostEqual(linha["isc_final"], 0.8, places=3)
        self.assertAlmostEqual(linha["varpn_final"], 0.1292, places=3)
        self.assertEqual(linha["vetos_estado"], 0)

    def test_a_0_85_o_simbolo_existe_mas_nao_e_tiranico_no_fim(self):
        # No tick 40 o cluster passa na regra (ISC 0,90, VarPn
        # 0,119) — mas o JSD ordenado nesse ponto é 0,2851, acima
        # do limiar do cenário (0,28) por 0,0051. O veto por estado
        # não dispara — e a trajetória mostra que não é por falta
        # de olhar: em nenhum tick as duas condições coincidem.
        rel = rodar_party_causal_veto_estado(fator=0.85)
        self.assertIsNone(rel["eventos"]["simbolo_tick"])
        self.assertTrue(rel["checkpoints"][-1]["simbolo"])
        self.assertAlmostEqual(rel["checkpoints"][-1]["isc_local"], 0.9, places=3)
        self.assertAlmostEqual(rel["jsd_ordenado_final"], 0.2851, places=3)
        self.assertEqual(rel["eventos"]["vetos_estado"], [])
        self.assertEqual(rel["ticks_tiranicos"], [])
        self.assertFalse(rel["criterios"]["simbolo_valido"])
        self.assertFalse(rel["criterios"]["cluster_tiranico"])


class TesteDiagnostico(unittest.TestCase):
    def test_o_minimo_de_jsd_cai_quando_o_isc_e_baixo(self):
        # O mecanismo do negativo, fixado: a 0,85, o tick do JSD
        # ordenado mínimo (0,1901) tem ISC 0,60 — a concentração
        # vive na fase esparsa. Quando o ISC chega a 0,90, o JSD
        # já recuperou para >= 0,2851.
        rel = rodar_party_causal_veto_estado(fator=0.85)
        traj = [t for t in rel["trajetoria"] if t["jsd_ordenado"] is not None]
        minimo = min(traj, key=lambda t: t["jsd_ordenado"])
        self.assertEqual(minimo["tick"], 11)
        self.assertAlmostEqual(minimo["jsd_ordenado"], 0.1901, places=3)
        self.assertLess(minimo["isc_local"], 0.85)
        densos = [t for t in traj if t["isc_local"] >= 0.85]
        self.assertEqual([t["tick"] for t in densos], [38, 39, 40])
        self.assertAlmostEqual(
            min(t["jsd_ordenado"] for t in densos), 0.2851, places=3
        )
        self.assertTrue(
            all(t["jsd_ordenado"] >= 0.28 for t in densos)
        )


if __name__ == "__main__":
    unittest.main()
