"""Isekai Zero — A Party Causal: variante VISÃO LOCAL + RICH-CLUB.

Assente na POMDP (party_causal_pomdp.py) sem a alterar — a mesma
semente, os mesmos 40 ticks, os mesmos raios de visão, os mesmos
agentes locais — e troca EXACTAMENTE UMA coisa: o PORTÃO DE
ESTADO. O portão do veto-estado (JSD ordenado < 0,28, só nos
checkpoints) é substituído pelo portão rich-club k(n) com
vigilância por tick (o da K VARIÁVEL: party_causal_k_variavel.py),
importado, não duplicado. Tudo o resto fica como na POMDP: visão
por raio, gatilho da tentativa no ISC visível, verificação global,
Sistema com reinjecção global, sem decaimento, sem segundo
critério.

## O problema que esta variante ataca

A POMDP provou que a visão parcial integra MELHOR do que a
global: a raio 2 o Símbolo forma-se no tick 26 — antes da base —
e o cluster chega à clique completa (10 arestas, ISC 1,0), com
menos depósitos (79 contra 94). Mas a POMDP usa o portão ANTIGO
do veto-estado (JSD ordenado < 0,28) — por isso tem 0 vetos por
estado em todos os raios. E a k variável é o portão actual que
morde: a 1,10 o Símbolo é inválido, e o controlo separa-se com
folga mínima de só 0,003. A pergunta é genuinamente por
responder: o cluster da raio 2 — a clique completa, que integra
melhor — sobrevive ao portão que morde? Ou a melhor integração
traz consigo a tirania?

## O portão (importado da K VARIÁVEL, não redefinido)

    ISC_Local >= 0,85 E JSD rich-club k(n) < limiar(n),
    com k(n) = ceil(n/3) e limiar(n) reescalado por n
    (0,1509 / 0,1708 / 0,1157 / 0,1323 / 0,1454 / 0,1129
    para n = 5..10), vigiado no fim de CADA TICK e, em
    paralelo, nos checkpoints.

A guarda é a mesma da TIRANIA: com < 5 arestas o JSD não é um
sinal — a trajetória regista None nesses ticks. O portão é um
observador, não bloqueia nada — como em todas as variantes.

## O que fica como na POMDP (a dinâmica é idêntica, tick a tick)

- O estado é o _EstadoPOMDP e os agentes são os _AGIR_POMDP:
  as mesmas ramificações, o mesmo consumo de RNG, a mesma
  semente. O controlo (raio ∞) reproduz a POMDP exactamente
  (Símbolo tick 32, Ren 28x verdadeiro / 1x falso, Veyra 6x)
  e a base; os testes fixam-no. A única diferença é o que o
  AUDITOR global mede no fim de cada tick.
- A raio 1 o Símbolo nunca é tentado (ISC visível máx 0,40 <
  0,70) e o cluster pára nos 0,80 (8 arestas) — como na POMDP.
  O portão novo vigia na mesma: o estado pode ser tirânico
  pela MEDIDA mesmo sem Símbolo reclamado, e a trajetória
  regista-o (ticks com a medida abaixo do limiar, e a folga
  mínima da medida contra o limiar, com ou sem fase densa).

## A comparação com o portão antigo (na mesma corrida)

A trajetória regista as DUAS medidas lado a lado (JSD ordenado
antigo e JSD rich-club k(n) novo, mais o k = 4 fixo) e o Gini
no mesmo estado. O portão antigo é avaliado na mesma
trajetória — ticks tirânicos pelo JSD ordenado e vetos por
estado que ele registaria nos checkpoints — sem re-correr a
simulação: a dinâmica é a da POMDP, por isso o veredicto do
portão antigo nesta trajetória É o veredicto da POMDP (0 vetos
em todos os raios). Os testes fixam-no contra uma corrida
POMDP real.

## O resultado (resumo — ver os testes para os números)

A clique completa da raio 2 SOBREVIVE ao portão que morde: 0
vetos por checkpoint e por tick em TODOS os raios, Símbolo
válido por ambos os portões a raio 2 (tick 26, clique completa,
ISC 1,0) e no controlo (tick 32, Ren 28x/1x, Veyra 6x). A
melhor integração NÃO traz tirania pelo portão k(n). A folga
mínima na fase densa a raio 2 é 0,0145 (tick 24) — ~5x a folga
do controlo da k variável (0,003), mas fina em termos
absolutos. A raio 1 não há fase densa (ISC máx 0,80), mas a
medida mergulha abaixo do limiar nos ticks 14–15 (folga mínima
−0,0227 no tick 14): o estado é tirânico pela medida na fase
esparsa, e só o ISC < 0,85 impede o portão de armar. Nuance: com
k = 4 FIXO, a medida mergulha abaixo do 0,113 no primeiro tick
denso a raio 2 (tick 24, JSD 0,1024 — profundidade 0,0106) e
roça-o depois (folga mínima 0,0004) — o portão k(n) absorve
exactamente esse mergulho (a n = 9 o limiar é 0,1454 e a medida
k(n) é 0,1599). Mas o mergulho é ANTES da reclamação (tick 26):
mesmo pelo portão de k = 4 fixo, o Símbolo contaria como válido
— o veto seria de um estado sem Símbolo reclamado. Os pesos
finais a raio 2 não são um rich club (Sora–Ren a 1,0, o resto
0,31–0,55): uma aresta dominante, não um hub — é por isso que
a medida rich-club fica acima do limiar. O controlo sobrevive
com folga 0,0334 na fase densa (mais do que os 0,003 da
k variável: sem decaimento nem amplificação, o cluster
concentra menos). O portão antigo, avaliado na mesma
trajetória, também não veta em nenhum raio — é o veredicto da
POMDP. O próximo passo que o resultado sugere: a pergunta
está respondida para esta dinâmica — o que falta é perceber
PORQUÊ a visão parcial integra melhor (o que muda na
alocação dos depósitos a raio 2), ou aceitar a folga 0,0145
como o novo bairro concorrido e calibrar o portão para ela.
"""

