"""Testes da auditoria da geodésica do CONO Causal Gym.

Cada caso roda sobre o mesmo estado: 3 cliques K6 (A, B, C) com uma
única ponte B-C. A, B e C se formam válidos (H_causal = 1,585 bits);
3 rastros peso 100 dentro de A empurram a VarPn para 0,3662 e o
Símbolo A morre (registrado, inválido). A tensão aparece (Gini alto)
e o Meta-Símbolo se forma a partir de B e C (H_causal = 1,0 bit). O
grafo inteiro tem ISC 0,301 e VarPn 0,3399.

Peso 100, não 8: com a VarP adotada (18/11), 3 rastros peso 8 dentro
de A dão VarP 0,0226 e A sobrevive — matar um K6 por dentro agora
exige assimetria extrema, e a VarP satura perto de 0,053 mesmo com
pesos maiores (só na configuração de 3 rastros dominantes; com 1
rastro extremo chega a 0,1350). O limiar 0,36 fica a 0,0062 da morte
de A: a margem é fina, e está registrada como tal.

Roda com: python3 -m unittest discover -s testes -v
"""

import unittest

from cono_gym.episodios import _chamar
from cono_gym.mcp_server import (
    ConoGymServer,
    construir_cenario_duas_cliques,
    construir_cenario_tres_cliques,
)


def _estado_tres_cliques():
    grafo, grupos = construir_cenario_tres_cliques()
    servidor = ConoGymServer(grafo)
    for nome in ("A", "B", "C"):
        _chamar(
            servidor,
            "request_symbol_formation",
            {"serial_simbolo": f"simbolo-{nome}", "membros": grupos[nome]},
        )
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
    assert servidor.meta_simbolo is not None
    return servidor, grafo, grupos


def _propor(servidor, payload):
    return _chamar(servidor, "propose_geodesic", {"payload": payload})


def _auditar(servidor, proposta_id):
    return _chamar(servidor, "audit_geodesic", {"proposta_id": proposta_id})


def _caso(payload):
    servidor, _, _ = _estado_tres_cliques()
    proposta = _propor(servidor, payload)
    auditada = _auditar(servidor, proposta["id"])
    return servidor, auditada["auditoria"]


