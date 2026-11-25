"""Testes da variante VISÃO LOCAL (POMDP) da Party Causal.

A variante troca o que cada agente VÊ (raio 1 = só incidentes, raio 2
= incidentes + incidentes aos vizinhos, raio ∞ = controlo). Os testes
fixam: (a) os agentes ignoram um rastro forte que não veem; (b) o
controlo raio ∞ reproduz a base exactamente; (c) os números medidos
da corrida POMDP por raio.

Nota de construção: os estados de teste montam o grafo de verdade
directamente (est.grafo.depositar_rastro), como o Sistema faz — a
guarda de depósito é uma restrição da ACÇÃO do agente, não do grafo.
"""

import unittest

from cono_gym import party_causal as pc
from cono_gym.party_causal_pomdp import (
    _AGIR_POMDP,
    _EstadoPOMDP,
    _agir_kael_local,
    _agir_lira_local,
    _agir_ren_local,
    _agir_veyra_local,
    rodar_party_causal_pomdp,
    sondar_pomdp,
)

SEMENTE = pc.SEMENTE


class _RngFalso:
    """RNG de sorteios fixos (mesmo padrão dos testes da Sora):
    random() devolve os valores da lista, por ordem; uniform()
    devolve o máximo do intervalo."""

    def __init__(self, valores):
        self.valores = list(valores)
        self.i = 0

    def random(self):
        valor = self.valores[self.i]
        self.i += 1
        return valor

    def uniform(self, a, b):
        return b


def _estado(raio=1):
    """Estado POMDP fresco, com as listas de vetos que o portão de
    estado espera (a base não as define)."""
    est = _EstadoPOMDP(SEMENTE, raio)
    est.tick = 40
    est.vetos = []
    est.vetos_estado = []
    return est


def _rastro(est, a, b, peso, tipo="teste"):
    """Rastro de verdade no grafo (origem -> destino, com peso).
    Contorna a guarda de depósito — é o mundo, não uma acção."""
    est.grafo.depositar_rastro(est.hashes[a], est.hashes[b], tipo, peso)