from . import party_causal as pc
from .auditoria import gini
from .party_causal_tyranny import _checkpoint_tyranny, jsd_pesos_ordenado
from .party_causal_veto_estado import (
    JSD_ESTADO,
    MIN_ARESTAS_JSD,
    _simbolo_valido,
)
from .party_causal_pomdp import (
    _AGIR_POMDP,
    _EstadoPOMDP,
    RAIO_INFINITO,
    RAIO_LOCAL,
    RAIO_VIZINHOS,
    RAIOS_SONDA,
)
from .party_causal_k_variavel import (
    TABELA_CALIBRACAO,
    _margens_bairro,
    _vigiar_estado_k,
    _vigiar_estado_tick_k,
    jsd_pesos_richclub_k,
    k_variavel,
    limiar_estado_k,
)
from .party_causal_richclub import (
    JSD_RC_ESTADO,
    JSD_RC_UNIFORME,
    jsd_pesos_richclub,
)


def _trajetoria_tick_rc(est):
    """Um tick da trajetória: o estado GLOBAL (auditor) com as
    DUAS medidas lado a lado, e o que os agentes veem dele. É a
    diferença entre as duas colunas que mede o custo da visão
    local — e a diferença entre as duas medidas que decide se o
    portão que morde veta o cluster que integra melhor."""
    sub = est.subgrafo_party()
    isc_tick = sub.n_arestas() / sub.max_arestas() if sub.max_arestas() else 0.0
    if sub.n_arestas() >= MIN_ARESTAS_JSD:
        jsd_ord = jsd_pesos_ordenado(sub)
        jsd_rck = jsd_pesos_richclub_k(sub)
        jsd_rc = jsd_pesos_richclub(sub)
        gini_tick = gini(sub.pesos())
        k_tick = k_variavel(sub.n_arestas())
        limiar_tick = limiar_estado_k(sub.n_arestas())
    else:
        jsd_ord = jsd_rck = jsd_rc = gini_tick = None
        k_tick = None
        limiar_tick = None
    iscs_vis = [est.isc_visivel(n) for n in pc.NOMES[:5]]
    return {
        "tick": est.tick,
        "n_arestas": sub.n_arestas(),
        "k": k_tick,
        "limiar": limiar_tick,
        "isc_local": round(isc_tick, 4),
        "jsd_ordenado": round(jsd_ord, 4) if jsd_ord is not None else None,
        "jsd_richclub_k": round(jsd_rck, 4) if jsd_rck is not None else None,
        "jsd_richclub": round(jsd_rc, 4) if jsd_rc is not None else None,
        "gini": round(gini_tick, 4) if gini_tick is not None else None,
        "isc_visivel_medio": round(sum(iscs_vis) / len(iscs_vis), 4),
        "isc_visivel_max": round(max(iscs_vis), 4),
    }


