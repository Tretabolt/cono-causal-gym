"""Isekai Zero — A Party Causal: análise ALOCAÇÃO DE DEPÓSITOS.

Assente na POMDP (party_causal_pomdp.py), sem a alterar — a mesma
semente, os mesmos 40 ticks, os mesmos agentes locais, o mesmo RNG.
Não empilha decaimento, rich-club nem segundo critério: a
instrumentação é a única variável. A pergunta que esta análise
ataca é a que a visão local + rich-club deixou em aberto: PORQUÊ
a visão parcial integra melhor? O que muda na alocação dos
depósitos a raio 2?

## O que se instrumenta

Cada chamada a est.depositar() (a única via pela qual um membro da
party cria ou reforça um rastro — o Sistema re-injeta por
grafo.depositar_rastro directo e NÃO passa por aqui, por isso os
seus dois rastros iniciais e as suas re-injecções não contam como
depósitos de alocação) é registada com: tick, agente, par
(ordenado), tipo, peso ofertado, peso antes, peso depois, e se foi
recusada pela guarda da POMDP (par não incidente ao agente).

A instrumentação não consome RNG nem muda nenhuma decisão: lê
dois pesos e anexa um dicionário a uma lista. A raio ∞ a corrida
reproduz a base EXACTAMENTE, como a POMDP — e os testes fixam-no
(checkpoints, eventos, depósitos, seguimentos, Símbolo).

## Definições do cenário (não canónicas)

- Depósito CRIADOR: o par não tinha aresta antes (peso_antes é
  None). É o depósito que aumenta o número de arestas — e, por
  isso, o ISC. Há no máximo um criador por par (o primeiro).
- Depósito REFORÇO: o par já tinha aresta e o peso sobe
  (peso_depois > peso_antes).
- Depósito REDUNDANTE: o depósito é aceite mas o peso NÃO sobe
  (peso_depois == peso_antes). Acontece quando o peso ofertado é
  menor ou igual ao peso actual, ou quando a aresta já está no
  teto (1,0). Depositar vale max(peso antigo, peso novo) — um
  depósito redundante é trabalho que não muda o grafo.
- Depósito RECUSADO: a guarda da POMDP recusa-o (o par não é
  incidente ao agente). Não tem efeitos e não conta nos
  depósitos do agente. Na POMDP todos os depósitos da party já
  são incidentes por construção — os recusados deviam ser zero,
  e os testes fixam-no.
- GANHO de um depósito: peso_depois - peso_antes (0,0 se
  redundante; peso_depois se criador).
- Concentração: quota do agente (ou da aresta) com mais depósitos
  sobre o total de depósitos aceites.

## As três hipóteses, testadas com números (não assumidas)

(a) A raio 2 há menos depósitos redundantes em arestas já fortes,
    porque os agentes não as veem — o que não se vê não se
    reforça sem necessidade.
(b) A visibilidade a raio 2 é o que permite os depósitos que
    faltam a raio 1 (Kael–Ren, Kael–Sora): os dois pares que
    exigem um depósito do Ren ou do Kael.
(c) O timing dos primeiros depósitos nas últimas arestas explica
    o Símbolo mais cedo: a 9.ª e a 10.ª arestas nascem mais cedo
    a raio 2 do que no controlo.

Se nenhuma se confirmar, o mecanismo medido é a resposta — o
negativo também é resultado.
"""

import math

from . import party_causal as pc
from .party_causal_pomdp import (
    RAIO_INFINITO,
    RAIO_LOCAL,
    RAIO_VIZINHOS,
    RAIOS_SONDA,
    _AGIR_POMDP,
    _EstadoPOMDP,
    _trajetoria_tick,
    rodar_party_causal_pomdp,
    sondar_pomdp,
)
from .party_causal_tyranny import _checkpoint_tyranny, jsd_pesos_ordenado
from .party_causal_veto_estado import (
    JSD_ESTADO,
    MIN_ARESTAS_JSD,
    _simbolo_valido,
    _vigiar_estado,
)

