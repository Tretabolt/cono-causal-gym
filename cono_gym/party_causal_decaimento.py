"""Isekai Zero — A Party Causal: variante DECAIMENTO (mudança de mecanismo).

Reutiliza o módulo base (party_causal.py) sem o alterar: a mesma
semente, os mesmos 40 ticks, os mesmos limiares canónicos
(ISC_Local >= 0,85 E VarPn <= 0,36). E reutiliza o portão de veto
da variante TIRANIA (party_causal_tyranny.py) sem o alterar: o
JSD ordenado é o monitor e o veto é o portão. O que muda é UMA
alavanca e UMA só — o decaimento — e a Lira fica com força TOTAL
nesta variante, para o efeito do decaimento ser medido isolado.

## O problema que esta variante ataca

A variante TIRANIA provou um negativo honesto: com a Lira fraca
(0,20), o Símbolo forma-se mais cedo (tick 16, ISC final 1,000)
mas o veto NUNCA dispara — 0 vetos, Gini máximo 0,233, JSD
ordenado nunca abaixo de 0,28 nos checkpoints. A alavanca
satura (0,5 ~= 0,2) e a 0,0 o Símbolo nem se forma. A conclusão
foi: a tirania não morde por PARÂMETRO; precisa de uma mudança
de MECANISMO. Esta variante testa a primeira mudança da lista:
o decaimento (esquecimento) das arestas não reforçadas.

## A alavanca (UMA): decaimento das arestas não tocadas

No fim de cada tick, cada aresta da party NÃO tocada nesse tick
(nenhum depósito nem seguimento) perde peso:

    peso = max(PISO, peso * FATOR)

FATOR_DECAIMENTO = 0,95 e PISO_DECAIMENTO = 0,05 por omissão.
O piso preserva a topologia: nenhuma aresta some, por isso o
ISC_Local (topológico) não é afetado pelo decaimento — só a
distribuição dos pesos muda. É o mesmo princípio do
esquecimento sináptico: o que não é usado enfraquece, o que é
mantido fica.

## Porque é que o decaimento pode fazer a tirania morder

Na base os pesos só sobem (depositar vale max, seguir soma
+0,05) e nunca descem — a distribuição só pode uniformizar-se
pelos depósitos da Lira e do Kael. Com decaimento, as arestas
que ninguém mantém afundam para o piso enquanto as arestas
mantidas (Sora->Ren, sempre reforçada) ficam em 1,0: o Gini
sobe e o JSD ordenado cai. A pergunta da variante é se existe
uma janela onde o veto dispara (JSD ordenado < 0,18) num
Símbolo ainda vivo — ou se o VarPn mata o Símbolo primeiro,
porque a mesma desigualdade que baixa o JSD sobe o VarPn.
É uma corrida entre dois limiares, e a sonda de dose-resposta
mede-a.

## O que NÃO muda

- A Lira está com força total (o _agir_lira da base, sem escala).
- O Sistema, os ritmos de re-injeção e as tabelas de
  probabilidade são os da base.
- Os limiares canónicos não são redefinidos; o JSD_pesos
  ordenado e o portão de veto são os da variante TIRANIA,
  importados, não duplicados.
- O decaimento NÃO atualiza ultimo_deposito: decair não é tocar.
  E só se aplica às arestas da party (o subgrafo avaliado):
  os dois rastros do Sistema ficam como a base os define.
"""

from . import party_causal as pc
from .party_causal_tyranny import (
    _checkpoint_tyranny,
    _tentar_simbolo_veto,
    jsd_pesos_ordenado,
)

# Alavanca principal (UMA): decaimento por tick das arestas não tocadas.
# 1,00 = sem decaimento (controlo: reproduz a base com o portão);
# 0,95 = omissão; valores menores = esquecimento mais rápido.
FATOR_DECAIMENTO = 0.95
# Piso: nenhuma aresta some — a topologia (e o ISC_Local) é preservada.
PISO_DECAIMENTO = 0.05


def _aplicar_decaimento(est, fator=FATOR_DECAIMENTO, piso=PISO_DECAIMENTO):
    """No fim de cada tick: cada aresta da party NÃO tocada neste
    tick decai para max(piso, peso * fator). Devolve o nº de arestas
    que decaíram. Arestas tocadas (ultimo_deposito == tick) não
    decaem; o decaimento não atualiza ultimo_deposito."""
    sub = est.subgrafo_party()
    n = 0
    for r in sub.todos_rastros():
        chave = frozenset((r.origem, r.destino))
        if est.ultimo_deposito.get(chave, 0) < est.tick:
            novo = max(piso, r.peso * fator)
            if novo < r.peso:
                est.grafo.depositar_rastro(r.origem, r.destino, r.tipo_relacao, novo)
                n += 1
    return n


def _arestas_no_piso(est, piso=PISO_DECAIMENTO):
    """Nº de arestas da party com peso no piso (ou abaixo dele)."""
    return sum(1 for r in est.subgrafo_party().todos_rastros() if r.peso <= piso + 1e-9)


