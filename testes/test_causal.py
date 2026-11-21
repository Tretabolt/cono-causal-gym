"""Testes da H_causal real do CONO Causal Gym.

Definição (corrigida 17/11 com a informação do Dan): H_causal é a
entropia de Shannon (base 2) sobre a distribuição normalizada dos ISCs
entre os Símbolos. O portão é um PISO: ISC_Global ≥ 0,80 e
H_causal ≥ log2(N)/2. A versão anterior deste arquivo media a entropia
do peso dos rastros entre Símbolos com teto H ≤ 0,1 — estava invertida
e foi apagada, não corrigida por cima.

Roda com: python3 -m unittest discover -s testes -v
"""

import unittest

from cono_gym.causal import (
    causal_entropy_bits,
    jsd_bits,
    jsd_para_tirania,
    jsd_uniforme_para_tirania,
    pode_emergir_meta_simbolo,
    prototipo_tirania,
    veto_jsd,
)
from cono_gym.episodios import _chamar
from cono_gym.mcp_server import (
    ConoGymServer,
    construir_cenario_duas_cliques,
    construir_cenario_tres_cliques,
)


def _formar(servidor, grupos):
    for nome, membros in grupos.items():
        _chamar(
            servidor,
            "request_symbol_formation",
            {"serial_simbolo": f"simbolo-{nome}", "membros": membros},
        )


