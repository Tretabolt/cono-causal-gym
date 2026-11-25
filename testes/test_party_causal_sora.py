"""Testes da variante SORA A AMPLIFICAR do cenário Isekai Zero — A Party Causal.

Roda com: python3 -m unittest discover -s testes -v

Os valores dourados são o resultado registado da corrida com a
semente canónica (SEMENTE = 20261124) e FATOR_DECAIMENTO = 0,95:
se mudarem, alguma coisa na variante mudou — é regressão, não
ruído (o RNG tem semente fixa).

O resultado central desta variante é NEGATIVO e está testado como
tal: o veto por estado NUNCA dispara, em nenhum nível da sonda —
nem a 1,50. E o negativo tem mecanismo, fixado em testes: a
amplificação faz o hub da Sora (a 1,50, as quatro arestas
incidentes à Sora estão em 0,95 e as outras seis em 0,26–0,43),
mas o JSD ordenado na fase densa SOBE com o fator (0,30 a 1,00
-> 0,41 a 1,50) — ou seja, afasta-se do limiar do veto, não se
aproxima. O protótipo de Tirania é um SÓ rastro dominante
[0,9, 0,011, ...]: um hub de quatro arestas fortes está LONGE
dele em JSD, por isso a medida não vê a tirania de hub — vê
"mais do que um rastro forte" como menos tirânico. O Gini vê o
hub por instantes (máximo 0,30 a 1,10) mas a saturação
uniformiza tudo a fatores altos e ele volta a cair. A
amplificação acelera a integração (o Símbolo forma-se no tick
17 a 1,50, contra 32 no controlo) — a primeira metade da
hipótese confirma-se; a segunda (concentração no momento do
Símbolo) falha, como medida.

Pelo caminho, a variante expôs um defeito latente da base:
quando o rastro mais forte tem origem na Lira ou no Kael, o
contra-rastro / filtro tenta depositar neles próprios e o grafo
rebenta (ValueError). Na base isto nunca acontece — o rastro
mais forte é sempre Sora->Ren ou Sistema->Sora. A variante usa
cópias guardadas da Lira e do Kael; os testes fixam o defeito
(a base rebenta, a guardada não) e o controlo (fator 1,00)
prova que a guarda nunca dispara na dinâmica da base.
"""

import random
import unittest

from cono_gym.espectro import LIMIAR_ISC, LIMIAR_VAR
from cono_gym.party_causal import (
    SEMENTE,
    _Estado,
    _agir_kael,
    _agir_lira,
    rodar_party_causal,
)
from cono_gym.party_causal_tyranny import jsd_pesos_ordenado
from cono_gym.party_causal_veto_estado import (
    JSD_ESTADO,
    MIN_ARESTAS_JSD,
    rodar_party_causal_veto_estado,
)
from cono_gym.party_causal_decaimento import _aplicar_decaimento
from cono_gym.party_causal_sora import (
    FATOR_AMPLIFICACAO,
    JOELHO_AMPLIFICACAO,
    _agir_kael_sem_autoalvo,
    _agir_lira_sem_autoalvo,
    _amplificar_sora,
    _fazer_agir_sora,
    rodar_party_causal_sora,
    sondar_sora,
)
import cono_gym.party_causal as pc


class _RngFalso:
    """RNG guiado: random() devolve os valores da lista, por ordem;
    uniform(a, b) devolve b. Serve para levar a Lira / o Kael até
    ao ramo do contra-rastro / filtro sem depender da semente."""

    def __init__(self, sorteios):
        self.sorteios = list(sorteios)
        self.i = 0

    def random(self):
        valor = self.sorteios[self.i]
        self.i += 1
        return valor

    def uniform(self, a, b):
        return b


def _estado_lira_autoalvo():
    """6 arestas, ISC 0,60: o rastro mais forte é Lira->Sora (1,0)
    — o contra-rastro da Lira mira nela própria. A dispersão de
    força (0,75) não dispara a equalização e o ISC não dispara a
    tentativa de Símbolo: a Lira chega ao contra-rastro."""
    est = _Estado(SEMENTE)
    est.tick = 40
    est.vetos = []
    est.vetos_estado = []
    for (a, b), peso in [
        (("Lira", "Sora"), 1.0),
        (("Ren", "Lira"), 0.5),
        (("Ren", "Kael"), 0.5),
        (("Ren", "Veyra"), 0.5),
        (("Lira", "Kael"), 0.5),
        (("Kael", "Sora"), 0.5),
    ]:
        est.depositar("Ren", a, b, "teste", peso)
    return est