# Pares da party (10 possíveis) e pares com o Sistema, como nomes.
PARES_PARTY = [
    tuple(sorted(p))
    for p in (
        ("Ren", "Lira"), ("Ren", "Kael"), ("Ren", "Sora"), ("Ren", "Veyra"),
        ("Lira", "Kael"), ("Lira", "Sora"), ("Lira", "Veyra"),
        ("Kael", "Sora"), ("Kael", "Veyra"), ("Sora", "Veyra"),
    )
]
# Os dois pares que faltam a raio 1 — só o Ren ou o Kael os podem
# criar, e nenhum dos dois deposita uma vez a raio 1.
PARES_DO_KAEL = [("Kael", "Ren"), ("Kael", "Sora")]


class _EstadoAlocacao(_EstadoPOMDP):
    """O estado da POMDP, com o registo de cada depósito.

    A única diferença é o registo: depositar() lê o peso antes,
    chama a versão da POMDP (com a guarda de incidente) e lê o
    peso depois. Não consome RNG, não muda nenhuma ramificação."""

    def __init__(self, semente=pc.SEMENTE, raio=RAIO_LOCAL):
        super().__init__(semente, raio)
        self.eventos_deposito = []

    def depositar(self, agente, a, b, tipo, peso):
        """Regista a tentativa e o efeito, e delega na POMDP."""
        antes = self.peso(a, b)
        resultado = super().depositar(agente, a, b, tipo, peso)
        depois = self.peso(a, b)
        recusado = resultado is None
        self.eventos_deposito.append(
            {
                "tick": self.tick,
                "agente": agente,
                "par": tuple(sorted((a, b))),
                "tipo": tipo,
                "peso_ofertado": round(peso, 4),
                "peso_antes": antes,
                "peso_depois": depois,
                "nova_aresta": antes is None and not recusado,
                "redundante": (not recusado) and antes is not None and depois == antes,
                "recusado": recusado,
            }
        )
        return resultado


# ------------------------------------------------------------------ análise

def classificar(evento):
    """Classe de um evento de depósito: criador / reforço /
    redundante / recusado (definições do cenário, ver o cabeçalho)."""
    if evento["recusado"]:
        return "recusado"
    if evento["nova_aresta"]:
        return "criador"
    if evento["redundante"]:
        return "redundante"
    return "reforco"


def ganho(evento):
    """Quanto peso o depósito acrescentou à aresta (0,0 se
    redundante ou recusado)."""
    if evento["recusado"]:
        return 0.0
    antes = evento["peso_antes"] if evento["peso_antes"] is not None else 0.0
    return round(evento["peso_depois"] - antes, 4)


def alocacao_por_agente(eventos):
    """Por agente: totais por classe, ganho total e quota."""
    totais = {n: 0 for n in pc.NOMES[:5]}
    por_agente = {}
    for nome in pc.NOMES[:5]:
        evs = [e for e in eventos if e["agente"] == nome]
        classes = {c: 0 for c in ("criador", "reforco", "redundante", "recusado")}
        for e in evs:
            classes[classificar(e)] += 1
        por_agente[nome] = {
            "total": len(evs),
            "criadores": classes["criador"],
            "reforcos": classes["reforco"],
            "redundantes": classes["redundante"],
            "recusados": classes["recusado"],
            "ganho_total": round(sum(ganho(e) for e in evs), 4),
        }
        totais[nome] = len(evs)
    aceites = sum(totais.values())
    quota_max = max(totais.values()) / aceites if aceites else 0.0
    return {"por_agente": por_agente, "quota_max_agente": round(quota_max, 4)}