class TesteHCausal(unittest.TestCase):
    def test_tirania_h_baixo(self):
        # Exemplo do Dan/glossário: 1 shard domina.
        tyranny = [0.90, 0.033, 0.033, 0.034]
        self.assertAlmostEqual(causal_entropy_bits(tyranny), 0.6275, places=3)

    def test_equilibrado_h_alto(self):
        balanced = [0.90, 0.88, 0.85, 0.89]
        self.assertAlmostEqual(causal_entropy_bits(balanced), 2.0, places=2)

    def test_cinco_simbolos_exemplo_do_dan(self):
        # [0.92, 0.88, 0.41, 0.37, 0.29] -> H ≈ 2.165 bits.
        cinco = [0.92, 0.88, 0.41, 0.37, 0.29]
        self.assertAlmostEqual(causal_entropy_bits(cinco), 2.165, places=2)

    def test_lista_vazia_h_zero(self):
        self.assertEqual(causal_entropy_bits([]), 0.0)

    def test_dois_iguais_h_um_bit(self):
        self.assertAlmostEqual(causal_entropy_bits([1.0, 1.0]), 1.0)

    def test_portao_tirania_bloqueia(self):
        tyranny = [0.90, 0.033, 0.033, 0.034]
        emergiu, isc_g, h, h_min = pode_emergir_meta_simbolo(tyranny, True)
        self.assertFalse(emergiu)
        self.assertAlmostEqual(isc_g, 0.25, places=2)
        self.assertAlmostEqual(h, 0.6275, places=3)
        self.assertAlmostEqual(h_min, 1.0)

    def test_portao_equilibrado_aprova(self):
        balanced = [0.90, 0.88, 0.85, 0.89]
        emergiu, isc_g, h, h_min = pode_emergir_meta_simbolo(balanced, True)
        self.assertTrue(emergiu)
        self.assertGreaterEqual(isc_g, 0.80)
        self.assertGreaterEqual(h, 1.0)

    def test_portao_cinco_simbolos_bloqueia_por_isc_global(self):
        # H passa (2.165 ≥ 1.161), mas a média dos ISCs é 0.574 < 0.80:
        # não emerge — fragmentada demais, não por falta de H.
        cinco = [0.92, 0.88, 0.41, 0.37, 0.29]
        emergiu, isc_g, h, h_min = pode_emergir_meta_simbolo(cinco, True)
        self.assertFalse(emergiu)
        self.assertAlmostEqual(isc_g, 0.574, places=2)
        self.assertGreaterEqual(h, h_min)

    def test_portao_exige_tensao_e_dois_simbolos(self):
        self.assertFalse(pode_emergir_meta_simbolo([0.9, 0.9], False)[0])
        self.assertFalse(pode_emergir_meta_simbolo([0.9], True)[0])

    def test_prototipo_tirania(self):
        p4 = prototipo_tirania(4)
        self.assertEqual(len(p4), 4)
        self.assertAlmostEqual(p4[0], 0.9)
        self.assertAlmostEqual(p4[1], 0.03333333333333333)
        self.assertAlmostEqual(sum(p4), 1.0)
        self.assertEqual(prototipo_tirania(2), [0.9, 0.1])
        self.assertAlmostEqual(sum(prototipo_tirania(5)), 1.0)

    def test_jsd_uniforme_dois_simbolos(self):
        # [0.5, 0.5] contra [0.9, 0.1]: 0.147 bits — a escala de 2
        # Símbolos é apertada; o veto usa a referência uniforme.
        self.assertAlmostEqual(jsd_para_tirania([1.0, 1.0]), 0.147, places=3)

    def test_jsd_tirania_zero(self):
        self.assertAlmostEqual(jsd_para_tirania([0.9, 0.033, 0.033, 0.034]), 0.0, places=3)

    def test_jsd_exemplo_heptagram(self):
        # Números do teste do harness: p_prop [0.6, 0.2, 0.1, 0.1]
        # contra a tirania fica abaixo de 0.15.
        p_prop = [0.6, 0.2, 0.1, 0.1]
        self.assertLess(jsd_bits(p_prop, prototipo_tirania(4)), 0.15)
        p_curr = [0.4, 0.3, 0.2, 0.1]
        self.assertGreater(jsd_bits(p_curr, prototipo_tirania(4)), 0.15)

    def test_veto_jsd(self):
        self.assertFalse(veto_jsd([1.0, 1.0])[0])
        self.assertFalse(veto_jsd([1.0, 1.0, 1.0])[0])
        self.assertTrue(veto_jsd([0.9, 0.1])[0])
        self.assertTrue(veto_jsd([0.9, 0.05, 0.05])[0])
        # A projeção do mega-símbolo (caso 2 da geodésica): [0.434,
        # 0.434, 0.131] fica abaixo da referência uniforme (0.267).
        self.assertTrue(veto_jsd([1.0, 1.0, 0.301])[0])
        self.assertFalse(veto_jsd([1.0])[0])

    def test_veto_jsd_regressao(self):
        # Regressão (DEFINICOES.md, seção 5): [1,1,1] -> [1,1,0.85] tem
        # JSD 0,2667 -> 0,2524 — acima do piso relativo (0,2167), então
        # o piso sozinho não vetaria, mas a regressão veta. O reverso
        # não veta, e com N diferente a regressão não se aplica.
        self.assertTrue(
            veto_jsd([1.0, 1.0, 0.85], iscs_antiga=[1.0, 1.0, 1.0])[0]
        )
        self.assertFalse(
            veto_jsd([1.0, 1.0, 1.0], iscs_antiga=[1.0, 1.0, 0.85])[0]
        )
        self.assertFalse(
            veto_jsd([1.0, 1.0, 0.85], iscs_antiga=[1.0, 1.0])[0]
        )

    def test_jsd_uniforme_cresce_com_n(self):
        self.assertLess(
            jsd_uniforme_para_tirania(2), jsd_uniforme_para_tirania(3)
        )
        self.assertLess(
            jsd_uniforme_para_tirania(3), jsd_uniforme_para_tirania(4)
        )

    def test_meta_forma_no_mundo_dois_cliques(self):
        grafo, grupos = construir_cenario_duas_cliques()
        servidor = ConoGymServer(grafo)
        _formar(servidor, grupos)
        for i in range(5):
            _chamar(
                servidor,
                "deposit_trail",
                {
                    "origem": grupos["A"][i],
                    "destino": grupos["B"][i],
                    "tipo_relacao": "ponte",
                    "peso": 8.0,
                },
            )
        self.assertIsNotNone(servidor.meta_simbolo)
        self.assertAlmostEqual(servidor.meta_simbolo["h_causal"], 1.0)
        self.assertAlmostEqual(servidor.meta_simbolo["isc_global"], 1.0)

    def test_meta_forma_no_mundo_tres_cliques(self):
        grafo, grupos = construir_cenario_tres_cliques()
        servidor = ConoGymServer(grafo)
        _formar(servidor, grupos)
        # Peso 100, não 8: com a VarP, 3 rastros peso 8 dentro de A dão
        # VarP 0,0226 e A sobrevive; é preciso peso 100 (VarPn 0,3662
        # > 0,36) para A morrer de verdade e o Meta-Símbolo nascer só
        # de B e C.
        for k in range(3):
            _chamar(
                servidor,
                "deposit_trail",
                {
                    "origem": grupos["A"][0],
                    "destino": grupos["A"][1 + k],
                    "tipo_relacao": "pesado",
                    "peso": 100.0,
                },
            )
        self.assertIsNotNone(servidor.meta_simbolo)
        self.assertAlmostEqual(servidor.meta_simbolo["h_causal"], 1.0)
        self.assertEqual(
            sorted(servidor.meta_simbolo["simbolos"]),
            ["simbolo-B", "simbolo-C"],
        )

    def test_meta_exige_dois_simbolos_validos(self):
        # Um Símbolo morto não conta: no mundo de 2 cliques, se A
        # morre antes da tensão aparecer, o Meta-Símbolo não se forma.
        # Peso 100 dentro de A: com a VarP, peso 8 não mata A (VarP
        # 0,0226); peso 100 mata (VarPn 0,3662 > 0,36).
        grafo, grupos = construir_cenario_duas_cliques()
        servidor = ConoGymServer(grafo)
        _formar(servidor, grupos)
        for k in range(3):
            _chamar(
                servidor,
                "deposit_trail",
                {
                    "origem": grupos["A"][0],
                    "destino": grupos["A"][1 + k],
                    "tipo_relacao": "pesado",
                    "peso": 100.0,
                },
            )
        for i in range(5):
            _chamar(
                servidor,
                "deposit_trail",
                {
                    "origem": grupos["A"][i],
                    "destino": grupos["B"][i],
                    "tipo_relacao": "ponte",
                    "peso": 8.0,
                },
            )
        self.assertEqual(len(servidor.simbolos_validos()), 1)
        self.assertIsNone(servidor.meta_simbolo)


if __name__ == "__main__":
    unittest.main()