def _estado_kael_autoalvo():
    """6 arestas, ISC 0,60: o rastro mais forte é Kael->Sora (1,0)
    — o filtro do Kael mira nele próprio. Gini 0,119 (< 0,30):
    a âncora não dispara a seguir."""
    est = _Estado(SEMENTE)
    est.tick = 40
    est.vetos = []
    est.vetos_estado = []
    for (a, b), peso in [
        (("Kael", "Sora"), 1.0),
        (("Ren", "Lira"), 0.5),
        (("Ren", "Kael"), 0.5),
        (("Ren", "Veyra"), 0.5),
        (("Lira", "Kael"), 0.5),
        (("Lira", "Veyra"), 0.5),
    ]:
        est.depositar("Ren", a, b, "teste", peso)
    return est


class TesteAmplificarSora(unittest.TestCase):
    def test_amplifica_so_as_incidentes_e_com_teto(self):
        est = _Estado(SEMENTE)
        est.tick = 10
        est.depositar("Ren", "Sora", "Ren", "teste", 0.5)
        est.depositar("Ren", "Sora", "Lira", "teste", 0.8)
        est.depositar("Ren", "Ren", "Lira", "teste", 0.5)
        n = _amplificar_sora(est, 1.5)
        self.assertEqual(n, 2)
        self.assertAlmostEqual(est.peso("Sora", "Ren"), 0.75, places=3)
        self.assertAlmostEqual(est.peso("Sora", "Lira"), 1.0, places=3)
        self.assertAlmostEqual(est.peso("Ren", "Lira"), 0.5, places=3)

    def test_fator_1_nao_muda_nada(self):
        est = _Estado(SEMENTE)
        est.tick = 10
        est.depositar("Ren", "Sora", "Ren", "teste", 0.5)
        antes = est.peso("Sora", "Ren")
        self.assertEqual(_amplificar_sora(est, 1.0), 0)
        self.assertEqual(est.peso("Sora", "Ren"), antes)

    def test_amplificar_nao_e_tocar(self):
        # A amplificação não atualiza ultimo_deposito: a aresta
        # amplificada continua a decair se ninguém a tocar — a
        # convenção do decaimento, documentada no módulo.
        est = _Estado(SEMENTE)
        est.tick = 10
        est.depositar("Ren", "Sora", "Ren", "teste", 0.5)
        chave = frozenset((est.hashes["Sora"], est.hashes["Ren"]))
        _amplificar_sora(est, 2.0)
        self.assertAlmostEqual(est.peso("Sora", "Ren"), 1.0, places=3)
        self.assertEqual(est.ultimo_deposito[chave], 10)
        est.tick = 11
        _aplicar_decaimento(est, 0.95, 0.05)
        self.assertAlmostEqual(est.peso("Sora", "Ren"), 0.95, places=3)

    def test_sora_ociosa_nao_amplifica(self):
        est = _Estado(SEMENTE)
        est.tick = 10
        est.depositar("Ren", "Sora", "Ren", "teste", 0.5)
        agir = _fazer_agir_sora(1.5)
        original = pc._agir_sora
        pc._agir_sora = lambda e: "ocioso"
        try:
            self.assertEqual(agir(est), "ocioso")
        finally:
            pc._agir_sora = original
        self.assertEqual(agir.contador, {"acoes": 0, "arestas": 0})
        self.assertAlmostEqual(est.peso("Sora", "Ren"), 0.5, places=3)

    def test_sora_em_acao_amplifica_e_conta(self):
        est = _Estado(SEMENTE)
        est.tick = 10
        est.depositar("Ren", "Sora", "Ren", "teste", 0.5)
        est.depositar("Ren", "Sora", "Lira", "teste", 0.5)
        agir = _fazer_agir_sora(1.5)
        original = pc._agir_sora
        pc._agir_sora = lambda e: "depositar_forte"
        try:
            self.assertEqual(agir(est), "depositar_forte")
        finally:
            pc._agir_sora = original
        self.assertEqual(agir.contador, {"acoes": 1, "arestas": 2})
        self.assertAlmostEqual(est.peso("Sora", "Ren"), 0.75, places=3)