def rodar_party_causal_pomdp_richclub(
    semente=pc.SEMENTE, n_ticks=pc.N_TICKS, raio=RAIO_LOCAL
):
    """Corre a variante (40 ticks, checkpoint a cada 10, vigilância
    de estado rich-club k(n) em CADA TICK e, em paralelo, nos
    checkpoints) e devolve o relatório completo. A POMDP não é
    alterada: usa-se o seu estado e os seus agentes, sem remendo
    de _tentar_simbolo nem decaimento — a visão é a única
    variável da dinâmica, e o portão é a única variável do
    auditor. Com raio = ∞ a variante É a POMDP com o portão
    trocado: a trajectória, o Símbolo e os contadores são os da
    POMDP, tick a tick — só os vetos mudam."""
    est = _EstadoPOMDP(semente, raio)
    est.vetos = []
    est.vetos_estado = []
    est.vetos_tick = []
    checkpoints = []
    trajetoria = []
    jsd_rck_min = None
    jsd_rck_min_tick = None
    jsd_rc_min = None
    jsd_rc_min_tick = None
    jsd_ord_min = None
    jsd_ord_min_tick = None
    cruzamentos = {}
    for tick in range(1, n_ticks + 1):
        est.tick = tick
        pc._agir_sistema(est)
        for nome in pc.NOMES[:5]:
            _AGIR_POMDP[nome](est)
        t = _trajetoria_tick_rc(est)
        trajetoria.append(t)
        jsd_rck = t["jsd_richclub_k"]
        jsd_rc = t["jsd_richclub"]
        jsd_ord = t["jsd_ordenado"]
        limiar_tick = t["limiar"]
        if jsd_rck is not None:
            if jsd_rck_min is None or jsd_rck < jsd_rck_min:
                jsd_rck_min, jsd_rck_min_tick = jsd_rck, tick
            if jsd_rck < limiar_tick and "rck_estado" not in cruzamentos:
                cruzamentos["rck_estado"] = tick
            if jsd_rck < JSD_ESTADO and "rck_0.28_sem_reescala" not in cruzamentos:
                cruzamentos["rck_0.28_sem_reescala"] = tick
        if jsd_rc is not None:
            if jsd_rc_min is None or jsd_rc < jsd_rc_min:
                jsd_rc_min, jsd_rc_min_tick = jsd_rc, tick
        if jsd_ord is not None:
            if jsd_ord_min is None or jsd_ord < jsd_ord_min:
                jsd_ord_min, jsd_ord_min_tick = jsd_ord, tick
        # A vigilância por tick corre no fim de CADA tick, com o
        # limiar do n DESSE tick — o portão da k variável.
        _vigiar_estado_tick_k(est, jsd_rck, jsd_ord, limiar_tick)
        if tick % pc.CHECKPOINT == 0:
            # A vigilância por checkpoint corre no mesmo lugar da
            # vigília, com o limiar do n DESSE checkpoint.
            _vigiar_estado_k(est, jsd_rck, jsd_ord, limiar_tick)
            c = _checkpoint_tyranny(est, jsd_ord)
            c["jsd_richclub_k"] = t["jsd_richclub_k"]
            c["jsd_richclub"] = t["jsd_richclub"]
            c["k"] = t["k"]
            c["limiar"] = t["limiar"]
            c["vetos_estado"] = len(est.vetos_estado)
            c["vetos_tick"] = len(est.vetos_tick)
            c["isc_visivel_medio"] = t["isc_visivel_medio"]
            c["isc_visivel_max"] = t["isc_visivel_max"]
            checkpoints.append(c)
            if est.simbolo_tick is not None:
                pc._tentar_meta_simbolo(est, f"checkpoint tick {tick}")
    # Avaliação final: o tick 40 já é checkpoint (40 % 10 == 0).
    # Só se vigia o estado final fora dos checkpoints quando o
    # último tick não é um checkpoint — sem dupla contagem (a
    # vigilância por tick já cobriu o último tick). A guarda de
    # >= 5 arestas é a do próprio portão.
    if n_ticks % pc.CHECKPOINT != 0:
        sub = est.subgrafo_party()
        if sub.n_arestas() >= MIN_ARESTAS_JSD:
            _vigiar_estado_k(
                est,
                jsd_pesos_richclub_k(sub),
                jsd_pesos_ordenado(sub),
                limiar_estado_k(sub.n_arestas()),
            )
    jsd_finais = [c["jsd_pesos"] for c in checkpoints if c["jsd_pesos"] is not None]
    jsd_min = min(jsd_finais) if jsd_finais else None
    jsd_final = jsd_finais[-1] if jsd_finais else None
    jsd_ord_finais = [c["jsd_ordenado"] for c in checkpoints if c["jsd_ordenado"] is not None]
    jsd_ord_final = jsd_ord_finais[-1] if jsd_ord_finais else None
    jsd_rck_finais = [c["jsd_richclub_k"] for c in checkpoints if c["jsd_richclub_k"] is not None]
    jsd_rck_final = jsd_rck_finais[-1] if jsd_rck_finais else None
    jsd_rc_finais = [c["jsd_richclub"] for c in checkpoints if c["jsd_richclub"] is not None]
    jsd_rc_final = jsd_rc_finais[-1] if jsd_rc_finais else None
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
    # Critérios da variante — os dois portões do portão novo, lado
    # a lado (checkpoint e tick).
    criterios["veto_estado_disparou"] = len(est.vetos_estado) > 0
    criterios["veto_tick_disparou"] = len(est.vetos_tick) > 0
    criterios["cluster_tiranico"] = len(est.vetos_estado) > 0
    criterios["simbolo_valido"] = _simbolo_valido(est.simbolo_tick, est.vetos_estado)
    criterios["simbolo_valido_checkpoint"] = criterios["simbolo_valido"]
    criterios["simbolo_valido_tick"] = _simbolo_valido(est.simbolo_tick, est.vetos_tick)
    criterios["veredicto_muda"] = (
        criterios["simbolo_valido"] != criterios["simbolo_valido_tick"]
    )
    # Ticks em que o estado seria tirânico pela regra NOVA
    # (ISC >= 0,85 E JSDrc_k < limiar(n)), na trajetória por tick:
    # os vetos por tick têm de ser exactamente estes ticks — é o
    # cheque de consistência entre a trajetória e o portão.
    ticks_tiranicos = [
        t["tick"]
        for t in trajetoria
        if t["isc_local"] >= 0.85
        and t["jsd_richclub_k"] is not None
        and t["jsd_richclub_k"] < t["limiar"]
    ]
    ticks_tiranicos_028 = [
        t["tick"]
        for t in trajetoria
        if t["isc_local"] >= 0.85
        and t["jsd_richclub_k"] is not None
        and t["jsd_richclub_k"] < JSD_ESTADO
    ]
    # O portão ANTIGO na mesma trajetória: ticks tirânicos pelo
    # JSD ordenado (< 0,28) e os vetos por estado que ele
    # registaria nos checkpoints — é o veredicto da POMDP, sem
    # re-correr a simulação (a dinâmica é a mesma, tick a tick).
    ticks_tiranicos_ord = [
        t["tick"]
        for t in trajetoria
        if t["isc_local"] >= 0.85
        and t["jsd_ordenado"] is not None
        and t["jsd_ordenado"] < JSD_ESTADO
    ]
    vetos_estado_antigo = [
        t["tick"]
        for t in trajetoria
        if t["tick"] % pc.CHECKPOINT == 0
        and t["isc_local"] >= 0.85
        and t["jsd_ordenado"] is not None
        and t["jsd_ordenado"] < JSD_ESTADO
    ]
    # A medida nova abaixo do limiar, com ou sem fase densa: a
    # raio 1 não há fase densa (ISC máx 0,80), mas o estado pode
    # ser tirânico pela medida — a folga mínima da medida contra
    # o limiar, em todos os ticks com JSD, é o resultado da
    # raio 1 para o portão.
    folgas_medida = [
        (t["jsd_richclub_k"] - t["limiar"], t["tick"])
        for t in trajetoria
        if t["jsd_richclub_k"] is not None and t["limiar"] is not None
    ]
    folga_min_medida = min(folgas_medida) if folgas_medida else None
    ticks_medida_abaixo = [
        t["tick"]
        for t in trajetoria
        if t["jsd_richclub_k"] is not None
        and t["limiar"] is not None
        and t["jsd_richclub_k"] < t["limiar"]
    ]
    criterios["simbolo_morto_por_varpn"] = bool(
        simbolo is False
        and varpn_final is not None
        and varpn_final > 0.36
        and checkpoints
        and checkpoints[-1]["isc_local"] >= 0.85
    )
    refs, _, _ = pc.calibrar_lambda2()
    # Comparação explícita entre os dois portões, na mesma corrida.
    vetos_tick_ticks = [v["tick"] for v in est.vetos_tick]
    vetos_ckpt_ticks = [v["tick"] for v in est.vetos_estado]
    primeiro_tick_reclamado = next(
        (v["tick"] for v in est.vetos_tick if v["simbolo_reclamado"]), None
    )
    primeiro_ckpt_reclamado = next(
        (v["tick"] for v in est.vetos_estado if v["simbolo_reclamado"]), None
    )
    comparacao = {
        "vetos_checkpoint": len(est.vetos_estado),
        "vetos_tick": len(est.vetos_tick),
        "primeiro_veto_checkpoint": vetos_ckpt_ticks[0] if vetos_ckpt_ticks else None,
        "primeiro_veto_tick": vetos_tick_ticks[0] if vetos_tick_ticks else None,
        "primeiro_veto_tick_reclamado": primeiro_tick_reclamado,
        "primeiro_veto_checkpoint_reclamado": primeiro_ckpt_reclamado,
        "simbolo_nasce_tiranico": bool(
            simbolo
            and primeiro_tick_reclamado is not None
            and primeiro_tick_reclamado == est.simbolo_tick
        ),
        "veredicto_muda": criterios["veredicto_muda"],
        "simbolo_valido_checkpoint": criterios["simbolo_valido_checkpoint"],
        "simbolo_valido_tick": criterios["simbolo_valido_tick"],
    }
    # A visão no fim: o que cada membro vê do cluster integrado.
    visao_final = {
        nome: {
            "arestas_party_visiveis": len(est.arestas_party_visiveis(nome)),
            "isc_visivel": round(est.isc_visivel(nome), 4),
        }
        for nome in pc.NOMES[:5]
    }
    # Pesos finais da party (ordem decrescente, com nomes): é isto
    # que mostra o hub da Sora — ou a sua ausência — sem ser
    # preciso re-correr a simulação para inspeccionar o estado.
    sub_final = est.subgrafo_party()
    pesos_finais = sorted(
        (
            {
                "peso": round(r.peso, 4),
                "a": est.nome_de_hash(r.origem),
                "b": est.nome_de_hash(r.destino),
                "incidente_sora": est.hashes["Sora"] in (r.origem, r.destino),
            }
            for r in sub_final.todos_rastros()
        ),
        key=lambda d: -d["peso"],
    )
    return {
        "variante": "visão local (POMDP) + portão rich-club k(n) com vigilância por tick",
        "semente": semente,
        "ticks": n_ticks,
        "pesos_finais": pesos_finais,
        "alavanca": {
            "nome": "raio de visão + portão rich-club k(n)",
            "raio": raio,
            "regra_k": "k(n) = ceil(n/3)",
            "tabela_calibracao": {
                str(n): {"k": k, "limiar": lim}
                for n, (k, lim) in sorted(TABELA_CALIBRACAO.items())
            },
            "jsd_rc_estado_k4": JSD_RC_ESTADO,
            "jsd_rc_uniforme_k4": JSD_RC_UNIFORME,
            "jsd_estado_antigo": JSD_ESTADO,
            "min_arestas_jsd": MIN_ARESTAS_JSD,
        },
        "checkpoints": checkpoints,
        "trajetoria": trajetoria,
        "ticks_tiranicos": ticks_tiranicos,
        "ticks_tiranicos_028": ticks_tiranicos_028,
        "ticks_tiranicos_ord": ticks_tiranicos_ord,
        "vetos_estado_antigo": vetos_estado_antigo,
        "folga_min_medida": (
            {"folga": round(folga_min_medida[0], 4), "tick": folga_min_medida[1]}
            if folga_min_medida is not None
            else None
        ),
        "ticks_medida_abaixo": ticks_medida_abaixo,
        "comparacao": comparacao,
        "margens_bairro": _margens_bairro(trajetoria),
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
            "vetos_tick": list(est.vetos_tick),
        },
        "criterios": criterios,
        "jsd_min": round(jsd_min, 4) if jsd_min is not None else None,
        "jsd_final": round(jsd_final, 4) if jsd_final is not None else None,
        "jsd_ordenado_min": round(jsd_ord_min, 4) if jsd_ord_min is not None else None,
        "jsd_ordenado_min_tick": jsd_ord_min_tick,
        "jsd_ordenado_final": round(jsd_ord_final, 4) if jsd_ord_final is not None else None,
        "jsd_richclub_k_min": round(jsd_rck_min, 4) if jsd_rck_min is not None else None,
        "jsd_richclub_k_min_tick": jsd_rck_min_tick,
        "jsd_richclub_k_final": round(jsd_rck_final, 4) if jsd_rck_final is not None else None,
        "jsd_richclub_min": round(jsd_rc_min, 4) if jsd_rc_min is not None else None,
        "jsd_richclub_min_tick": jsd_rc_min_tick,
        "jsd_richclub_final": round(jsd_rc_final, 4) if jsd_rc_final is not None else None,
        "cruzamentos": {str(k2): v for k2, v in sorted(cruzamentos.items())},
        "referencias": {
            "lambda2": refs,
            "lambda2_min": pc.LAMBDA2_MIN,
            "jsd_uniforme_10": round(
                pc.jsd_bits([0.1] * 10, pc.prototipo_tirania(10)), 4
            ),
            "jsd_rc_uniforme_10": JSD_RC_UNIFORME,
        },
    }