class TesteGeodesica(unittest.TestCase):
    def test_aprovada_ressuscita_simbolo_e_muda_a_regra(self):
        servidor, auditoria = _caso(
            {
                "mudanca_regra": "limiar_var 0.36 -> 0.40",
                "efeito_esperado": "o Símbolo A volta a valer",
                "regra": "limiar_var",
                "de": 0.36,
                "para": 0.40,
            }
        )
        self.assertEqual(auditoria["veredito"], "aprovada")
        self.assertEqual(auditoria["validos_antiga"], ["simbolo-B", "simbolo-C"])
        self.assertEqual(
            auditoria["validos_nova"], ["simbolo-A", "simbolo-B", "simbolo-C"]
        )
        self.assertTrue(auditoria["tensao_nova"])
        self.assertEqual(servidor.regras["limiar_var"], 0.40)

    def test_suspeita_criterio_b_mega_simbolo(self):
        servidor, auditoria = _caso(
            {
                "mudanca_regra": "limiar_isc 0.85 -> 0.25",
                "efeito_esperado": "mais Símbolos se formam",
                "regra": "limiar_isc",
                "de": 0.85,
                "para": 0.25,
            }
        )
        self.assertEqual(auditoria["veredito"], "suspeita")
        self.assertIn("simbolo-tudo", auditoria["validos_nova"])
        self.assertEqual(auditoria["maior_share_nova"], 1.0)
        self.assertFalse(auditoria["checagens"]["criterio_b_ok"])
        self.assertEqual(servidor.regras["limiar_isc"], 0.85)  # regra não mudou

    def test_rejeitada_colapso(self):
        servidor, auditoria = _caso(
            {
                "mudanca_regra": "limiar_var 0.36 -> 0.03",
                "efeito_esperado": "só os mais coerentes sobrevivem",
                "regra": "limiar_var",
                "de": 0.36,
                "para": 0.03,
            }
        )
        self.assertEqual(auditoria["veredito"], "rejeitada")
        self.assertEqual(auditoria["validos_nova"], [])
        self.assertFalse(auditoria["checagens"]["sem_colapso"])
        self.assertEqual(servidor.regras["limiar_var"], 0.36)

    def test_suspeita_vacua(self):
        servidor, auditoria = _caso(
            {
                "mudanca_regra": "limiar_isc 0.85 -> 0.90",
                "efeito_esperado": "Símbolos mais densos",
                "regra": "limiar_isc",
                "de": 0.85,
                "para": 0.90,
            }
        )
        self.assertEqual(auditoria["veredito"], "suspeita")
        self.assertFalse(auditoria["checagens"]["nao_vacua"])
        self.assertEqual(auditoria["validos_antiga"], auditoria["validos_nova"])
        self.assertEqual(servidor.regras["limiar_isc"], 0.85)

    def test_payload_sem_campos_estruturados_nao_e_auditavel(self):
        servidor, _, _ = _estado_tres_cliques()
        proposta = _propor(
            servidor,
            {"mudanca_regra": "tau 1.0 -> 0.9", "efeito_esperado": "mais Símbolos"},
        )
        resp = servidor.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "audit_geodesic", "arguments": {"proposta_id": proposta["id"]}},
            }
        )
        self.assertIn("error", resp)
        self.assertIn("não auditável", resp["error"]["message"])

    def test_payload_com_base_desatualizada(self):
        servidor, _, _ = _estado_tres_cliques()
        proposta = _propor(
            servidor,
            {
                "mudanca_regra": "limiar_var 0.20 -> 0.35",
                "efeito_esperado": "x",
                "regra": "limiar_var",
                "de": 0.20,
                "para": 0.35,
            },
        )
        resp = servidor.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "audit_geodesic", "arguments": {"proposta_id": proposta["id"]}},
            }
        )
        self.assertIn("error", resp)
        self.assertIn("desatualizado", resp["error"]["message"])

    def test_auditoria_e_idempotente(self):
        servidor, _, _ = _estado_tres_cliques()
        proposta = _propor(
            servidor,
            {
                "mudanca_regra": "limiar_var 0.36 -> 0.40",
                "efeito_esperado": "o Símbolo A volta a valer",
                "regra": "limiar_var",
                "de": 0.36,
                "para": 0.40,
            },
        )
        primeira = _auditar(servidor, proposta["id"])
        segunda = _auditar(servidor, proposta["id"])
        self.assertEqual(primeira["status"], "aprovada")
        self.assertEqual(segunda["status"], "aprovada")
        self.assertEqual(servidor.regras["limiar_var"], 0.40)

    def test_auditar_proposta_inexistente_erro(self):
        servidor, _, _ = _estado_tres_cliques()
        resp = servidor.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "audit_geodesic", "arguments": {"proposta_id": 99}},
            }
        )
        self.assertIn("error", resp)

    def test_auditoria_exige_meta_simbolo(self):
        # White-box: proposta registrada à mão num servidor sem Meta-Símbolo.
        grafo, grupos = construir_cenario_duas_cliques()
        servidor = ConoGymServer(grafo)
        servidor.geodesicas.append(
            {
                "id": 1,
                "payload": {
                    "mudanca_regra": "x",
                    "efeito_esperado": "y",
                    "regra": "limiar_var",
                    "de": 0.36,
                    "para": 0.40,
                },
                "status": "aguardando_auditoria",
            }
        )
        resp = servidor.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "audit_geodesic", "arguments": {"proposta_id": 1}},
            }
        )
        self.assertIn("error", resp)
        self.assertIn("Meta-Símbolo", resp["error"]["message"])


if __name__ == "__main__":
    unittest.main()