def alocacao_por_aresta(eventos, pesos_finais=None):
    """Por par: totais por classe, primeiro e último depósito,
    quem criou a aresta, ganho total e peso final (do grafo, se
    dado — os seguimentos também mexem nos pesos depois do
    último depósito)."""
    por_aresta = {}
    for par in PARES_PARTY:
        evs = [e for e in eventos if e["par"] == par]
        if not evs:
            por_aresta[par] = {
                "total": 0,
                "criadores": 0,
                "reforcos": 0,
                "redundantes": 0,
                "primeiro_tick": None,
                "primeiro_agente": None,
                "ultimo_tick": None,
                "ganho_total": 0.0,
                "peso_final": None,
            }
            continue
        classes = {c: 0 for c in ("criador", "reforco", "redundante", "recusado")}
        for e in evs:
            classes[classificar(e)] += 1
        primeiro = evs[0]
        por_aresta[par] = {
            "total": len(evs),
            "criadores": classes["criador"],
            "reforcos": classes["reforco"],
            "redundantes": classes["redundante"],
            "primeiro_tick": primeiro["tick"],
            "primeiro_agente": primeiro["agente"],
            "ultimo_tick": evs[-1]["tick"],
            "ganho_total": round(sum(ganho(e) for e in evs), 4),
            "peso_final": (
                pesos_finais.get(par) if pesos_finais is not None else evs[-1]["peso_depois"]
            ),
        }
    return por_aresta


def primeiro_deposito_por_par(eventos):
    """Tick do primeiro depósito em cada par da party (None se o
    par nunca recebeu um depósito)."""
    return {
        par: (
            next((e["tick"] for e in eventos if e["par"] == par), None)
        )
        for par in PARES_PARTY
    }


def resumo_alocacao(eventos):
    """Totais por classe, concentração por agente e por aresta."""
    classes = {c: 0 for c in ("criador", "reforco", "redundante", "recusado")}
    for e in eventos:
        classes[classificar(e)] += 1
    aceites = sum(
        classes[c] for c in ("criador", "reforco", "redundante")
    )
    por_ag = alocacao_por_agente(eventos)["por_agente"]
    totais_ag = {n: v["total"] for n, v in por_ag.items()}
    por_ar = alocacao_por_aresta(eventos)
    totais_ar = {p: v["total"] for p, v in por_ar.items() if v["total"] > 0}
    return {
        "total_eventos": len(eventos),
        "total_aceites": aceites,
        "criadores": classes["criador"],
        "reforcos": classes["reforco"],
        "redundantes": classes["redundante"],
        "recusados": classes["recusado"],
        "quota_redundante": round(classes["redundante"] / aceites, 4) if aceites else 0.0,
        "ganho_total": round(sum(ganho(e) for e in eventos), 4),
        "quota_max_agente": round(max(totais_ag.values()) / aceites, 4) if aceites else 0.0,
        "agente_top": max(totais_ag, key=lambda n: totais_ag[n]) if aceites else None,
        "quota_max_aresta": round(max(totais_ar.values()) / aceites, 4) if aceites else 0.0,
        "aresta_top": max(totais_ar, key=lambda p: totais_ar[p]) if aceites else None,
        "n_pares_tocados": len(totais_ar),
    }


def nascimento_das_arestas(eventos):
    """Em que tick nasce cada aresta da party (o tick do depósito
    criador) e em que tick o cluster atinge k arestas — a
    cronologia que a hipótese (c) precisa."""
    primeiros = primeiro_deposito_por_par(eventos)
    nascidos = sorted(
        (t, p) for p, t in primeiros.items() if t is not None
    )
    atinge = {}
    for k in range(1, 11):
        atinge[k] = nascidos[k - 1][0] if len(nascidos) >= k else None
    return {
        "nascimento_por_par": primeiros,
        "ordem_nascimento": [(p, t) for t, p in nascidos],
        "tick_atinge_k_arestas": atinge,
    }


def analisar_alocacao(rel):
    """A secção de alocação de um relatório de corrida: por
    agente, por aresta, nascimentos e resumo."""
    eventos = rel["eventos_deposito"]
    pesos_finais = rel.get("pesos_finais", {})
    return {
        "por_agente": alocacao_por_agente(eventos),
        "por_aresta": alocacao_por_aresta(eventos, pesos_finais),
        "primeiro_deposito_por_par": primeiro_deposito_por_par(eventos),
        "nascimento_das_arestas": nascimento_das_arestas(eventos),
        "resumo": resumo_alocacao(eventos),
    }


