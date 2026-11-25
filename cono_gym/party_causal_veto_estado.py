"""Isekai Zero — A Party Causal: variante VETO POR ESTADO.

Reutiliza a variante DECAIMENTO (party_causal_decaimento.py) sem a
alterar — a mesma semente, os mesmos 40 ticks, o mesmo decaimento,
o mesmo portão de veto por tentativa da TIRANIA — e acrescenta UMA
coisa: a vigilância do ESTADO do cluster.

## O problema que esta variante ataca

A variante DECAIMENTO provou um negativo preciso: a 0,85 o cluster
chega a ISC 0,90 no tick 38 sem que nenhum agente tente formar
Símbolo depois disso — o Símbolo existe mas não é reclamado, e o
portão de veto só vigia tentativas. A hipótese desta variante é
que, se o portão vigiar o ESTADO (e não só as tentativas), o veto
dispara a 0,85 e fica calado na base.

## O resultado (resumo — ver os testes para os números)

A hipótese NÃO se confirma. O veto por estado nunca dispara, em
nenhum nível da sonda — nem a 0,85, nem a nenhum tick, em nenhum
fator. E não é um artefacto da granularidade dos checkpoints: a
trajetória por tick mostra que as duas condições NUNCA coincidem.
O JSD ordenado mínimo da corrida a 0,85 (0,1901) cai no tick 11,
com ISC 0,60; quando o ISC chega a 0,90 (ticks 38–40), o JSD
ordenado já recuperou para 0,32 / 0,30 / 0,2851. A concentração
(JSD baixo) vive na fase esparsa e a integração (ISC alto) vive
na fase densa — e nesta dinâmica as duas são anti-correlacionadas:
mais arestas implicam mais depósitos, que espalham os pesos e
fazem o JSD ordenado subir. O "estado tirânico" que a variante
de decaimento diagnosticou era o mínimo da corrida, não o estado
no momento em que o Símbolo existe.

## A vigilância de estado

A cada checkpoint de 10 ticks (e no fim, tick 40 — que já é
checkpoint, por isso não há dupla contagem), avalia-se o cluster
atual: se ISC_Local >= 0,85 E JSD_pesos_ordenado < JSD_ESTADO
(0,28, limiar DO CENÁRIO — o mesmo do sucesso do Dan, não
canónico), regista-se um evento de veto por estado e o cluster
fica marcado como tirânico: um Símbolo reclamado nesse estado
não conta como Símbolo válido. A vigilância é um observador,
não um portão — não bloqueia formações; o portão por tentativa
(0,18) continua como está, e os dois são reportados lado a lado.

Guarda herdada da TIRANIA: o JSD ordenado só é um sinal com
>= 5 arestas (com menos, o protótipo é degenerado). O VarPn não
entra na condição do veto por estado — nunca ameaça nesta sonda
(máximo 0,13) — mas fica registado no evento.
"""

from . import party_causal as pc
from .auditoria import gini
from .party_causal_tyranny import (
    _checkpoint_tyranny,
    _tentar_simbolo_veto,
    jsd_pesos_ordenado,
)
from .party_causal_decaimento import (
    FATOR_DECAIMENTO,
    PISO_DECAIMENTO,
    _aplicar_decaimento,
    _arestas_no_piso,
)

# Limiar DO CENÁRIO para o veto por estado (não canónico): o 0,28 do
# sucesso do Dan (pc.JSD_SUCESSO). Um cluster que passa a regra de
# Símbolo com JSD ordenado abaixo disto é tirânico.
JSD_ESTADO = 0.28  # = pc.JSD_SUCESSO
# Mínimo de arestas para o JSD ordenado ser um sinal (TIRANIA).
MIN_ARESTAS_JSD = 5


def _vigiar_estado(est, jsd_ord):
    """Vigilância de ESTADO no checkpoint: se o cluster passa a
    regra canónica de Símbolo (ISC_Local >= 0,85) mas o JSD
    ordenado está abaixo do limiar do cenário (0,28), regista um
    evento de veto por estado e devolve True. Não bloqueia nada —
    é um observador. Com < 5 arestas, ou sem JSD, não há sinal:
    devolve False sem registar."""
    sub = est.subgrafo_party()
    if sub.n_arestas() < MIN_ARESTAS_JSD or jsd_ord is None:
        return False
    rel = pc.avaliar_cluster(sub, "SIMBOLO_PARTY_001")
    if rel["isc_local"] >= 0.85 and jsd_ord < JSD_ESTADO:
        est.vetos_estado.append(
            {
                "tick": est.tick,
                "isc_local": round(rel["isc_local"], 4),
                "var_ponderada_normalizada": round(
                    rel["var_ponderada_normalizada"], 4
                ),
                "jsd_ordenado": round(jsd_ord, 4),
                "gini": round(gini(sub.pesos()), 4),
                "n_arestas": sub.n_arestas(),
                "simbolo_reclamado": est.simbolo_tick is not None,
                "simbolo_no_checkpoint": rel["simbolo"],
            }
        )
        est.eventos.append(
            (est.tick, "VETO POR ESTADO (cluster tirânico)", round(jsd_ord, 4))
        )
        return True
    return False