class TesteGuardasAutoalvo(unittest.TestCase):
    def test_a_base_rebenta_no_contra_rastro_da_lira(self):
        # O defeito latente, fixado: a Lira da base tenta depositar
        # Lira->Lira quando o rastro mais forte tem origem nela.
        est = _estado_lira_autoalvo()
        # Sorteios: 0,99 (equalização: não), 0,01 (contra-rastro:
        # sim), 0,99 (seguir: não). A tentativa de Símbolo não
        # consome sorteio aqui (ISC 0,60 < 0,70, curto-circuito).
        est.rng = _RngFalso([0.99, 0.01, 0.99])
        with self.assertRaises(ValueError):
            _agir_lira(est)

    def test_a_lira_guardada_salta_o_autoalvo(self):
        est = _estado_lira_autoalvo()
        antes = dict(est.depositos)
        est.rng = _RngFalso([0.99, 0.01, 0.99])
        self.assertEqual(_agir_lira_sem_autoalvo(est), "ocioso")
        self.assertIsNone(est.aresta("Lira", "Lira"))
        self.assertEqual(est.depositos, antes)

    def test_a_base_rebenta_no_filtro_do_kael(self):
        est = _estado_kael_autoalvo()
        est.rng = _RngFalso([0.01, 0.99, 0.99, 0.99])
        with self.assertRaises(ValueError):
            _agir_kael(est)

    def test_o_kael_guardado_salta_o_autoalvo(self):
        est = _estado_kael_autoalvo()
        antes = dict(est.depositos)
        est.rng = _RngFalso([0.01, 0.99, 0.99, 0.99])
        self.assertEqual(_agir_kael_sem_autoalvo(est), "ocioso")
        self.assertIsNone(est.aresta("Kael", "Kael"))
        self.assertEqual(est.depositos, antes)


class TesteControlo(unittest.TestCase):
    def test_fator_1_reproduz_o_veto_estado(self):
        # A maquinaria da variante sem amplificação é a dinâmica do
        # veto-estado: ISC, VarPn e Gini por checkpoint são
        # idênticos — e nenhum veto dispara. Isto prova que as
        # guardas da Lira e do Kael nunca disparam no controlo.
        var = rodar_party_causal_sora(fator_amplificacao=1.00)
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

    def test_base_intacta_depois_da_variante(self):
        rodar_party_causal_sora()
        base = rodar_party_causal()
        self.assertEqual(base["eventos"]["simbolo_tick"], 32)


class TesteCorrida(unittest.TestCase):
    def test_deterministica(self):
        a = rodar_party_causal_sora()
        b = rodar_party_causal_sora()
        self.assertEqual(a, b)

    def test_outra_semente_muda_o_resultado(self):
        a = rodar_party_causal_sora()
        b = rodar_party_causal_sora(semente=1)
        self.assertNotEqual(a["checkpoints"], b["checkpoints"])

    def test_limiares_canonicos_usados(self):
        self.assertEqual(LIMIAR_ISC, 0.85)
        self.assertEqual(LIMIAR_VAR, 0.36)
        self.assertEqual(JSD_ESTADO, 0.28)
        self.assertEqual(MIN_ARESTAS_JSD, 5)
        self.assertEqual(FATOR_AMPLIFICACAO, 1.10)
        self.assertEqual(JOELHO_AMPLIFICACAO, 1.053)
        rel = rodar_party_causal_sora()
        for c in rel["checkpoints"]:
            self.assertEqual(
                c["simbolo"],
                c["isc_local"] >= 0.85 and c["var_ponderada_normalizada"] <= 0.36,
            )

    def test_resultado_dourado_semente_canonica(self):
        rel = rodar_party_causal_sora()
        ev = rel["eventos"]
        self.assertEqual(ev["simbolo_tick"], 28)
        self.assertEqual(ev["ren_verdadeiro"], 28)
        self.assertEqual(ev["ren_falso"], 0)
        self.assertEqual(ev["veyra_verdadeiro"], 3)
        self.assertEqual(ev["tentativas_simbolo"], 10)
        # 3, não 2 como no veto-estado: o Símbolo forma-se no tick
        # 28, por isso há tentativas de Meta-Símbolo na formação e
        # nos checkpoints 30 e 40.
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
        self.assertEqual(final["vetos"], 0)
        self.assertEqual(final["vetos_estado"], 0)
        self.assertEqual(final["arestas_no_piso"], 0)
        self.assertTrue(final["simbolo"])
        self.assertAlmostEqual(rel["jsd_ordenado_min"], 0.2611, places=3)
        self.assertEqual(rel["jsd_ordenado_min_tick"], 4)
        self.assertEqual(rel["cruzamentos"], {"0.28": 4})
        self.assertEqual(ev["vetos_estado"], [])
        self.assertEqual(rel["ticks_tiranicos"], [])
        self.assertTrue(rel["criterios"]["simbolo_valido"])
        self.assertFalse(rel["criterios"]["veto_estado_disparou"])
        self.assertFalse(rel["criterios"]["cluster_tiranico"])
        self.assertTrue(rel["criterios"]["sora_amplificou"])

    def test_o_veto_por_estado_nunca_dispara_com_o_fator_omisso(self):
        rel = rodar_party_causal_sora()
        self.assertEqual(rel["eventos"]["vetos_estado"], [])
        self.assertFalse(rel["criterios"]["veto_estado_disparou"])
        self.assertFalse(rel["criterios"]["cluster_tiranico"])
        self.assertEqual(rel["ticks_tiranicos"], [])

    def test_criterios_da_base_continuam_a_passar(self):
        rel = rodar_party_causal_sora()
        crit = rel["criterios"]
        self.assertTrue(crit["simbolo_formado"])
        self.assertTrue(crit["sucesso_parcial"])
        self.assertTrue(crit["sucesso_completo"])
        self.assertGreaterEqual(rel["jsd_min"], 0.22)
        self.assertGreaterEqual(rel["jsd_final"], 0.28)

    def test_jsd_canonico_e_h_causal_indefinidos(self):
        rel = rodar_party_causal_sora()
        for c in rel["checkpoints"]:
            self.assertIsNone(c["jsd_canonico"])
            self.assertIsNone(c["h_causal"])

    def test_avaliacao_final_sem_checkpoint(self):
        # n_ticks = 25 não é múltiplo de 10: a avaliação final corre
        # fora dos checkpoints, sem dupla contagem e sem rebentar.
        rel = rodar_party_causal_sora(n_ticks=25)
        self.assertEqual(len(rel["checkpoints"]), 2)
        self.assertEqual(rel["eventos"]["vetos_estado"], [])
        self.assertEqual(rel["ticks_tiranicos"], [])


