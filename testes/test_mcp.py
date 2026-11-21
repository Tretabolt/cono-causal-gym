"""Testes do MCP server do CONO Causal Gym.

Roda com: python3 -m unittest discover -s testes -v
"""

import unittest

from cono_gym.auditoria import auditoria_diversidade, gini
from cono_gym.espectro import avaliar_cluster
from cono_gym.grafo import GrafoCausal, UIF
from cono_gym.mcp_server import ConoGymServer, construir_cenario_duas_cliques


def _servidor_com_clique(n=6):
    grafo = GrafoCausal()
    hs = []
    for i in range(n):
        uif = UIF(serial=f"k{i}", tipo_agente="no", funcao_s=f"no-{i}")
        grafo.adicionar_uif(uif)
        hs.append(uif.hash_uif)
    for i in range(n):
        for j in range(i + 1, n):
            grafo.depositar_rastro(hs[i], hs[j], "liga", peso=1.0)
    return ConoGymServer(grafo), hs


def _chamar(servidor, nome, argumentos=None):
    return servidor.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": nome, "arguments": argumentos or {}},
        }
    )


def _resultado(resp):
    return resp["result"]["content"][0]["data"]


class TesteGini(unittest.TestCase):
    def test_uniforme_e_zero(self):
        self.assertAlmostEqual(gini([1.0, 1.0, 1.0, 1.0]), 0.0)

    def test_um_forte_tres_fracos(self):
        # média 2, soma das diffs 24, G = 24 / (2*16*2) = 0.375
        self.assertAlmostEqual(gini([1.0, 1.0, 1.0, 5.0]), 0.375)


class TesteTransporte(unittest.TestCase):
    def test_initialize_e_tools_list(self):
        servidor, _ = _servidor_com_clique()
        resp = servidor.handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        self.assertEqual(resp["result"]["serverInfo"]["name"], "cono-causal-gym")
        resp = servidor.handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        nomes = [t["name"] for t in resp["result"]["tools"]]
        self.assertEqual(
            nomes,
            [
                "create_uif",
                "get_local_causal_view",
                "deposit_trail",
                "follow_trail",
                "inspect_identity",
                "request_symbol_formation",
                "propose_geodesic",
                "audit_geodesic",
                "request_diversity_audit",
            ],
        )

    def test_tool_desconhecida_recusada(self):
        servidor, _ = _servidor_com_clique()
        resp = _chamar(servidor, "abrir_porta")
        self.assertIn("error", resp)
        self.assertIn("AI-Jail", resp["error"]["message"])

    def test_metodo_desconhecido(self):
        servidor, _ = _servidor_com_clique()
        resp = servidor.handle_request({"jsonrpc": "2.0", "id": 9, "method": "nada"})
        self.assertEqual(resp["error"]["code"], -32601)


class TesteToolsBasicas(unittest.TestCase):
    def test_depositar_e_ver_vista_local(self):
        servidor, hs = _servidor_com_clique()
        resp = _chamar(
            servidor,
            "get_local_causal_view",
            {"hash_uif": hs[0]},
        )
        dados = _resultado(resp)
        self.assertEqual(dados["centro"], hs[0])
        self.assertEqual(len(dados["vizinhos"]), 6)  # o próprio + 5 vizinhos

    def test_follow_trail_move_o_foco(self):
        servidor, hs = _servidor_com_clique()
        rastro = servidor.grafo.rastro_por_hash(
            servidor.grafo.todos_rastros()[0].hash_rastro
        )
        resp = _chamar(servidor, "follow_trail", {"hash_rastro": rastro.hash_rastro})
        dados = _resultado(resp)
        self.assertEqual(dados["foco"], rastro.destino)
        self.assertEqual(servidor.foco, rastro.destino)

    def test_follow_trail_desconhecido_erro(self):
        servidor, _ = _servidor_com_clique()
        resp = _chamar(servidor, "follow_trail", {"hash_rastro": "inexistente"})
        self.assertIn("error", resp)

    def test_inspect_identity_so_mostra_hash_e_tipo(self):
        servidor, hs = _servidor_com_clique()
        dados = _resultado(_chamar(servidor, "inspect_identity", {"hash_uif": hs[0]}))
        self.assertEqual(set(dados), {"hash_uif", "tipo_agente"})
        self.assertEqual(dados["hash_uif"], hs[0])

    def test_peso_nao_positivo_erro(self):
        servidor, hs = _servidor_com_clique()
        resp = _chamar(
            servidor,
            "deposit_trail",
            {"origem": hs[0], "destino": hs[1], "tipo_relacao": "x", "peso": 0},
        )
        self.assertIn("error", resp)


