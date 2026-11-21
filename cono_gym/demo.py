"""Demo do esqueleto do MVP: quatro clusters, quatro vereditos.

- estrela: a topologia da rede-pulsos (sol, calor, chuva -> decisão).
- ciclo-5: um anel de 5 UIFs.
- clique-5: K5, o menor grafo completo que passa no limite de Var.
- clique-6: K6, um Símbolo folgado.

Uso: python3 -m cono_gym.demo
"""

from .espectro import avaliar_cluster
from .grafo import GrafoCausal, UIF


def _cluster(nomes, arestas):
    grafo = GrafoCausal()
    uifs = {}
    for nome in nomes:
        uif = UIF(serial=f"uif-{nome}", tipo_agente="sensor", funcao_s=nome)
        grafo.adicionar_uif(uif)
        uifs[nome] = uif.hash_uif
    for a, b in arestas:
        grafo.depositar_rastro(uifs[a], uifs[b], "causa")
    return grafo


def _completo(n):
    nomes = [f"c{i}" for i in range(n)]
    arestas = [(a, b) for i, a in enumerate(nomes) for b in nomes[i + 1 :]]
    return _cluster(nomes, arestas)


def main():
    casos = [
        ("estrela (rede-pulsos)", _cluster(
            ["sol", "calor", "chuva", "decisao"],
            [("sol", "decisao"), ("calor", "decisao"), ("chuva", "decisao")],
        )),
        ("ciclo-5", _cluster(
            [f"n{i}" for i in range(5)],
            [(f"n{i}", f"n{(i + 1) % 5}") for i in range(5)],
        )),
        ("clique-5 (K5)", _completo(5)),
        ("clique-6 (K6)", _completo(6)),
    ]
    print(f"{'cluster':<22} {'nós':>3} {'arestas':>7} {'ISC':>5} {'VarPn':>7}  Símbolo?")
    for nome, grafo in casos:
        rel = avaliar_cluster(grafo, f"simbolo-{nome}")
        esp = "[" + ", ".join(f"{v:.3f}" for v in rel["espectro"]) + "]"
        print(
            f"{nome:<22} {rel['nos']:>3} {rel['arestas']:>7} "
            f"{rel['isc_local']:>5.2f} {rel['var_ponderada_normalizada']:>7.4f}  "
            f"{'SIM' if rel['simbolo'] else 'NÃO'}   λ={esp}"
        )
        if rel["simbolo"]:
            print(f"{'':<22} Hash_Símbolo: {rel['hash_simbolo'][:16]}…")
    print()
    print("Leitura honesta: os primeiros Símbolos do gym são cliques densos.")
    print("ISC 1.0 sozinho é armadilha (estagnação). Falta medir a tensão")
    print("diversidade × coerência — é o próximo passo, não este esqueleto.")


if __name__ == "__main__":
    main()