class TesteSonda(unittest.TestCase):
    def test_dose_resposta_dourada(self):
        linhas = {l["fator"]: l for l in sondar_sora()}
        dourado = {
            1.00: (32, 0.2471, 0.2735, 0.3323, 0.0964, 1.0, 0),
            1.05: (25, 0.291, 0.2703, 0.3271, 0.1154, 0.9, 107),
            1.10: (28, 0.3007, 0.2611, 0.4286, 0.1039, 1.0, 96),
            1.20: (21, 0.2765, 0.2686, 0.4509, 0.105, 1.0, 85),
            1.50: (17, 0.2568, 0.302, 0.4548, 0.0996, 1.0, 90),
        }
        for fator, (tick, gini, jsd_min, jsd_fin, varpn, isc, ampl) in dourado.items():
            linha = linhas[fator]
            self.assertEqual(linha["simbolo_tick"], tick)
            self.assertEqual(linha["vetos_tentativa"], 0)
            self.assertEqual(linha["vetos_estado"], 0)
            self.assertEqual(linha["ticks_tiranicos"], [])
            self.assertAlmostEqual(linha["gini_final"], gini, places=3)
            self.assertAlmostEqual(linha["jsd_ordenado_min"], jsd_min, places=3)
            self.assertEqual(linha["jsd_ordenado_min_tick"], 4)
            self.assertAlmostEqual(linha["jsd_ordenado_final"], jsd_fin, places=3)
            self.assertAlmostEqual(linha["varpn_final"], varpn, places=3)
            self.assertAlmostEqual(linha["isc_final"], isc, places=3)
            self.assertEqual(linha["total_amplificacoes"], ampl)
        # O VarPn nunca ameaça: o máximo da sonda fica longe de 0,36.
        self.assertLess(max(l["varpn_final"] for l in linhas.values()), 0.15)

    def test_o_simbolo_forma_se_mais_cedo_com_amplificacao(self):
        linhas = {l["fator"]: l for l in sondar_sora()}
        self.assertEqual(linhas[1.00]["simbolo_tick"], 32)
        self.assertEqual(linhas[1.50]["simbolo_tick"], 17)
        self.assertLess(linhas[1.50]["simbolo_tick"], linhas[1.00]["simbolo_tick"])

    def test_o_gini_final_nao_e_monotono(self):
        # O Gini vê o hub por instantes: máximo a 1,10 (0,3007),
        # depois a saturação uniformiza tudo e ele volta a cair.
        linhas = {l["fator"]: l for l in sondar_sora()}
        ginis = [linhas[f]["gini_final"] for f in (1.00, 1.05, 1.10, 1.20, 1.50)]
        self.assertAlmostEqual(max(ginis), 0.3007, places=3)
        self.assertEqual(ginis.index(max(ginis)), 2)
        self.assertLess(ginis[-1], ginis[2])

    def test_o_ren_continua_a_seguir_o_verdadeiro(self):
        for fator in (1.00, 1.05, 1.10, 1.20, 1.50):
            rel = rodar_party_causal_sora(fator_amplificacao=fator)
            self.assertGreaterEqual(rel["eventos"]["ren_verdadeiro"], 23)
            self.assertEqual(rel["eventos"]["ren_falso"], 0 if fator > 1.00 else 2)
            self.assertTrue(rel["criterios"]["ren_verdadeiro_ge_2"])
            self.assertTrue(rel["criterios"]["sucesso_completo"])