def rodar_party_causal_decaimento(
    semente=pc.SEMENTE, n_ticks=pc.N_TICKS, fator=FATOR_DECAIMENTO, piso=PISO_DECAIMENTO
):
    """Corre a variante (40 ticks, checkpoint a cada 10) e devolve
    o relatório completo. A base não é alterada: o remendo de
    _tentar_simbolo é reposto no finally, e a corrida base continua
    a dar os mesmos números depois disto. Com fator = 1,00 a
    variante é a base com o portão de veto (o decaimento não faz
    nada) — é o controlo da sonda."""
    est = pc._Estado(semente)
    est.vetos = []
    checkpoints = []
    jsd_ord_min = None
    jsd_ord_min_tick = None
    cruzamentos = {}
    total_decaimentos = 0
    original = pc._tentar_simbolo
    pc._tentar_simbolo = _tentar_simbolo_veto
    try:
        for tick in range(1, n_ticks + 1):
            est.tick = tick
            pc._agir_sistema(est)
            for nome in pc.NOMES[:5]:
                pc._AGIR[nome](est)
            total_decaimentos += _aplicar_decaimento(est, fator, piso)
            jsd_ord = jsd_pesos_ordenado(est.subgrafo_party())
            if jsd_ord is not None and est.subgrafo_party().n_arestas() >= 5:
                if jsd_ord_min is None or jsd_ord < jsd_ord_min:
                    jsd_ord_min, jsd_ord_min_tick = jsd_ord, tick
                for limiar in (pc.JSD_SUCESSO, pc.JSD_PARCIAL, pc.JSD_VETO):
                    if jsd_ord < limiar and limiar not in cruzamentos:
                        cruzamentos[limiar] = tick
            if tick % pc.CHECKPOINT == 0:
                c = _checkpoint_tyranny(est, jsd_ord)
                c["arestas_no_piso"] = _arestas_no_piso(est, piso)
                checkpoints.append(c)
                if est.simbolo_tick is not None:
                    pc._tentar_meta_simbolo(est, f"checkpoint tick {tick}")
    finally:
        pc._tentar_simbolo = original
    jsd_finais = [c["jsd_pesos"] for c in checkpoints if c["jsd_pesos"] is not None]
    jsd_min = min(jsd_finais) if jsd_finais else None
    jsd_final = jsd_finais[-1] if jsd_finais else None
    jsd_ord_finais = [c["jsd_ordenado"] for c in checkpoints if c["jsd_ordenado"] is not None]
    jsd_ord_final = jsd_ord_finais[-1] if jsd_ord_finais else None
    simbolo = est.simbolo_tick is not None
    criterios = {
        "simbolo_formado": simbolo,
        "simbolo_sem_tirania": bool(simbolo and jsd_min is not None and jsd_min >= pc.JSD_PARCIAL),
        "jsd_nunca_abaixo_0.22": bool(jsd_min is not None and jsd_min >= pc.JSD_PARCIAL),
        "ren_verdadeiro_ge_2": est.ren_verdadeiro >= 2,
        "jsd_final_ge_0.28": bool(jsd_final is not None and jsd_final >= pc.JSD_SUCESSO),
    }
    criterios["sucesso_parcial"] = criterios["simbolo_sem_tirania"]
    criterios["sucesso_completo"] = bool(
        simbolo and criterios["ren_verdadeiro_ge_2"] and criterios["jsd_final_ge_0.28"]
    )
    gini_final = checkpoints[-1]["gini"] if checkpoints else None
    varpn_final = checkpoints[-1]["var_ponderada_normalizada"] if checkpoints else None
    criterios["gini_final_ge_0.30"] = bool(gini_final is not None and gini_final >= 0.30)
    criterios["jsd_ordenado_min_lt_0.28"] = bool(jsd_ord_min is not None and jsd_ord_min < pc.JSD_SUCESSO)
    criterios["jsd_ordenado_min_lt_0.22"] = bool(jsd_ord_min is not None and jsd_ord_min < pc.JSD_PARCIAL)
    criterios["veto_disparou"] = len(est.vetos) > 0
    criterios["veto_bloqueou_formacao"] = any(v["bloqueou_formacao"] for v in est.vetos)
    # Critérios da variante (o mecanismo): o decaimento mordeu?
    criterios["simbolo_morto_por_varpn"] = bool(
        simbolo is False
        and varpn_final is not None
        and varpn_final > 0.36
        and checkpoints
        and checkpoints[-1]["isc_local"] >= 0.85
    )
    refs, _, _ = pc.calibrar_lambda2()
    return {
        "variante": "decaimento (esquecimento das arestas não reforçadas)",
        "semente": semente,
        "ticks": n_ticks,
        "alavanca": {
            "nome": "decaimento por tick das arestas não tocadas",
            "fator_decaimento": fator,
            "piso_decaimento": piso,
            "lira": "força total (sem escala) — o decaimento é a única alavanca",
            "total_decaimentos": total_decaimentos,
        },
        "checkpoints": checkpoints,
        "eventos": {
            "simbolo_tick": est.simbolo_tick,
            "simbolo_serial": est.simbolo_serial,
            "ren_verdadeiro": est.ren_verdadeiro,
            "ren_falso": est.ren_falso,
            "veyra_verdadeiro": est.veyra_verdadeiro,
            "tentativas_simbolo": est.tentativas_simbolo,
            "tentativas_meta_simbolo": est.tentativas_meta,
            "depositos_por_agente": dict(est.depositos),
            "seguimentos_por_agente": dict(est.seguimentos),
            "vetos": list(est.vetos),
        },
        "criterios": criterios,
        "jsd_min": round(jsd_min, 4) if jsd_min is not None else None,
        "jsd_final": round(jsd_final, 4) if jsd_final is not None else None,
        "jsd_ordenado_min": round(jsd_ord_min, 4) if jsd_ord_min is not None else None,
        "jsd_ordenado_min_tick": jsd_ord_min_tick,
        "jsd_ordenado_final": round(jsd_ord_final, 4) if jsd_ord_final is not None else None,
        "cruzamentos": {str(k): v for k, v in sorted(cruzamentos.items())},
        "referencias": {
            "lambda2": refs,
            "lambda2_min": pc.LAMBDA2_MIN,
            "jsd_uniforme_10": round(
                pc.jsd_bits([0.1] * 10, pc.prototipo_tirania(10)), 4
            ),
        },
    }