class TesteVisao(unittest.TestCase):
    def _estado_grafo(self, raio=1):
        """Grafo conhecido: Ren-Lira, Ren-Kael, Lira-Sora + os dois
        rastros iniciais do Sistema (Sistema->Ren 0,12 e
        Sistema->Sora 0,87)."""
        est = _estado(raio)
        _rastro(est, "Ren", "Lira", 0.50)
        _rastro(est, "Ren", "Kael", 0.50)
        _rastro(est, "Lira", "Sora", 0.50)
        return est

    def test_raio_1_ve_so_incidentes(self):
        est = self._estado_grafo(raio=1)
        vistos_ren = {
            (est.nome_de_hash(r.origem), est.nome_de_hash(r.destino))
            for r in est.rastros_visiveis("Ren")
        }
        # Ren vê os seus incidentes (Sistema->Ren, Ren-Lira,
        # Ren-Kael) e NÃO o Sistema->Sora nem o Lira-Sora.
        self.assertEqual(
            {tuple(sorted(p)) for p in vistos_ren},
            {("Ren", "Sistema"), ("Lira", "Ren"), ("Kael", "Ren")},
        )
        vistos_lira = {
            tuple(sorted((est.nome_de_hash(r.origem), est.nome_de_hash(r.destino))))
            for r in est.rastros_visiveis("Lira")
        }
        self.assertEqual(
            vistos_lira, {("Lira", "Ren"), ("Lira", "Sora")}
        )

    def test_raio_2_ve_vizinhos(self):
        est = self._estado_grafo(raio=2)
        # Ren vê o Sistema->Sora via Sistema (distância 2).
        pares_ren = {
            tuple(sorted((est.nome_de_hash(r.origem), est.nome_de_hash(r.destino))))
            for r in est.rastros_visiveis("Ren")
        }
        self.assertIn(("Sistema", "Sora"), pares_ren)
        # Lira vê o Ren-Kael via Ren (distância 2).
        pares_lira = {
            tuple(sorted((est.nome_de_hash(r.origem), est.nome_de_hash(r.destino))))
            for r in est.rastros_visiveis("Lira")
        }
        self.assertIn(("Kael", "Ren"), pares_lira)

    def test_raio_infinito_ve_tudo(self):
        est = self._estado_grafo(raio=float("inf"))
        for nome in pc.NOMES[:5]:
            self.assertEqual(len(est.rastros_visiveis(nome)), 5)

    def test_distancia_via_sistema(self):
        est = _estado(raio=1)
        # Estado inicial: Ren-Sistema-Sora.
        self.assertEqual(est.distancia("Ren", "Sora"), 2)
        self.assertEqual(est.distancia("Ren", "Ren"), 0)
        self.assertEqual(est.distancia("Lira", "Sora"), float("inf"))
        _rastro(est, "Ren", "Sora", 0.50)
        self.assertEqual(est.distancia("Ren", "Sora"), 1)

    def test_isc_visivel(self):
        est = self._estado_grafo(raio=1)
        # Ren vê 2 arestas da party (Ren-Lira, Ren-Kael): 2/10.
        self.assertAlmostEqual(est.isc_visivel("Ren"), 0.2)
        self.assertAlmostEqual(est.isc_visivel("Lira"), 0.2)
        # A raio ∞ o ISC visível é o isc_party() exacto.
        est_inf = self._estado_grafo(raio=float("inf"))
        for nome in pc.NOMES[:5]:
            self.assertAlmostEqual(
                est_inf.isc_visivel(nome), est_inf.isc_party()
            )

    def test_forca_visivel_igual_base_a_raio_infinito(self):
        est = self._estado_grafo(raio=float("inf"))
        for nome in pc.NOMES[:5]:
            self.assertEqual(est.forca_visivel(nome), est.forca_membros())

    def test_membro_mais_fraco_visivel_igual_base_a_raio_infinito(self):
        est = self._estado_grafo(raio=float("inf"))
        for nome in pc.NOMES[:5]:
            for excluir in (None, "Ren", "Lira"):
                self.assertEqual(
                    est.membro_mais_fraco_visivel(nome, excluir=excluir),
                    est.membro_mais_fraco(excluir=excluir),
                )

    def test_rastros_extremos_visiveis_iguais_base_a_raio_infinito(self):
        est = self._estado_grafo(raio=float("inf"))
        for nome in pc.NOMES[:5]:
            forte = est.rastro_mais_forte_visivel(nome)
            self.assertEqual(forte.peso, est.rastro_mais_forte().peso)
            fraco = est.rastro_mais_fraco_visivel(nome)
            self.assertEqual(fraco.peso, est.rastro_mais_fraco().peso)


class TesteGuardas(unittest.TestCase):
    def test_depositar_nao_incidente_recusado(self):
        est = _estado(raio=1)
        self.assertIsNone(est.depositar("Lira", "Ren", "Kael", "teste", 0.50))
        self.assertIsNone(est.aresta("Ren", "Kael"))
        self.assertEqual(est.depositos["Lira"], 0)

    def test_depositar_incidente_funciona(self):
        est = _estado(raio=1)
        self.assertAlmostEqual(
            est.depositar("Lira", "Lira", "Ren", "teste", 0.50), 0.50
        )
        self.assertEqual(est.depositos["Lira"], 1)

    def test_seguir_nao_visivel_recusado(self):
        est = _estado(raio=1)
        _rastro(est, "Ren", "Veyra", 1.0)
        self.assertIsNone(est.seguir("Lira", "Ren", "Veyra"))
        self.assertAlmostEqual(est.peso("Ren", "Veyra"), 1.0)
        self.assertEqual(est.seguimentos["Lira"], 0)

    def test_seguir_visivel_funciona(self):
        est = _estado(raio=1)
        _rastro(est, "Sora", "Lira", 0.50)
        self.assertAlmostEqual(est.seguir("Lira", "Sora", "Lira"), 0.55)
        self.assertEqual(est.seguimentos["Lira"], 1)