def _simbolo_valido(simbolo_tick, vetos_estado):
    """Um Símbolo reclamado só conta como válido se nunca foi
    apanhado tirânico pela vigilância de estado enquanto existia.
    Sem Símbolo reclamado, não há Símbolo válido."""
    if simbolo_tick is None:
        return False
    return not any(v["simbolo_reclamado"] for v in vetos_estado)


def rodar_party_causal_veto_estado(
    semente=pc.SEMENTE, n_ticks=pc.N_TICKS, fator=FATOR_DECAIMENTO, piso=PISO_DECAIMENTO
):
    """Corre a variante (40 ticks, checkpoint a cada 10, vigilância
    de estado em cada checkpoint e no fim) e devolve o relatório
    completo. A base não é alterada: o remendo de _tentar_simbolo
    é reposto no finally, e a corrida base continua a dar os
    mesmos números depois disto. Com fator = 1,00 a variante é a
    base com os dois portões (o decaimento não faz nada) — é o
    controlo da sonda. A trajetória por tick fica no relatório:
    é ela que prova que o negativo não é um artefacto da
    granularidade dos checkpoints."""
    est = pc._Estado(semente)
    est.vetos = []
    est.vetos_estado = []
    checkpoints = []
    trajetoria = []
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
            sub = est.subgrafo_party()
            isc_tick = (
                sub.n_arestas() / sub.max_arestas() if sub.max_arestas() else 0.0
            )
            # A mesma guarda da TIRANIA: com < 5 arestas o protótipo
            # é degenerado e o JSD não é um sinal — a trajetória
            # regista None nesses ticks, em vez de um mínimo falso.
            jsd_ord = (
                jsd_pesos_ordenado(sub)
                if sub.n_arestas() >= MIN_ARESTAS_JSD
                else None
            )
            trajetoria.append(
                {
                    "tick": tick,
                    "n_arestas": sub.n_arestas(),
                    "isc_local": round(isc_tick, 4),
                    "jsd_ordenado": round(jsd_ord, 4) if jsd_ord is not None else None,
                }
            )
            if jsd_ord is not None and sub.n_arestas() >= MIN_ARESTAS_JSD:
                if jsd_ord_min is None or jsd_ord < jsd_ord_min:
                    jsd_ord_min, jsd_ord_min_tick = jsd_ord, tick
                for limiar in (pc.JSD_SUCESSO, pc.JSD_PARCIAL, pc.JSD_VETO):
                    if jsd_ord < limiar and limiar not in cruzamentos:
                        cruzamentos[limiar] = tick
            if tick % pc.CHECKPOINT == 0:
                # A vigilância corre antes do checkpoint, para o
                # checkpoint contar o veto por estado deste tick.
                _vigiar_estado(est, jsd_ord)
                c = _checkpoint_tyranny(est, jsd_ord)
                c["arestas_no_piso"] = _arestas_no_piso(est, piso)
                c["vetos_estado"] = len(est.vetos_estado)
                checkpoints.append(c)
                if est.simbolo_tick is not None:
                    pc._tentar_meta_simbolo(est, f"checkpoint tick {tick}")
        # Avaliação final: o tick 40 já é checkpoint (40 % 10 == 0).
        # Só se vigia o estado final fora dos checkpoints quando o
        # último tick não é um checkpoint — sem dupla contagem.
        if n_ticks % pc.CHECKPOINT != 0:
            sub = est.subgrafo_party()
            _vigiar_estado(est, jsd_pesos_ordenado(sub))
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
    # Critérios da variante (a vigilância de estado).
    criterios["veto_estado_disparou"] = len(est.vetos_estado) > 0
    criterios["cluster_tiranico"] = len(est.vetos_estado) > 0
    criterios["simbolo_valido"] = _simbolo_valido(est.simbolo_tick, est.vetos_estado)
    # Ticks em que o estado seria tirânico pela regra (ISC >= 0,85
    # E JSDord < 0,28), na trajetória por tick: se esta lista está
    # vazia, o negativo não depende da granularidade dos checkpoints.
    ticks_tiranicos = [
        t["tick"]
        for t in trajetoria
        if t["isc_local"] >= 0.85
        and t["jsd_ordenado"] is not None
        and t["jsd_ordenado"] < JSD_ESTADO
    ]
    criterios["simbolo_morto_por_varpn"] = bool(
        simbolo is False
        and varpn_final is not None
        and varpn_final > 0.36
        and checkpoints
        and checkpoints[-1]["isc_local"] >= 0.85
    )
    refs, _, _ = pc.calibrar_lambda2()
    return {
        "variante": "veto por estado (vigilância do cluster, não só das tentativas)",
        "semente": semente,
        "ticks": n_ticks,
        "alavanca": {
            "nome": "vigilância de estado + decaimento importado",
            "fator_decaimento": fator,
            "piso_decaimento": piso,
            "lira": "força total (sem escala) — como no decaimento",
            "jsd_estado": JSD_ESTADO,
            "min_arestas_jsd": MIN_ARESTAS_JSD,
            "total_decaimentos": total_decaimentos,
        },
        "checkpoints": checkpoints,
        "trajetoria": trajetoria,
        "ticks_tiranicos": ticks_tiranicos,
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
            "vetos_estado": list(est.vetos_estado),
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


def sondar_veto_estado(fatores=(1.00, 0.98, 0.95, 0.90, 0.85), semente=pc.SEMENTE):
    """Sonda de dose-resposta: corre a variante em cada fator e
    devolve, por fator, se o Símbolo se formou, os vetos por
    tentativa e por estado, o Gini final, o JSD ordenado mínimo e
    o VarPn final. A pergunta que a sonda responde: o veto por
    estado dispara a 0,85 (e a 0,90, se o estado lá chegar) e fica
    calado a 1,00 / 0,95?"""
    linhas = []
    for fator in fatores:
        rel = rodar_party_causal_veto_estado(semente=semente, fator=fator)
        final = rel["checkpoints"][-1] if rel["checkpoints"] else {}
        linhas.append(
            {
                "fator": fator,
                "simbolo_tick": rel["eventos"]["simbolo_tick"],
                "vetos_tentativa": len(rel["eventos"]["vetos"]),
                "vetos_estado": len(rel["eventos"]["vetos_estado"]),
                "ticks_tiranicos": list(rel["ticks_tiranicos"]),
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
    print("Isekai Zero — A Party Causal: variante VETO POR ESTADO")
    print(f"semente={rel['semente']}  ticks={rel['ticks']}  "
          f"fator={rel['alavanca']['fator_decaimento']}  piso={rel['alavanca']['piso_decaimento']}  "
          f"jsd_estado={rel['alavanca']['jsd_estado']}")
    print("tick | arest | ISC   | VarPn | ISCaux | Gini  | λ₂    | MIP   | JSDp  | JSDord | VetT | VetE | Piso | Símbolo")
    for c in rel["checkpoints"]:
        print(
            f"{c['tick']:>4} | {c['n_arestas']:>5} | {c['isc_local']:.3f} | "
            f"{c['var_ponderada_normalizada']:.3f} | {c['isc_aux']:.3f} | "
            f"{c['gini']:.3f} | {c['lambda2']:.3f} | {c['mip_corte_min']:.3f} | "
            f"{c['jsd_pesos'] if c['jsd_pesos'] is not None else '-':>5} | "
            f"{c['jsd_ordenado'] if c['jsd_ordenado'] is not None else '-':>6} | "
            f"{c['vetos']:>4} | {c['vetos_estado']:>4} | {c['arestas_no_piso']:>4} | {'SIM' if c['simbolo'] else 'não'}"
        )
    ev = rel["eventos"]
    print(f"Símbolo formado no tick: {ev['simbolo_tick']}")
    print(f"Ren seguiu o verdadeiro fraco: {ev['ren_verdadeiro']}x (falso: {ev['ren_falso']}x)")
    print(f"Vetos por tentativa: {len(ev['vetos'])} -> {ev['vetos']}")
    print(f"Vetos por estado: {len(ev['vetos_estado'])} -> {ev['vetos_estado']}")
    print(f"Ticks tirânicos (trajetória por tick): {rel['ticks_tiranicos']}")
    print(f"Depósitos por agente: {ev['depositos_por_agente']}")
    print(f"JSD ordenado: mínimo {rel['jsd_ordenado_min']} (tick {rel['jsd_ordenado_min_tick']}), "
          f"final {rel['jsd_ordenado_final']}; cruzamentos: {rel['cruzamentos']}")
    print(f"Critérios: {rel['criterios']}")
    print()
    print("Sonda de dose-resposta (fator -> Símbolo / vetos tent. / vetos estado / Gini final / JSDord mín / VarPn final):")
    for linha in sondar_veto_estado():
        print(
            f"  {linha['fator']:.2f} -> tick {linha['simbolo_tick']} / "
            f"{linha['vetos_tentativa']} tent. / {linha['vetos_estado']} estado / "
            f"Gini {linha['gini_final']} / JSDord mín {linha['jsd_ordenado_min']} / "
            f"VarPn {linha['varpn_final']} / ticks tirânicos {linha['ticks_tiranicos']}"
        )


if __name__ == "__main__":
    imprimir_relatorio(rodar_party_causal_veto_estado())