def sondar_pomdp_richclub(raios=RAIOS_SONDA, semente=pc.SEMENTE):
    """Sonda de raios: corre a variante em cada raio e devolve,
    por raio, se o Símbolo se formou, os contadores do Ren e da
    Veyra, os vetos do portão NOVO (checkpoint e tick) e do
    portão ANTIGO (na mesma trajetória), os dois veredictos de
    validade, os ticks tirânicos novos e antigos, as margens do
    bairro concorrido, o Gini final, os JSDs mínimo e final
    (ordenado antigo, rich-club k(n) novo e k = 4 fixo), o VarPn
    final e o ISC visível final. A pergunta que a sonda
    responde: o cluster da raio 2 — a clique completa, que
    integra melhor — sobrevive ao portão que morde?"""
    linhas = []
    for raio in raios:
        rel = rodar_party_causal_pomdp_richclub(semente=semente, raio=raio)
        final = rel["checkpoints"][-1] if rel["checkpoints"] else {}
        traj_final = rel["trajetoria"][-1] if rel["trajetoria"] else {}
        linhas.append(
            {
                "raio": raio,
                "simbolo_tick": rel["eventos"]["simbolo_tick"],
                "tentativas_simbolo": rel["eventos"]["tentativas_simbolo"],
                "ren_verdadeiro": rel["eventos"]["ren_verdadeiro"],
                "ren_falso": rel["eventos"]["ren_falso"],
                "veyra_verdadeiro": rel["eventos"]["veyra_verdadeiro"],
                "vetos_tentativa": len(rel["eventos"]["vetos"]),
                "vetos_estado": len(rel["eventos"]["vetos_estado"]),
                "vetos_tick": len(rel["eventos"]["vetos_tick"]),
                "primeiro_veto_checkpoint": rel["comparacao"]["primeiro_veto_checkpoint"],
                "primeiro_veto_tick": rel["comparacao"]["primeiro_veto_tick"],
                "primeiro_veto_tick_reclamado": rel["comparacao"]["primeiro_veto_tick_reclamado"],
                "primeiro_veto_checkpoint_reclamado": rel["comparacao"]["primeiro_veto_checkpoint_reclamado"],
                "simbolo_nasce_tiranico": rel["comparacao"]["simbolo_nasce_tiranico"],
                "simbolo_valido": rel["criterios"]["simbolo_valido"],
                "simbolo_valido_tick": rel["criterios"]["simbolo_valido_tick"],
                "veredicto_muda": rel["criterios"]["veredicto_muda"],
                "ticks_tiranicos": list(rel["ticks_tiranicos"]),
                "ticks_tiranicos_ord": list(rel["ticks_tiranicos_ord"]),
                "vetos_estado_antigo": list(rel["vetos_estado_antigo"]),
                "folga_min_medida": rel["folga_min_medida"],
                "ticks_medida_abaixo": list(rel["ticks_medida_abaixo"]),
                "margens_bairro": rel["margens_bairro"],
                "n_arestas_final": final.get("n_arestas"),
                "isc_final": final.get("isc_local"),
                "isc_visivel_medio_final": traj_final.get("isc_visivel_medio"),
                "isc_visivel_max_final": traj_final.get("isc_visivel_max"),
                "gini_final": final.get("gini"),
                "jsd_ordenado_min": rel["jsd_ordenado_min"],
                "jsd_ordenado_min_tick": rel["jsd_ordenado_min_tick"],
                "jsd_ordenado_final": rel["jsd_ordenado_final"],
                "jsd_richclub_k_min": rel["jsd_richclub_k_min"],
                "jsd_richclub_k_min_tick": rel["jsd_richclub_k_min_tick"],
                "jsd_richclub_k_final": rel["jsd_richclub_k_final"],
                "jsd_richclub_min": rel["jsd_richclub_min"],
                "jsd_richclub_min_tick": rel["jsd_richclub_min_tick"],
                "jsd_richclub_final": rel["jsd_richclub_final"],
                "varpn_final": final.get("var_ponderada_normalizada"),
                "depositos": dict(rel["eventos"]["depositos_por_agente"]),
                "seguimentos": dict(rel["eventos"]["seguimentos_por_agente"]),
            }
        )
    return linhas