class TesteIgnoraEscondido(unittest.TestCase):
    def test_lira_ignora_forte_escondido(self):
        """O rastro mais forte do grafo (Ren-Veyra 1,0) é invisível
        para a Lira a raio 1; o contra-rastro mira o mais forte
        que ela VÊ (Sora-Lira 0,85 -> Sora), não o escondido."""
        est = _estado(raio=1)
        _rastro(est, "Sora", "Lira", 0.85)
        _rastro(est, "Ren", "Lira", 0.50)
        _rastro(est, "Lira", "Kael", 0.50)
        _rastro(est, "Ren", "Veyra", 1.0)
        # Sorteios: 0,99 salta a equalização (dispersão > 0,25),
        # 0,10 entra no contra-rastro.
        est.rng = _RngFalso([0.99, 0.10])
        self.assertEqual(_agir_lira_local(est), "depositar_contra_rastro")
        self.assertEqual(est.depositos["Lira"], 1)
        # O depósito foi para a Sora (o par Lira-Sora fica com
        # ultimo_deposito no tick actual) e não para o Ren nem
        # para a Veyra (o Ren-Lira existe desde a montagem, sem
        # depósito; o Lira-Veyra nem existe).
        chave_sora = frozenset((est.hashes["Lira"], est.hashes["Sora"]))
        chave_ren = frozenset((est.hashes["Lira"], est.hashes["Ren"]))
        self.assertEqual(est.ultimo_deposito.get(chave_sora), 40)
        self.assertEqual(est.ultimo_deposito.get(chave_ren, 0), 0)
        self.assertIsNone(est.aresta("Lira", "Veyra"))
        self.assertAlmostEqual(est.peso("Ren", "Veyra"), 1.0)
        self.assertEqual(est.seguimentos["Lira"], 0)

    def test_kael_ignora_forte_escondido(self):
        """O mesmo, no filtro do Kael: o mais forte que ele vê é
        Sora-Kael 0,90 -> filtro para a Sora; o Ren-Veyra 1,0
        escondido não é tocado."""
        est = _estado(raio=1)
        _rastro(est, "Sora", "Kael", 0.90)
        _rastro(est, "Ren", "Veyra", 1.0)
        # Sorteios: 0,10 entra no ramo do filtro (< 0,75),
        # 0,90 deposita o filtro (>= 0,50 — abaixo disso ignora).
        est.rng = _RngFalso([0.10, 0.90])
        self.assertEqual(_agir_kael_local(est), "depositar_filtro")
        self.assertEqual(est.depositos["Kael"], 1)
        self.assertIsNone(est.aresta("Kael", "Ren"))
        self.assertIsNone(est.aresta("Kael", "Veyra"))
        self.assertAlmostEqual(est.peso("Ren", "Veyra"), 1.0)

    def test_ren_segue_verdadeiro_com_raio_1(self):
        """A mecânica central sobrevive: o verdadeiro fraco é
        incidente ao Ren, por isso ele vê-o e segue-o."""
        est = _estado(raio=1)
        est.rng = _RngFalso([0.10])
        self.assertEqual(_agir_ren_local(est), "seguir_verdadeiro")
        self.assertEqual(est.ren_verdadeiro, 1)

    def test_veyra_nao_ve_verdadeiro_com_raio_1(self):
        """A Veyra NÃO vê o Sistema->Ren (0,12): o mais fraco que
        ela vê é a sua própria aresta (Veyra-Lira 0,20) — e é essa
        que ela segue, não o verdadeiro fraco."""
        est = _estado(raio=1)
        _rastro(est, "Veyra", "Lira", 0.20)
        fraco = est.rastro_mais_fraco_visivel("Veyra")
        self.assertAlmostEqual(fraco.peso, 0.20)
        self.assertEqual(
            {est.nome_de_hash(fraco.origem), est.nome_de_hash(fraco.destino)},
            {"Veyra", "Lira"},
        )
        est.rng = _RngFalso([0.10])
        self.assertEqual(_agir_veyra_local(est), "seguir_fraco")
        self.assertEqual(est.veyra_verdadeiro, 0)
        self.assertAlmostEqual(est.peso("Veyra", "Lira"), 0.25)