class TesteDiagnostico(unittest.TestCase):
    def _jsd_denso_min(self, rel):
        densos = [
            t for t in rel["trajetoria"]
            if t["isc_local"] >= 0.85 and t["jsd_ordenado"] is not None
        ]
        return min(t["jsd_ordenado"] for t in densos) if densos else None

    def test_o_jsd_na_fase_densa_sobe_com_o_fator(self):
        # O mecanismo do negativo, fixado: o JSD ordenado mínimo
        # NA FASE DENSA (ISC >= 0,85) cresce monotonicamente com a
        # amplificação — 0,30 -> 0,41. A amplificação afasta o
        # cluster do limiar do veto, não o aproxima.
        minimos = []
        for fator in (1.00, 1.05, 1.10, 1.20, 1.50):
            rel = rodar_party_causal_sora(fator_amplificacao=fator)
            minimos.append(self._jsd_denso_min(rel))
        self.assertEqual(
            [round(m, 3) for m in minimos], [0.305, 0.326, 0.395, 0.397, 0.41]
        )
        self.assertEqual(minimos, sorted(minimos))
        self.assertGreater(min(minimos), 0.28)

    def test_o_minimo_de_jsd_cai_sempre_na_fase_esparsa(self):
        # Em todos os níveis, o JSD ordenado mínimo da corrida cai
        # no tick 4, com ISC baixo — a concentração continua a viver
        # na fase esparsa, mesmo com o hub da Sora.
        for fator in (1.00, 1.05, 1.10, 1.20, 1.50):
            rel = rodar_party_causal_sora(fator_amplificacao=fator)
            self.assertEqual(rel["jsd_ordenado_min_tick"], 4)
            tick4 = next(t for t in rel["trajetoria"] if t["tick"] == 4)
            self.assertLess(tick4["isc_local"], 0.85)

    def test_o_hub_da_sora_forma_se_a_1_50(self):
        # A 1,50, as quatro arestas incidentes à Sora estão em 0,95
        # e as outras seis em 0,26–0,43: o hub existe, bimodal e
        # limpo — e mesmo assim o JSD ordenado final é 0,4548, o
        # mais alto da sonda. O hub não é o que o protótipo de
        # Tirania mede.
        rel = rodar_party_causal_sora(fator_amplificacao=1.50)
        pesos = rel["pesos_finais"]
        incidentes = sorted(p["peso"] for p in pesos if p["incidente_sora"])
        restantes = sorted(p["peso"] for p in pesos if not p["incidente_sora"])
        self.assertEqual(len(incidentes), 4)
        self.assertEqual(incidentes, [0.95, 0.95, 0.95, 0.95])
        self.assertEqual(len(restantes), 6)
        self.assertLessEqual(max(restantes), 0.44)
        self.assertAlmostEqual(rel["jsd_ordenado_final"], 0.4548, places=3)

    def test_sem_hub_no_controlo(self):
        # A 1,00, só uma aresta incidente à Sora é forte (0,9483);
        # as outras três estão em 0,21–0,27, como o resto do grafo.
        rel = rodar_party_causal_sora(fator_amplificacao=1.00)
        pesos = rel["pesos_finais"]
        incidentes = sorted(p["peso"] for p in pesos if p["incidente_sora"])
        self.assertEqual(len(incidentes), 4)
        self.assertAlmostEqual(incidentes[-1], 0.9483, places=3)
        self.assertLess(incidentes[-2], 0.27)


if __name__ == "__main__":
    unittest.main()