class TesteSimboloEMeta(unittest.TestCase):
    def test_estrela_nao_forma_simbolo(self):
        grafo = GrafoCausal()
        centro = UIF(serial="c", tipo_agente="d", funcao_s="d")
        grafo.adicionar_uif(centro)
        for nome in ("a", "b", "e"):
            uif = UIF(serial=nome, tipo_agente="s", funcao_s=nome)
            grafo.adicionar_uif(uif)
            grafo.depositar_rastro(uif.hash_uif, centro.hash_uif, "causa")
        servidor = ConoGymServer(grafo)
        dados = _resultado(
            _chamar(
                servidor,
                "request_symbol_formation",
                {"serial_simbolo": "sim-estrela"},
            )
        )
        self.assertFalse(dados["simbolo"])
        self.assertFalse(dados["registrado"])
        self.assertEqual(servidor.simbolos, {})

    def test_dois_simbolos_uniformes_nao_formam_meta(self):
        grafo, grupos = construir_cenario_duas_cliques()
        servidor = ConoGymServer(grafo)
        for serial, membros in (("simbolo-A", grupos["A"]), ("simbolo-B", grupos["B"])):
            dados = _resultado(
                _chamar(
                    servidor,
                    "request_symbol_formation",
                    {"serial_simbolo": serial, "membros": membros},
                )
            )
            self.assertTrue(dados["simbolo"])
        self.assertIsNone(servidor.meta_simbolo)
        auditoria = auditoria_diversidade(grafo, list(servidor.simbolos.values()))
        self.assertAlmostEqual(auditoria["gini_pesos"], 0.0)
        self.assertFalse(auditoria["tensao_presente"])

    def test_gates_sem_meta_simbolo(self):
        grafo, grupos = construir_cenario_duas_cliques()
        servidor = ConoGymServer(grafo)
        _chamar(
            servidor,
            "request_symbol_formation",
            {"serial_simbolo": "simbolo-A", "membros": grupos["A"]},
        )
        resp = _chamar(servidor, "request_diversity_audit")
        self.assertIn("error", resp)
        resp = _chamar(
            servidor,
            "propose_geodesic",
            {"payload": {"mudanca_regra": "x", "efeito_esperado": "y"}},
        )
        self.assertIn("error", resp)

    def test_rastros_pesados_formam_meta_e_auditoria_passa(self):
        grafo, grupos = construir_cenario_duas_cliques()
        servidor = ConoGymServer(grafo)
        for serial, membros in (("simbolo-A", grupos["A"]), ("simbolo-B", grupos["B"])):
            _chamar(
                servidor,
                "request_symbol_formation",
                {"serial_simbolo": serial, "membros": membros},
            )
        self.assertIsNone(servidor.meta_simbolo)
        for i in range(5):
            dados = _resultado(
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
            )
        self.assertIsNotNone(servidor.meta_simbolo)
        self.assertTrue(dados["meta_simbolo_existe"])
        auditoria = _resultado(_chamar(servidor, "request_diversity_audit"))
        self.assertTrue(auditoria["tensao_presente"])
        self.assertGreaterEqual(auditoria["gini_pesos"], 0.30)

    def test_geodesica_registrada_nao_aprovada(self):
        grafo, grupos = construir_cenario_duas_cliques()
        servidor = ConoGymServer(grafo)
        for serial, membros in (("simbolo-A", grupos["A"]), ("simbolo-B", grupos["B"])):
            _chamar(
                servidor,
                "request_symbol_formation",
                {"serial_simbolo": serial, "membros": membros},
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
        dados = _resultado(
            _chamar(
                servidor,
                "propose_geodesic",
                {"payload": {"mudanca_regra": "tau 1.0 -> 0.9", "efeito_esperado": "mais Símbolos"}},
            )
        )
        self.assertEqual(dados["status"], "aguardando_auditoria")
        self.assertEqual(len(servidor.geodesicas), 1)
        resp = _chamar(
            servidor,
            "propose_geodesic",
            {"payload": {"mudanca_regra": "tau 1.0"}},
        )
        self.assertIn("error", resp)


class TesteCriarUif(unittest.TestCase):
    def test_criar_retorna_hash_canonico(self):
        from cono_gym.hasher import hash_uif

        servidor, _ = _servidor_com_clique()
        dados = _resultado(
            _chamar(
                servidor,
                "create_uif",
                {
                    "serial": "uif-nova",
                    "tipo_agente": "no",
                    "funcao_s": "no-nova",
                },
            )
        )
        self.assertTrue(dados["criado"])
        self.assertEqual(dados["serial"], "uif-nova")
        self.assertEqual(
            dados["hash_uif"], hash_uif("uif-nova", "no", "no-nova")
        )
        self.assertIsNotNone(servidor.grafo.uif_por_hash(dados["hash_uif"]))

    def test_criar_duplicado_recusado(self):
        servidor, _ = _servidor_com_clique()
        args = {
            "serial": "uif-nova",
            "tipo_agente": "no",
            "funcao_s": "no-nova",
        }
        _resultado(_chamar(servidor, "create_uif", args))
        n_antes = len(servidor.grafo.hashes())
        resp = _chamar(servidor, "create_uif", args)
        self.assertIn("error", resp)
        self.assertIn("serial já existe", resp["error"]["message"])
        self.assertEqual(len(servidor.grafo.hashes()), n_antes)
        # Nem com outro tipo/função o mesmo serial passa.
        resp = _chamar(
            servidor,
            "create_uif",
            {"serial": "uif-nova", "tipo_agente": "outro", "funcao_s": "x"},
        )
        self.assertIn("error", resp)

    def test_criar_argumentos_invalidos(self):
        servidor, _ = _servidor_com_clique()
        resp = _chamar(
            servidor,
            "create_uif",
            {"serial": "   ", "tipo_agente": "no", "funcao_s": "x"},
        )
        self.assertIn("error", resp)
        resp = _chamar(
            servidor,
            "create_uif",
            {"serial": "uif-x", "tipo_agente": "no"},
        )
        self.assertIn("error", resp)

    def test_criada_isolada_e_inspecionavel(self):
        servidor, _ = _servidor_com_clique()
        dados = _resultado(
            _chamar(
                servidor,
                "create_uif",
                {"serial": "uif-so", "tipo_agente": "no", "funcao_s": "no-so"},
            )
        )
        h = dados["hash_uif"]
        identidade = _resultado(
            _chamar(servidor, "inspect_identity", {"hash_uif": h})
        )
        self.assertEqual(identidade["hash_uif"], h)
        self.assertEqual(identidade["tipo_agente"], "no")
        vista = _resultado(
            _chamar(servidor, "get_local_causal_view", {"hash_uif": h, "raio": 1})
        )
        # A vista inclui o próprio centro, sem nenhum rastro: isolada.
        self.assertEqual(len(vista["vizinhos"]), 1)
        self.assertEqual(vista["vizinhos"][0]["hash_uif"], h)
        self.assertEqual(vista["vizinhos"][0]["rastros"], [])

    def test_crescer_nova_clique_e_formar_simbolo(self):
        # O gym pode crescer: 6 UIFs criadas pela tool, ligadas em K6,
        # formam um Símbolo válido — sem nenhum grafo pré-construído.
        servidor, _ = _servidor_com_clique(n=0)
        hs = []
        for i in range(6):
            dados = _resultado(
                _chamar(
                    servidor,
                    "create_uif",
                    {
                        "serial": f"uif-n{i}",
                        "tipo_agente": "no",
                        "funcao_s": f"no-n{i}",
                    },
                )
            )
            hs.append(dados["hash_uif"])
        for i in range(6):
            for j in range(i + 1, 6):
                _resultado(
                    _chamar(
                        servidor,
                        "deposit_trail",
                        {
                            "origem": hs[i],
                            "destino": hs[j],
                            "tipo_relacao": "liga",
                            "peso": 1.0,
                        },
                    )
                )
        rel = _resultado(
            _chamar(
                servidor,
                "request_symbol_formation",
                {"serial_simbolo": "simbolo-novo", "membros": hs},
            )
        )
        self.assertTrue(rel["simbolo"])
        self.assertTrue(rel["registrado"])
        self.assertEqual(rel["isc_local"], 1.0)
        self.assertAlmostEqual(rel["var_lambda"], 0.2, places=3)

    def test_criar_nao_perturba_meta_existente(self):
        servidor, grupos = _servidor_com_meta()
        meta_antes = servidor.meta_simbolo["hash_meta_simbolo"]
        validos_antes = sorted(
            s["serial"] for s in servidor.simbolos_validos()
        )
        _resultado(
            _chamar(
                servidor,
                "create_uif",
                {"serial": "uif-tardia", "tipo_agente": "no", "funcao_s": "x"},
            )
        )
        self.assertEqual(
            servidor.meta_simbolo["hash_meta_simbolo"], meta_antes
        )
        self.assertEqual(
            sorted(s["serial"] for s in servidor.simbolos_validos()),
            validos_antes,
        )


def _servidor_com_meta():
    grafo, grupos = construir_cenario_duas_cliques()
    servidor = ConoGymServer(grafo)
    for nome in ("A", "B"):
        _chamar(
            servidor,
            "request_symbol_formation",
            {"serial_simbolo": f"simbolo-{nome}", "membros": grupos[nome]},
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
    assert servidor.meta_simbolo is not None
    return servidor, grupos


if __name__ == "__main__":
    unittest.main()
