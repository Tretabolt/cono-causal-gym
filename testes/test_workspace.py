"""Testes do Espaço J do CONO Causal Gym.

O Espaço J é o análogo funcional do J-space (Anthropic, jul/2026):
pequeno e seletivo, relatável, segurável, usável no raciocínio e
editável de um jeito que muda o comportamento. Cada propriedade tem
um teste aqui. O estado-base é o mesmo da geodésica: 3 cliques K6,
A morto perto da borda (VarPn 0,3662), B e C válidos, Meta-Símbolo
formado.

Roda com: python3 -m unittest discover -s testes -v
"""

import unittest

from cono_gym.episodios import LoopEpisodios, _chamar
from cono_gym.mcp_server import (
    ConoGymServer,
    construir_cenario_duas_cliques,
    construir_cenario_tres_cliques,
)
from cono_gym.workspace import EspacoJ
from testes.test_geodesica import _estado_tres_cliques


def _segurar(servidor, regra, de, para, motivo, tipo="direcao"):
    return _chamar(
        servidor,
        "hold_direction",
        {"tipo": tipo, "regra": regra, "de": de, "para": para, "motivo": motivo},
    )


def _propor_do_workspace(servidor, direcao_id):
    return _chamar(
        servidor,
        "propose_geodesic",
        {"payload": {"do_workspace": True, "direcao_id": direcao_id}},
    )


class TesteEspacoJ(unittest.TestCase):
    def test_capacidade_despeja_a_mais_antiga(self):
        espaco = EspacoJ(capacidade=3)
        for i in range(4):
            espaco.segurar("direcao", "limiar_var", 0.36, 0.40 + i * 0.01, f"m{i}")
        self.assertEqual(len(espaco), 3)
        ids = [c["id"] for c in espaco.relatar()]
        self.assertEqual(ids, [2, 3, 4])

    def test_segurar_devolve_a_despejada(self):
        espaco = EspacoJ(capacidade=2)
        espaco.segurar("direcao", "limiar_var", 0.36, 0.40, "primeira")
        espaco.segurar("direcao", "limiar_var", 0.36, 0.41, "segunda")
        resultado = espaco.segurar("direcao", "limiar_var", 0.36, 0.42, "terceira")
        self.assertEqual(resultado["despejado"]["motivo"], "primeira")
        self.assertEqual(resultado["segurado"]["motivo"], "terceira")

    def test_editar_muda_o_conteudo_segurado(self):
        espaco = EspacoJ()
        espaco.segurar("direcao", "limiar_var", 0.36, 0.40, "afrouxar")
        editado = espaco.editar(1, para=0.03, motivo="apertar")
        self.assertEqual(editado["para"], 0.03)
        self.assertEqual(editado["motivo"], "apertar")
        self.assertEqual(espaco.relatar()[0]["para"], 0.03)

    def test_hold_sem_meta_e_recusado(self):
        grafo, _ = construir_cenario_duas_cliques()
        servidor = ConoGymServer(grafo)
        self.assertIsNone(servidor.meta_simbolo)
        with self.assertRaises(RuntimeError):
            _segurar(servidor, "limiar_var", 0.36, 0.40, "sem meta")


class TesteWorkspaceNoServidor(unittest.TestCase):
    def test_propor_do_workspace_aprovada(self):
        # A direção segurada (0.36 -> 0.40) ressuscita A: aprovada, e a
        # regra vigente muda de verdade.
        servidor, _, _ = _estado_tres_cliques()
        segurado = _segurar(
            servidor, "limiar_var", 0.36, 0.40, "ressuscitar A"
        )
        direcao_id = segurado["segurado"]["id"]
        proposta = _propor_do_workspace(servidor, direcao_id)
        auditada = _chamar(
            servidor, "audit_geodesic", {"proposta_id": proposta["id"]}
        )
        self.assertEqual(auditada["auditoria"]["veredito"], "aprovada")
        self.assertEqual(servidor.regras["limiar_var"], 0.40)

    def test_swap_muda_o_veredito(self):
        # O teste da troca (aranha -> formiga): a mesma direção segurada,
        # com o `para` editado de 0.40 para 0.03, vira colapso — a edição
        # no workspace muda o comportamento.
        servidor, _, _ = _estado_tres_cliques()
        segurado = _segurar(
            servidor, "limiar_var", 0.36, 0.40, "ressuscitar A"
        )
        direcao_id = segurado["segurado"]["id"]
        _chamar(
            servidor,
            "edit_direction",
            {"direcao_id": direcao_id, "mudancas": {"para": 0.03}},
        )
        proposta = _propor_do_workspace(servidor, direcao_id)
        auditada = _chamar(
            servidor, "audit_geodesic", {"proposta_id": proposta["id"]}
        )
        self.assertEqual(auditada["auditoria"]["veredito"], "rejeitada")
        self.assertEqual(servidor.regras["limiar_var"], 0.36)

    def test_relatar_mostra_o_que_o_meta_segura(self):
        servidor, _, _ = _estado_tres_cliques()
        _segurar(servidor, "limiar_var", 0.36, 0.40, "ressuscitar A")
        relato = _chamar(servidor, "report_workspace")
        self.assertEqual(len(relato["conteudos"]), 1)
        self.assertEqual(relato["conteudos"][0]["motivo"], "ressuscitar A")
        self.assertEqual(relato["capacidade"], 3)


class TesteAutoProposta(unittest.TestCase):
    def test_auto_proposta_dispara_perto_da_borda(self):
        # A morto a 0,0062 da borda: o Meta-Símbolo gera a direção
        # sozinho, segura, propõe e a auditoria aprova.
        servidor, _, _ = _estado_tres_cliques()
        resultado = servidor.tentar_auto_proposta()
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado["veredito"], "aprovada")
        self.assertEqual(servidor.regras["limiar_var"], 0.40)
        relato = _chamar(servidor, "report_workspace")
        self.assertEqual(len(relato["conteudos"]), 1)
        self.assertTrue(relato["conteudos"][0]["proposto"])

    def test_loop_padrao_nao_propoe_sem_motivo(self):
        # No loop padrão (12 episódios, semente 42) nenhum Símbolo chega
        # perto da borda — o Meta-Símbolo não inventa direção sem motivo
        # medido, e o meta continua se formando no episódio 4.
        grafo, grupos = construir_cenario_duas_cliques()
        servidor = ConoGymServer(grafo)
        clusters = {
            "A": grupos["A"],
            "B": grupos["B"],
        }
        resultado = LoopEpisodios(servidor, clusters).rodar(12)
        self.assertEqual(resultado["resumo"]["episodio_meta"], 4)
        self.assertTrue(
            all(e["auto_proposta"] is None for e in resultado["episodios"])
        )


if __name__ == "__main__":
    unittest.main()