def imprimir_relatorio(rel):
    """Tabela da variante + sonda de raios + margens do bairro
    concorrido nas duas medidas."""
    print("Isekai Zero — A Party Causal: variante VISÃO LOCAL + RICH-CLUB (POMDP + portão k(n))")
    print(f"semente={rel['semente']}  ticks={rel['ticks']}  raio={rel['alavanca']['raio']}  "
          f"jsd_estado_antigo={rel['alavanca']['jsd_estado_antigo']}")
    print(f"Tabela de calibração (n -> k, limiar): {rel['alavanca']['tabela_calibracao']}")
    print("tick | arest | k | limiar | ISC   | VarPn | ISCaux | Gini  | λ₂    | MIP   | JSDp  | JSDord | JSDrcK | JSDrc4 | VetT | VetE | VetK | ISCvis | Símbolo")
    for c in rel["checkpoints"]:
        print(
            f"{c['tick']:>4} | {c['n_arestas']:>5} | {c['k'] if c['k'] is not None else '-':>2} | "
            f"{c['limiar'] if c['limiar'] is not None else '-':>6} | {c['isc_local']:.3f} | "
            f"{c['var_ponderada_normalizada']:.3f} | {c['isc_aux']:.3f} | "
            f"{c['gini']:.3f} | {c['lambda2']:.3f} | {c['mip_corte_min']:.3f} | "
            f"{c['jsd_pesos'] if c['jsd_pesos'] is not None else '-':>5} | "
            f"{c['jsd_ordenado'] if c['jsd_ordenado'] is not None else '-':>6} | "
            f"{c['jsd_richclub_k'] if c['jsd_richclub_k'] is not None else '-':>6} | "
            f"{c['jsd_richclub'] if c['jsd_richclub'] is not None else '-':>6} | "
            f"{c['vetos']:>4} | {c['vetos_estado']:>4} | {c['vetos_tick']:>4} | "
            f"{c['isc_visivel_medio']:.3f} | {'SIM' if c['simbolo'] else 'não'}"
        )
    ev = rel["eventos"]
    print(f"Símbolo formado no tick: {ev['simbolo_tick']}")
    print(f"Ren seguiu o verdadeiro fraco: {ev['ren_verdadeiro']}x (falso: {ev['ren_falso']}x)")
    print(f"Veyra seguiu o verdadeiro fraco: {ev['veyra_verdadeiro']}x")
    print(f"Tentativas de Símbolo: {ev['tentativas_simbolo']}; Meta-Símbolo: {len(ev['tentativas_meta_simbolo'])}")
    print(f"Vetos por tentativa: {len(ev['vetos'])} -> {ev['vetos']}")
    print(f"Vetos por estado (checkpoint, rich-club k(n)): {len(ev['vetos_estado'])} -> {[v['tick'] for v in ev['vetos_estado']]}")
    print(f"Vetos por estado (tick, rich-club k(n)): {len(ev['vetos_tick'])} -> {[v['tick'] for v in ev['vetos_tick']]}")
    print(f"Comparação: {rel['comparacao']}")
    print(f"Margens do bairro concorrido: {rel['margens_bairro']}")
    print(f"Ticks tirânicos k(n) (trajetória por tick): {rel['ticks_tiranicos']}")
    print(f"Ticks tirânicos JSD ordenado (portão antigo): {rel['ticks_tiranicos_ord']}")
    print(f"Vetos por estado do portão antigo (checkpoints): {rel['vetos_estado_antigo']}")
    print(f"Folga mínima da medida contra o limiar: {rel['folga_min_medida']}; "
          f"ticks com a medida abaixo do limiar: {rel['ticks_medida_abaixo']}")
    print(f"Depósitos por agente: {ev['depositos_por_agente']}")
    print(f"Seguimentos por agente: {ev['seguimentos_por_agente']}")
    print(f"Visão final (arestas da party visíveis / ISC visível): {rel['visao_final']}")
    print(f"Pesos finais (ordem decrescente): {rel['pesos_finais']}")
    print(f"JSD rich-club k(n): mínimo {rel['jsd_richclub_k_min']} (tick {rel['jsd_richclub_k_min_tick']}), "
          f"final {rel['jsd_richclub_k_final']}; JSD rich-club k=4: mínimo {rel['jsd_richclub_min']} "
          f"(tick {rel['jsd_richclub_min_tick']}), final {rel['jsd_richclub_final']}; "
          f"JSD ordenado: mínimo {rel['jsd_ordenado_min']} "
          f"(tick {rel['jsd_ordenado_min_tick']}), final {rel['jsd_ordenado_final']}; "
          f"cruzamentos: {rel['cruzamentos']}")
    print(f"Critérios: {rel['criterios']}")
    print()
    print("Sonda de raios (raio -> Símbolo / tentativas / Ren verd. / Ren falso / Veyra verd. / vetos tent. / vetos estado / vetos tick / 1º veto tick / válido ckpt / válido tick / veredicto muda / ticks tiranicos k(n) / vetos estado antigo / Gini final / JSDrcK mín / JSDrcK final / JSDord mín / VarPn):")
    for linha in sondar_pomdp_richclub():
        print(
            f"  {linha['raio']} -> tick {linha['simbolo_tick']} / "
            f"{linha['tentativas_simbolo']} tent. / Ren {linha['ren_verdadeiro']}/{linha['ren_falso']} / "
            f"Veyra {linha['veyra_verdadeiro']} / {linha['vetos_tentativa']} tent. / "
            f"{linha['vetos_estado']} estado / {linha['vetos_tick']} tick / "
            f"1º tick {linha['primeiro_veto_tick']} / válido ckpt {linha['simbolo_valido']} / "
            f"válido tick {linha['simbolo_valido_tick']} / muda {linha['veredicto_muda']} / "
            f"tiranicos {linha['ticks_tiranicos']} / antigo {linha['vetos_estado_antigo']} / "
            f"Gini {linha['gini_final']} / JSDrcK mín {linha['jsd_richclub_k_min']} (tick {linha['jsd_richclub_k_min_tick']}) / "
            f"JSDrcK final {linha['jsd_richclub_k_final']} / JSDord mín {linha['jsd_ordenado_min']} / "
            f"VarPn {linha['varpn_final']}"
        )


if __name__ == "__main__":
    imprimir_relatorio(rodar_party_causal_pomdp_richclub())
