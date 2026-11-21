"""Demo do loop de episódios: 12 episódios, semente 42.

O agente deposita 3 rastros por episódio e tenta formar Símbolo nos
dois clusters e no grafo inteiro. A tabela mostra, por episódio, o que
foi medido — não o que foi prometido.

Uso: python3 -m cono_gym.demo_episodios
"""

from .episodios import LoopEpisodios
from .mcp_server import ConoGymServer, construir_cenario_duas_cliques


def main():
    grafo, grupos = construir_cenario_duas_cliques()
    servidor = ConoGymServer(grafo)
    loop = LoopEpisodios(servidor, clusters=grupos, semente=42)
    relatorio = loop.rodar(n_episodios=12)

    print(f"{'ep':>3} {'reg':>3} {'vál':>3} {'rastros':>7} {'Gini':>6} {'Var méd':>7} {'H_caus':>6} {'ISC_gl':>6}  tensão  meta")
    for e in relatorio["episodios"]:
        h = e["h_causal"]
        isc_g = e["isc_global"]
        print(
            f"{e['episodio']:>3} {e['n_registrados']:>3} {e['n_validos']:>3} "
            f"{e['n_rastros']:>7} {e['gini_pesos']:>6.3f} "
            f"{e['var_media'] if e['var_media'] is not None else float('nan'):>7.3f} "
            f"{h if h is not None else float('nan'):>6.3f} "
            f"{isc_g if isc_g is not None else float('nan'):>6.3f}  "
            f"{'SIM' if e['tensao_presente'] else 'não':<6} "
            f"{'SIM' if e['meta_simbolo'] else 'não'}"
        )
    print()
    resumo = relatorio["resumo"]
    print("Resumo:")
    for simbolo, est in resumo["estabilidade_por_simbolo"].items():
        print(f"  {simbolo}: estabilidade {est:.3f}")
    print(f"  estabilidade média: {resumo['estabilidade_media']:.3f}")
    print(f"  episódios com tensão: {resumo['episodios_com_tensao']}/12")
    print(
        "  Meta-Símbolo formado no episódio "
        f"{resumo['episodio_meta']}" if resumo["meta_simbolo_formado"] else "  Meta-Símbolo não se formou"
    )
    print(f"  Gini final: {resumo['gini_final']:.3f}, Var média final: {resumo['var_media_final']:.3f}")


if __name__ == "__main__":
    main()