# ------------------------------------------------------------------ corrida

def rodar_party_causal_alocacao(
    semente=pc.SEMENTE, n_ticks=pc.N_TICKS, raio=RAIO_LOCAL
):
    """Corre a POMDP com o estado instrumentado e devolve o
    relatório da POMDP mais a secção de alocação. O ciclo de
    ticks é o da POMDP, verbatim — a instrumentação não muda
    nenhuma decisão, por isso a raio ∞ a corrida reproduz a base
    exactamente, como a POMDP."""
    est = _EstadoAlocacao(semente, raio)
    est.vetos = []
    est.vetos_estado = []
    checkpoints = []
    trajetoria = []
    jsd_ord_min = None
    jsd_ord_min_tick = None
    cruzamentos = {}
    for tick in range(1, n_ticks + 1):
        est.tick = tick
        pc._agir_sistema(est)
        for nome in pc.NOMES[:5]:
            _AGIR_POMDP[nome](est)
        t = _trajetoria_tick(est)
        trajetoria.append(t)
        jsd_ord = t["jsd_ordenado"]
        if jsd_ord is not None:
            if jsd_ord_min is None or jsd_ord < jsd_ord_min:
                jsd_ord_min, jsd_ord_min_tick = jsd_ord, tick
            for limiar in (pc.JSD_SUCESSO, pc.JSD_PARCIAL, pc.JSD_VETO):
                if jsd_ord < limiar and limiar not in cruzamentos:
                    cruzamentos[limiar] = tick
        if tick % pc.CHECKPOINT == 0:
            _vigiar_estado(est, jsd_ord)
            c = _checkpoint_tyranny(est, jsd_ord)
            c["vetos_estado"] = len(est.vetos_estado)
            c["isc_visivel_medio"] = t["isc_visivel_medio"]
            c["isc_visivel_max"] = t["isc_visivel_max"]
            checkpoints.append(c)
            if est.simbolo_tick is not None:
                pc._tentar_meta_simbolo(est, f"checkpoint tick {tick}")
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
    criterios["veto_estado_disparou"] = len(est.vetos_estado) > 0
    criterios["cluster_tiranico"] = len(est.vetos_estado) > 0
    criterios["simbolo_valido"] = _simbolo_valido(est.simbolo_tick, est.vetos_estado)
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
    visao_final = {
        nome: {
            "arestas_party_visiveis": len(est.arestas_party_visiveis(nome)),
            "isc_visivel": round(est.isc_visivel(nome), 4),
        }
        for nome in pc.NOMES[:5]
    }
    refs, _, _ = pc.calibrar_lambda2()
    pesos_finais = {
        par: est.peso(*par) for par in PARES_PARTY
    }
    rel = {
        "variante": "alocação de depósitos (POMDP instrumentada) — raio 1, 2 ou ∞",
        "semente": semente,
        "ticks": n_ticks,
        "alavanca": {
            "nome": "raio de visão",
            "raio": raio,
            "jsd_estado": JSD_ESTADO,
            "min_arestas_jsd": MIN_ARESTAS_JSD,
        },
        "checkpoints": checkpoints,
        "trajetoria": trajetoria,
        "ticks_tiranicos": ticks_tiranicos,
        "visao_final": visao_final,
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
        "eventos_deposito": list(est.eventos_deposito),
        "pesos_finais": pesos_finais,
    }
    rel["alocacao"] = analisar_alocacao(rel)
    return rel


# ------------------------------------------------------------------ comparação