def sondar_decaimento(fatores=(1.00, 0.98, 0.95, 0.90, 0.85), semente=pc.SEMENTE):
    """Sonda de dose-resposta: corre a variante em cada fator e
    devolve, por fator, se o Símbolo se formou, se o veto disparou,
    o Gini final, o JSD ordenado mínimo e o VarPn final. É a sonda
    que decide se existe uma janela onde o veto dispara num Símbolo
    vivo — ou se o VarPn mata o Símbolo primeiro."""
    linhas = []
    for fator in fatores:
        rel = rodar_party_causal_decaimento(semente=semente, fator=fator)
        final = rel["checkpoints"][-1] if rel["checkpoints"] else {}
        linhas.append(
            {
                "fator": fator,
                "simbolo_tick": rel["eventos"]["simbolo_tick"],
                "vetos": len(rel["eventos"]["vetos"]),
                "gini_final": final.get("gini"),
                "jsd_ordenado_min": rel["jsd_ordenado_min"],
                "jsd_ordenado_final": rel["jsd_ordenado_final"],
                "varpn_final": final.get("var_ponderada_normalizada"),
                "isc_final": final.get("isc_local"),
                "arestas_no_piso": final.get("arestas_no_piso"),
            }
        )
    return linhas


def imprimir_relatorio(rel):
    """Tabela da variante + sonda de dose-resposta."""
    print("Isekai Zero — A Party Causal: variante DECAIMENTO")
    print(f"semente={rel['semente']}  ticks={rel['ticks']}  "
          f"fator={rel['alavanca']['fator_decaimento']}  piso={rel['alavanca']['piso_decaimento']}")
    print("tick | arest | ISC   | VarPn | ISCaux | Gini  | λ₂    | MIP   | JSDp  | JSDord | Vetos | Piso | Símbolo")
    for c in rel["checkpoints"]:
        print(
            f"{c['tick']:>4} | {c['n_arestas']:>5} | {c['isc_local']:.3f} | "
            f"{c['var_ponderada_normalizada']:.3f} | {c['isc_aux']:.3f} | "
            f"{c['gini']:.3f} | {c['lambda2']:.3f} | {c['mip_corte_min']:.3f} | "
            f"{c['jsd_pesos'] if c['jsd_pesos'] is not None else '-':>5} | "
            f"{c['jsd_ordenado'] if c['jsd_ordenado'] is not None else '-':>6} | "
            f"{c['vetos']:>5} | {c['arestas_no_piso']:>4} | {'SIM' if c['simbolo'] else 'não'}"
        )
    ev = rel["eventos"]
    print(f"Símbolo formado no tick: {ev['simbolo_tick']}")
    print(f"Ren seguiu o verdadeiro fraco: {ev['ren_verdadeiro']}x (falso: {ev['ren_falso']}x)")
    print(f"Vetos: {len(ev['vetos'])} -> {ev['vetos']}")
    print(f"Depósitos por agente: {ev['depositos_por_agente']}")
    print(f"Decaimentos aplicados: {rel['alavanca']['total_decaimentos']}")
    print(f"JSD ordenado: mínimo {rel['jsd_ordenado_min']} (tick {rel['jsd_ordenado_min_tick']}), "
          f"final {rel['jsd_ordenado_final']}; cruzamentos: {rel['cruzamentos']}")
    print(f"Critérios: {rel['criterios']}")
    print()
    print("Sonda de dose-resposta (fator -> Símbolo / vetos / Gini final / JSDord mín / VarPn final):")
    for linha in sondar_decaimento():
        print(
            f"  {linha['fator']:.2f} -> tick {linha['simbolo_tick']} / "
            f"{linha['vetos']} vetos / Gini {linha['gini_final']} / "
            f"JSDord mín {linha['jsd_ordenado_min']} / VarPn {linha['varpn_final']}"
        )


if __name__ == "__main__":
    imprimir_relatorio(rodar_party_causal_decaimento())