class TesteControlo(unittest.TestCase):
    def test_raio_infinito_reproduz_base(self):
        """O controlo é a base, tick a tick: mesmos checkpoints,
        mesmos eventos, mesmos contadores."""
        base = pc.rodar_party_causal()
        ctrl = rodar_party_causal_pomdp(raio=float("inf"))
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
        self.assertEqual(ev_c["ren_verdadeiro"], ev_b["ren_verdadeiro"])
        self.assertEqual(ev_c["ren_verdadeiro"], 28)
        self.assertEqual(ev_c["ren_falso"], ev_b["ren_falso"])
        self.assertEqual(ev_c["ren_falso"], 1)
        self.assertEqual(ev_c["veyra_verdadeiro"], ev_b["veyra_verdadeiro"])
        self.assertEqual(ev_c["veyra_verdadeiro"], 6)
        self.assertEqual(ev_c["tentativas_simbolo"], ev_b["tentativas_simbolo"])
        self.assertEqual(ev_c["tentativas_simbolo"], 11)
        self.assertEqual(ev_c["depositos_por_agente"], ev_b["depositos_por_agente"])
        self.assertEqual(ev_c["seguimentos_por_agente"], ev_b["seguimentos_por_agente"])
        self.assertEqual(ctrl["jsd_min"], base["jsd_min"])
        self.assertEqual(ctrl["jsd_final"], base["jsd_final"])
        # O portão de estado (observador) não dispara no controlo.
        self.assertEqual(ctrl["eventos"]["vetos_estado"], [])
        self.assertTrue(ctrl["criterios"]["simbolo_valido"])

    def test_base_intacta_depois_da_variante(self):
        """A variante não remenda a base: correr a base depois da
        POMDP dá os mesmos números."""
        rodar_party_causal_pomdp(raio=1)
        rodar_party_causal_pomdp(raio=float("inf"))
        base = pc.rodar_party_causal()
        self.assertEqual(base["eventos"]["simbolo_tick"], 32)
        self.assertEqual(base["eventos"]["ren_verdadeiro"], 28)


class TesteCorridaPOMDP(unittest.TestCase):
    def test_raio_1_numeros(self):
        """Raio 1: o Símbolo NUNCA é tentado (0 tentativas — o ISC
        visível máximo da corrida é 0,40 < 0,70) e o cluster pára
        nos 0,80 (8 arestas): as duas arestas que faltam são as
        do Kael (Kael-Ren, Kael-Sora), e nem o Ren nem o Kael
        depositam uma única vez. O Ren segue o verdadeiro 33x —
        mais do que na base (28x) — e a Veyra 0x."""
        rel = rodar_party_causal_pomdp(raio=1)
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
        self.assertFalse(rel["criterios"]["simbolo_formado"])
        self.assertEqual(
            max(t["isc_visivel_max"] for t in rel["trajetoria"]), 0.4
        )

    def test_raio_2_numeros(self):
        """Raio 2: o Símbolo forma-se no tick 26 — ANTES da base
        (32) — e o cluster chega à clique completa (10 arestas,
        ISC 1,0), coisa que a base nunca faz (9 arestas). No fim
        os agentes veem tudo (ISC visível 1,0)."""
        rel = rodar_party_causal_pomdp(raio=2)
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
        self.assertTrue(rel["criterios"]["simbolo_valido"])
        self.assertEqual(rel["trajetoria"][-1]["isc_visivel_medio"], 1.0)
        self.assertEqual(rel["trajetoria"][-1]["isc_visivel_max"], 1.0)

    def test_sonda(self):
        linhas = sondar_pomdp()
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

    def test_determinismo(self):
        """Duas sondas completas dão os mesmos números."""
        self.assertEqual(sondar_pomdp(), sondar_pomdp())


if __name__ == "__main__":
    unittest.main()