def sondar_alocacao(raios=RAIOS_SONDA, semente=pc.SEMENTE):
    """Sonda de alocação: corre a variante instrumentada em cada
    raio e devolve, por raio, o Símbolo, os depósitos por agente
    e por classe, a concentração, o nascimento das arestas e o
    veredicto das três hipóteses contra o controlo."""
    linhas = []
    for raio in raios:
        rel = rodar_party_causal_alocacao(semente=semente, raio=raio)
        al = rel["alocacao"]
        linhas.append(
            {
                "raio": raio,
                "simbolo_tick": rel["eventos"]["simbolo_tick"],
                "tentativas_simbolo": rel["eventos"]["tentativas_simbolo"],
                "ren_verdadeiro": rel["eventos"]["ren_verdadeiro"],
                "ren_falso": rel["eventos"]["ren_falso"],
                "veyra_verdadeiro": rel["eventos"]["veyra_verdadeiro"],
                "vetos_estado": len(rel["eventos"]["vetos_estado"]),
                "n_arestas_final": rel["checkpoints"][-1]["n_arestas"],
                "isc_final": rel["checkpoints"][-1]["isc_local"],
                "depositos": dict(rel["eventos"]["depositos_por_agente"]),
                "seguimentos": dict(rel["eventos"]["seguimentos_por_agente"]),
                "resumo": dict(al["resumo"]),
                "por_agente": {
                    n: dict(v) for n, v in al["por_agente"]["por_agente"].items()
                },
                "por_aresta": {
                    p: dict(v) for p, v in al["por_aresta"].items()
                },
                "nascimento": dict(al["nascimento_das_arestas"]["tick_atinge_k_arestas"]),
                "primeiro_deposito_por_par": dict(al["primeiro_deposito_por_par"]),
            }
        )
    return linhas


def testar_hipoteses(linhas):
    """Veredicto das três hipóteses, com os números que as
    decidem. `linhas` é a saída de sondar_alocacao(); o controlo
    é a linha de raio ∞."""
    por_raio = {l["raio"]: l for l in linhas}
    ctrl = por_raio[RAIO_INFINITO]
    r2 = por_raio[RAIO_VIZINHOS]
    r1 = por_raio[RAIO_LOCAL]
    # (a) Menos depósitos redundantes a raio 2 do que no controlo?
    red_r2 = r2["resumo"]["redundantes"]
    red_ctrl = ctrl["resumo"]["redundantes"]
    quota_r2 = r2["resumo"]["quota_redundante"]
    quota_ctrl = ctrl["resumo"]["quota_redundante"]
    hip_a = {
        "descricao": "menos depósitos redundantes a raio 2 (o que não se vê não se reforça sem necessidade)",
        "redundantes_raio_2": red_r2,
        "redundantes_controlo": red_ctrl,
        "quota_redundante_raio_2": quota_r2,
        "quota_redundante_controlo": quota_ctrl,
        "diferenca": red_r2 - red_ctrl,
        "confirma": red_r2 < red_ctrl,
    }
    # (b) A visibilidade a raio 2 permite os depósitos que faltam
    # a raio 1 (Kael–Ren, Kael–Sora)?
    nasc_r1 = r1["primeiro_deposito_por_par"]
    nasc_r2 = r2["primeiro_deposito_por_par"]
    nasc_ctrl = ctrl["primeiro_deposito_por_par"]
    hip_b = {
        "descricao": "a visibilidade a raio 2 permite os depósitos que faltam a raio 1 (Kael–Ren, Kael–Sora)",
        "primeiro_deposito": {
            par: {
                "raio_1": nasc_r1[par],
                "raio_2": nasc_r2[par],
                "controlo": nasc_ctrl[par],
            }
            for par in PARES_DO_KAEL
        },
        "confirma": all(
            nasc_r1[par] is None and nasc_r2[par] is not None
            for par in PARES_DO_KAEL
        ),
    }
    # (c) O timing do nascimento das últimas arestas explica o
    # Símbolo mais cedo?
    nasc_tick_r2 = r2["nascimento"]
    nasc_tick_ctrl = ctrl["nascimento"]
    hip_c = {
        "descricao": "o nascimento das últimas arestas é mais cedo a raio 2 e explica o Símbolo mais cedo",
        "tick_9_arestas_raio_2": nasc_tick_r2[9],
        "tick_9_arestas_controlo": nasc_tick_ctrl[9],
        "tick_10_arestas_raio_2": nasc_tick_r2[10],
        "tick_10_arestas_controlo": nasc_tick_ctrl[10],
        "simbolo_raio_2": r2["simbolo_tick"],
        "simbolo_controlo": ctrl["simbolo_tick"],
        "confirma": bool(
            nasc_tick_r2[9] is not None
            and nasc_tick_ctrl[9] is not None
            and nasc_tick_r2[9] < nasc_tick_ctrl[9]
        ),
    }
    # Onde vão os 15 depósitos a menos da raio 2 (79 contra 94)?
    diferenca_por_agente = {
        n: r2["depositos"][n] - ctrl["depositos"][n] for n in pc.NOMES[:5]
    }
    return {
        "hipotese_a_redundancia": hip_a,
        "hipotese_b_pares_do_kael": hip_b,
        "hipotese_c_timing": hip_c,
        "diferenca_depositos_raio_2_vs_controlo": {
            "total": sum(r2["depositos"].values()) - sum(ctrl["depositos"].values()),
            "por_agente": diferenca_por_agente,
            "redundantes": red_r2 - red_ctrl,
            "reforcos": r2["resumo"]["reforcos"] - ctrl["resumo"]["reforcos"],
            "criadores": r2["resumo"]["criadores"] - ctrl["resumo"]["criadores"],
        },
    }


def imprimir_relatorio(rel):
    """Tabelas da análise + sonda de alocação + hipóteses."""
    print("Isekai Zero — A Party Causal: análise ALOCAÇÃO DE DEPÓSITOS")
    print(f"semente={rel['semente']}  ticks={rel['ticks']}  raio={rel['alavanca']['raio']}")
    ev = rel["eventos"]
    print(f"Símbolo formado no tick: {ev['simbolo_tick']}")
    print(f"Depósitos por agente: {ev['depositos_por_agente']}")
    al = rel["alocacao"]
    print("Alocação por agente (total / criadores / reforços / redundantes / recusados / ganho):")
    for nome, v in al["por_agente"]["por_agente"].items():
        print(
            f"  {nome:>6}: {v['total']:>3} / {v['criadores']:>2} / {v['reforcos']:>2} / "
            f"{v['redundantes']:>2} / {v['recusados']:>2} / {v['ganho_total']:.2f}"
        )
    print(f"Resumo: {al['resumo']}")
    print("Alocação por aresta (total / criadores / reforços / redundantes / 1.º tick / 1.º agente / ganho / peso final):")
    for par, v in al["por_aresta"].items():
        print(
            f"  {par[0]}-{par[1]}: {v['total']:>2} / {v['criadores']} / {v['reforcos']:>2} / "
            f"{v['redundantes']:>2} / {v['primeiro_tick']} / {v['primeiro_agente']} / "
            f"{v['ganho_total']:.2f} / {v['peso_final']}"
        )
    print(f"Nascimento das arestas: {al['nascimento_das_arestas']['ordem_nascimento']}")
    print(f"Tick em que o cluster atinge k arestas: {al['nascimento_das_arestas']['tick_atinge_k_arestas']}")
    print()
    print("Sonda de alocação (raio -> Símbolo / depósitos / criadores / reforços / redundantes / quota redundante / ganho / agente top):")
    linhas = sondar_alocacao()
    for linha in linhas:
        r = linha["resumo"]
        print(
            f"  {linha['raio']} -> tick {linha['simbolo_tick']} / "
            f"{r['total_aceites']} aceites / {r['criadores']} criadores / "
            f"{r['reforcos']} reforços / {r['redundantes']} redundantes / "
            f"quota {r['quota_redundante']} / ganho {r['ganho_total']} / "
            f"top {r['agente_top']} ({r['quota_max_agente']})"
        )
    hip = testar_hipoteses(linhas)
    print("Hipóteses:")
    for chave, h in hip.items():
        print(f"  {chave}: {h}")


if __name__ == "__main__":
    imprimir_relatorio(rodar_party_causal_alocacao())
