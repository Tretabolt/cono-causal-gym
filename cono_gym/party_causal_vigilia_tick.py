"""Isekai Zero — A Party Causal: variante VIGILÂNCIA POR TICK.

Reutiliza a variante PROTÓTIPO DE TIRANIA DE RICH-CLUB
(party_causal_richclub.py) sem a alterar — a mesma semente, os
mesmos 40 ticks, o mesmo decaimento (0,95), a mesma Lira com
força total, o mesmo portão de veto por tentativa da TIRANIA
(JSD ordenado < 0,18), a mesma amplificação da Sora, o mesmo
protótipo rich-club (k = 4) e o mesmo limiar reescalado (0,113)
— e troca UMA coisa: a GRANULARIDADE da vigilância de estado.

## O problema que esta variante ataca

A rich-club provou que o veto por estado morde — mas deixou uma
questão em aberto. O CONTROLO (fator 1,00, sem amplificação) é
transitoriamente tirânico pela trajetória (ticks 32–36, ISC 0,90,
JSD rich-club ~0,10) e o Símbolo é reclamado no tick 32 — no
meio do transiente. Mas o portão por CHECKPOINT não o apanha: no
checkpoint 30 o ISC ainda é 0,80 e no 40 o JSDrc já recuperou
para 0,1232. A trajetória vê-o; o portão não. A pergunta que
ficou foi: se o portão vigiar TODOS OS TICKS em vez de só os
checkpoints, o controlo passa a ter o Símbolo invalidado? E os
veredictos a 1,05–1,50 mudam — invalidação mais cedo, mais
vetos?

## O que muda (e o que não muda)

A dinâmica é a da rich-club, tick a tick — agentes, RNG,
amplificação, decaimento, portão de veto por tentativa. A única
mudança é o observador: o portão de estado (ISC >= 0,85 E JSD
rich-club < 0,113) corre no FIM DE CADA TICK, e não só nos
checkpoints 10/20/30/40. O portão por checkpoint CONTINUA a
correr, no mesmo lugar e com a mesma função (_vigiar_estado_rc
da rich-club, sem a tocar): os dois vetos ficam registados lado
a lado, no mesmo relatório e sobre a mesma corrida — a variante
só prova o seu valor se apanhar alguma coisa que o checkpoint
não apanha, ou se mudar algum veredicto. Os vetos por tick vão
para `est.vetos_tick`; os por checkpoint continuam em
`est.vetos_estado`. O critério de validade é o mesmo nos dois
casos (_simbolo_valido do veto-estado): um Símbolo reclamado só
conta como válido se nunca foi apanhado tirânico, pela
vigilância em causa, enquanto existia.

## Definições do CENÁRIO (não canónicas)

As da rich-club, herdadas sem alteração: protótipo rich-club
(k = 4), JSD rich-club (pesos ordenados por ordem decrescente),
limiar reescalado JSD_RC_ESTADO = 0,113. A única definição nova
é a da variante: "vigilância por tick" = o portão de estado
corre no fim de cada tick, com a mesma regra e o mesmo limiar do
portão por checkpoint. Um "veto por tick" é um evento de veto
por estado registado fora de um checkpoint; um "veto por
checkpoint" é o mesmo evento, registado num checkpoint. Os dois
têm o mesmo formato de evento (o campo "simbolo_no_checkpoint"
é, nos eventos por tick, a qualificação do cluster como Símbolo
nesse tick — o mesmo significado, amostrado por tick), mais o
campo "via" ("tick" ou "checkpoint") que os distingue.

## O resultado (resumo — ver os testes para os números)

A hipótese CONFIRMA-SE — e o veredicto que muda é o do
controlo. A 1,00 o portão por tick dispara 5 vezes (ticks
32–36, o primeiro no próprio tick em que o Símbolo é
reclamado) e o Símbolo, válido pelo checkpoint, é INVÁLIDO
pela vigilância por tick: é a única mudança de veredicto da
sonda. Nos níveis amplificados os veredictos não mudam (já
eram inválidos por checkpoint), mas a invalidação chega muito
mais cedo: o primeiro veto por tick reclamado é o próprio tick
do Símbolo em TODOS os níveis (17/21/25/28/32) — o Símbolo
nasce tirânico em toda a sonda, e sob a vigilância por tick
nenhum Símbolo é válido. Os vetos por tick são exactamente os
ticks tirânicos da trajetória em todos os níveis (5/21/18/21/
24) — o portão e a trajetória concordam. O "bairro concorrido"
não piora nem melhora: os vetos do controlo disparam com JSDrc
0,0997–0,1045, a 0,0085–0,0133 do limiar, e os ticks 37–40
ficam a 0,1159–0,1244, logo acima dele — o portão por tick não
inventa sinal (apanha um transiente que a medida já assinala),
mas expõe que o limiar atravessa os valores da fase densa do
controlo: um portão por tick dispara em pequenas depressões
abaixo de 0,113. Os critérios da base continuam a passar em
todos os níveis (Ren 23–28x o verdadeiro fraco, 0–2x o falso;
sucesso parcial e completo). O próximo passo que o resultado
sugere: um k que varie com n, ou um segundo critério — a
vigilância por tick esgotou o que a granularidade tinha para
dar.
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
from .party_causal_veto_estado import (
    JSD_ESTADO,
    MIN_ARESTAS_JSD,
    _simbolo_valido,
)
from .party_causal_sora import (
    FATOR_AMPLIFICACAO,
    _fazer_agir_sora,
)
from .party_causal_richclub import (
    JSD_RC_ESTADO,
    JSD_RC_UNIFORME,
    RICHCLUB_K,
    _vigiar_estado_rc,
    jsd_pesos_richclub,
    prototipo_richclub,
    rodar_party_causal_richclub,
)


def _vigiar_estado_tick(est, jsd_rc, jsd_ord):
    """Vigilância de ESTADO em CADA TICK, com a medida rich-club:
    a mesma regra do portão por checkpoint (ISC_Local >= 0,85 E
    JSD rich-club < JSD_RC_ESTADO), corrida no fim de cada tick.
    É um observador, não um portão — não bloqueia nada. Os eventos
    vão para est.vetos_tick, com o mesmo formato dos eventos por
    checkpoint (mais o campo "via": "tick"). Com < 5 arestas, ou
    sem JSD, não há sinal: devolve False sem registar."""
    sub = est.subgrafo_party()
    if sub.n_arestas() < MIN_ARESTAS_JSD or jsd_rc is None:
        return False
    rel = pc.avaliar_cluster(sub, "SIMBOLO_PARTY_001")
    if rel["isc_local"] >= 0.85 and jsd_rc < JSD_RC_ESTADO:
        est.vetos_tick.append(
            {
                "tick": est.tick,
                "isc_local": round(rel["isc_local"], 4),
                "var_ponderada_normalizada": round(
                    rel["var_ponderada_normalizada"], 4
                ),
                "jsd_richclub": round(jsd_rc, 4),
                "jsd_ordenado": round(jsd_ord, 4) if jsd_ord is not None else None,
                "gini": round(gini(sub.pesos()), 4),
                "n_arestas": sub.n_arestas(),
                "simbolo_reclamado": est.simbolo_tick is not None,
                "simbolo_no_checkpoint": rel["simbolo"],
                "via": "tick",
            }
        )
        est.eventos.append(
            (est.tick, "VETO POR ESTADO (tick) rich-club", round(jsd_rc, 4))
        )
        return True
    return False


def rodar_party_causal_vigilia_tick(
    semente=pc.SEMENTE,
    n_ticks=pc.N_TICKS,
    fator_amplificacao=FATOR_AMPLIFICACAO,
    fator_decaimento=FATOR_DECAIMENTO,
    piso=PISO_DECAIMENTO,
    k=RICHCLUB_K,
):
    """Corre a variante (40 ticks, checkpoint a cada 10, vigilância
    de estado rich-club em CADA TICK e, em paralelo, nos
    checkpoints) e devolve o relatório completo. A base não é
    alterada: o remendo de _tentar_simbolo é reposto no finally,
    e a corrida base continua a dar os mesmos números depois
    disto. Com fator_amplificacao = 1,00 a variante é o
    veto-estado exato com a medida trocada — é o controlo da
    sonda. A trajetória por tick regista as DUAS medidas (JSD
    ordenado antigo e JSD rich-club novo) e o Gini no mesmo
    estado. Os vetos por tick e por checkpoint ficam lado a lado
    no relatório: a comparação é explícita, na mesma corrida."""
    est = pc._Estado(semente)
    est.vetos = []
    est.vetos_estado = []
    est.vetos_tick = []
    agir = dict(pc._AGIR)
    agir_sora = _fazer_agir_sora(fator_amplificacao)
    agir["Sora"] = agir_sora
    checkpoints = []
    trajetoria = []
    jsd_rc_min = None
    jsd_rc_min_tick = None
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
                agir[nome](est)
            total_decaimentos += _aplicar_decaimento(est, fator_decaimento, piso)
            sub = est.subgrafo_party()
            isc_tick = (
                sub.n_arestas() / sub.max_arestas() if sub.max_arestas() else 0.0
            )
            # A mesma guarda da TIRANIA: com < 5 arestas o protótipo
            # é degenerado e o JSD não é um sinal — a trajetória
            # regista None nesses ticks, em vez de um mínimo falso.
            if sub.n_arestas() >= MIN_ARESTAS_JSD:
                jsd_ord = jsd_pesos_ordenado(sub)
                jsd_rc = jsd_pesos_richclub(sub, k)
                gini_tick = gini(sub.pesos())
            else:
                jsd_ord = jsd_rc = gini_tick = None
            trajetoria.append(
                {
                    "tick": tick,
                    "n_arestas": sub.n_arestas(),
                    "isc_local": round(isc_tick, 4),
                    "jsd_ordenado": round(jsd_ord, 4) if jsd_ord is not None else None,
                    "jsd_richclub": round(jsd_rc, 4) if jsd_rc is not None else None,
                    "gini": round(gini_tick, 4) if gini_tick is not None else None,
                }
            )
            if jsd_rc is not None:
                if jsd_rc_min is None or jsd_rc < jsd_rc_min:
                    jsd_rc_min, jsd_rc_min_tick = jsd_rc, tick
                if jsd_rc < JSD_RC_ESTADO and "rc_estado" not in cruzamentos:
                    cruzamentos["rc_estado"] = tick
                if jsd_rc < JSD_ESTADO and "rc_0.28_sem_reescala" not in cruzamentos:
                    cruzamentos["rc_0.28_sem_reescala"] = tick
            if jsd_ord is not None:
                if jsd_ord_min is None or jsd_ord < jsd_ord_min:
                    jsd_ord_min, jsd_ord_min_tick = jsd_ord, tick
            # A vigilância por tick corre no fim de CADA tick —
            # é a única mudança face à rich-club.
            _vigiar_estado_tick(est, jsd_rc, jsd_ord)
            if tick % pc.CHECKPOINT == 0:
                # A vigilância por checkpoint corre no mesmo lugar
                # da rich-club, com a mesma função, sem a tocar.
                _vigiar_estado_rc(est, jsd_rc, jsd_ord)
                c = _checkpoint_tyranny(est, jsd_ord)
                c["jsd_richclub"] = round(jsd_rc, 4) if jsd_rc is not None else None
                c["arestas_no_piso"] = _arestas_no_piso(est, piso)
                c["vetos_estado"] = len(est.vetos_estado)
                c["vetos_tick"] = len(est.vetos_tick)
                c["amplificacoes"] = agir_sora.contador["arestas"]
                checkpoints.append(c)
                if est.simbolo_tick is not None:
                    pc._tentar_meta_simbolo(est, f"checkpoint tick {tick}")
        # Avaliação final: o tick 40 já é checkpoint (40 % 10 == 0).
        # Só se vigia o estado final fora dos checkpoints quando o
        # último tick não é um checkpoint — sem dupla contagem (a
        # vigilância por tick já cobriu o último tick).
        if n_ticks % pc.CHECKPOINT != 0:
            sub = est.subgrafo_party()
            _vigiar_estado_rc(
                est, jsd_pesos_richclub(sub, k), jsd_pesos_ordenado(sub)
            )
    finally:
        pc._tentar_simbolo = original
    jsd_finais = [c["jsd_pesos"] for c in checkpoints if c["jsd_pesos"] is not None]
    jsd_min = min(jsd_finais) if jsd_finais else None
    jsd_final = jsd_finais[-1] if jsd_finais else None
    jsd_ord_finais = [c["jsd_ordenado"] for c in checkpoints if c["jsd_ordenado"] is not None]
    jsd_ord_final = jsd_ord_finais[-1] if jsd_ord_finais else None
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
    # Critérios da variante — os dois portões, lado a lado.
    criterios["veto_estado_disparou"] = len(est.vetos_estado) > 0
    criterios["veto_tick_disparou"] = len(est.vetos_tick) > 0
    criterios["cluster_tiranico"] = len(est.vetos_estado) > 0
    criterios["simbolo_valido"] = _simbolo_valido(est.simbolo_tick, est.vetos_estado)
    criterios["simbolo_valido_checkpoint"] = criterios["simbolo_valido"]
    criterios["simbolo_valido_tick"] = _simbolo_valido(est.simbolo_tick, est.vetos_tick)
    criterios["veredicto_muda"] = (
        criterios["simbolo_valido"] != criterios["simbolo_valido_tick"]
    )
    # Ticks em que o estado seria tirânico pela regra nova
    # (ISC >= 0,85 E JSDrc < 0,113), na trajetória por tick: os
    # vetos por tick têm de ser exactamente estes ticks — é o
    # cheque de consistência entre a trajetória e o portão.
    ticks_tiranicos = [
        t["tick"]
        for t in trajetoria
        if t["isc_local"] >= 0.85
        and t["jsd_richclub"] is not None
        and t["jsd_richclub"] < JSD_RC_ESTADO
    ]
    ticks_tiranicos_028 = [
        t["tick"]
        for t in trajetoria
        if t["isc_local"] >= 0.85
        and t["jsd_richclub"] is not None
        and t["jsd_richclub"] < JSD_ESTADO
    ]
    criterios["sora_amplificou"] = agir_sora.contador["arestas"] > 0
    criterios["limiar_0.28_sem_reescala_dispararia"] = len(ticks_tiranicos_028) > 0
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
        "variante": "vigilância por tick (rich-club k=4, portão de estado em cada tick)",
        "semente": semente,
        "ticks": n_ticks,
        "pesos_finais": pesos_finais,
        "alavanca": {
            "nome": "vigilância por tick no portão de estado rich-club",
            "richclub_k": k,
            "jsd_rc_estado": JSD_RC_ESTADO,
            "jsd_rc_uniforme": JSD_RC_UNIFORME,
            "jsd_estado_sem_reescala": JSD_ESTADO,
            "min_arestas_jsd": MIN_ARESTAS_JSD,
            "fator_amplificacao": fator_amplificacao,
            "fator_decaimento": fator_decaimento,
            "piso_decaimento": piso,
            "lira": "força total (sem escala) — como no veto-estado",
            "total_decaimentos": total_decaimentos,
            "acoes_amplificadoras": agir_sora.contador["acoes"],
            "total_amplificacoes": agir_sora.contador["arestas"],
        },
        "checkpoints": checkpoints,
        "trajetoria": trajetoria,
        "ticks_tiranicos": ticks_tiranicos,
        "ticks_tiranicos_028": ticks_tiranicos_028,
        "comparacao": comparacao,
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


def sondar_vigilia_tick(
    fatores=(1.00, 1.05, 1.10, 1.20, 1.50),
    semente=pc.SEMENTE,
    fator_decaimento=FATOR_DECAIMENTO,
):
    """Sonda de dose-resposta: corre a variante em cada fator de
    amplificação (decaimento fixo em 0,95, como na Sora e na
    rich-club) e devolve, por fator, se o Símbolo se formou, os
    vetos por tentativa, por estado (checkpoint) e por tick, o
    primeiro veto de cada portão, os dois veredictos de validade
    (checkpoint e tick) e se o veredicto muda, os ticks tirânicos,
    o Gini final, os JSDs mínimo e final (antigo e novo), o VarPn
    final e o total de amplificações. A pergunta que a sonda
    responde: a vigilância por tick apanha alguma coisa que o
    checkpoint não apanha — e muda algum veredicto?"""
    linhas = []
    for fator in fatores:
        rel = rodar_party_causal_vigilia_tick(
            semente=semente, fator_amplificacao=fator, fator_decaimento=fator_decaimento
        )
        final = rel["checkpoints"][-1] if rel["checkpoints"] else {}
        linhas.append(
            {
                "fator": fator,
                "simbolo_tick": rel["eventos"]["simbolo_tick"],
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
                "ticks_tiranicos_028": list(rel["ticks_tiranicos_028"]),
                "gini_final": final.get("gini"),
                "jsd_ordenado_min": rel["jsd_ordenado_min"],
                "jsd_ordenado_min_tick": rel["jsd_ordenado_min_tick"],
                "jsd_ordenado_final": rel["jsd_ordenado_final"],
                "jsd_richclub_min": rel["jsd_richclub_min"],
                "jsd_richclub_min_tick": rel["jsd_richclub_min_tick"],
                "jsd_richclub_final": rel["jsd_richclub_final"],
                "varpn_final": final.get("var_ponderada_normalizada"),
                "isc_final": final.get("isc_local"),
                "arestas_no_piso": final.get("arestas_no_piso"),
                "total_amplificacoes": rel["alavanca"]["total_amplificacoes"],
                "acoes_amplificadoras": rel["alavanca"]["acoes_amplificadoras"],
            }
        )
    return linhas


def imprimir_relatorio(rel):
    """Tabela da variante + sonda de dose-resposta + comparação
    dos dois portões (tick vs checkpoint) na mesma corrida."""
    print("Isekai Zero — A Party Causal: variante VIGILÂNCIA POR TICK (rich-club k=4)")
    print(f"semente={rel['semente']}  ticks={rel['ticks']}  "
          f"fator_amplificacao={rel['alavanca']['fator_amplificacao']}  "
          f"fator_decaimento={rel['alavanca']['fator_decaimento']}  piso={rel['alavanca']['piso_decaimento']}  "
          f"jsd_rc_estado={rel['alavanca']['jsd_rc_estado']}  (0,28 sem reescala = {rel['alavanca']['jsd_estado_sem_reescala']})")
    print("tick | arest | ISC   | VarPn | ISCaux | Gini  | λ₂    | MIP   | JSDp  | JSDord | JSDrc  | VetT | VetE | VetK | Piso | Ampl | Símbolo")
    for c in rel["checkpoints"]:
        print(
            f"{c['tick']:>4} | {c['n_arestas']:>5} | {c['isc_local']:.3f} | "
            f"{c['var_ponderada_normalizada']:.3f} | {c['isc_aux']:.3f} | "
            f"{c['gini']:.3f} | {c['lambda2']:.3f} | {c['mip_corte_min']:.3f} | "
            f"{c['jsd_pesos'] if c['jsd_pesos'] is not None else '-':>5} | "
            f"{c['jsd_ordenado'] if c['jsd_ordenado'] is not None else '-':>6} | "
            f"{c['jsd_richclub'] if c['jsd_richclub'] is not None else '-':>6} | "
            f"{c['vetos']:>4} | {c['vetos_estado']:>4} | {c['vetos_tick']:>4} | {c['arestas_no_piso']:>4} | "
            f"{c['amplificacoes']:>4} | {'SIM' if c['simbolo'] else 'não'}"
        )
    ev = rel["eventos"]
    print(f"Símbolo formado no tick: {ev['simbolo_tick']}")
    print(f"Ren seguiu o verdadeiro fraco: {ev['ren_verdadeiro']}x (falso: {ev['ren_falso']}x)")
    print(f"Vetos por tentativa: {len(ev['vetos'])} -> {ev['vetos']}")
    print(f"Vetos por estado (checkpoint): {len(ev['vetos_estado'])} -> {[v['tick'] for v in ev['vetos_estado']]}")
    print(f"Vetos por estado (tick): {len(ev['vetos_tick'])} -> {[v['tick'] for v in ev['vetos_tick']]}")
    print(f"Comparação: {rel['comparacao']}")
    print(f"Ticks tirânicos rich-club (trajetória por tick): {rel['ticks_tiranicos']}")
    print(f"Ticks tirânicos com 0,28 sem reescala: {rel['ticks_tiranicos_028']}")
    print(f"Depósitos por agente: {ev['depositos_por_agente']}")
    print(f"Amplificações da Sora: {rel['alavanca']['total_amplificacoes']} arestas em "
          f"{rel['alavanca']['acoes_amplificadoras']} ações")
    print(f"JSD rich-club: mínimo {rel['jsd_richclub_min']} (tick {rel['jsd_richclub_min_tick']}), "
          f"final {rel['jsd_richclub_final']}; JSD ordenado: mínimo {rel['jsd_ordenado_min']} "
          f"(tick {rel['jsd_ordenado_min_tick']}), final {rel['jsd_ordenado_final']}; "
          f"cruzamentos: {rel['cruzamentos']}")
    print(f"Critérios: {rel['criterios']}")
    print()
    print("Sonda de dose-resposta (fator -> Símbolo / vetos tent. / vetos estado / vetos tick / 1º veto tick / 1º veto ckpt / válido ckpt / válido tick / veredicto muda / Gini final / JSDrc mín / JSDrc final / VarPn final):")
    for linha in sondar_vigilia_tick():
        print(
            f"  {linha['fator']:.2f} -> tick {linha['simbolo_tick']} / "
            f"{linha['vetos_tentativa']} tent. / {linha['vetos_estado']} estado / "
            f"{linha['vetos_tick']} tick / 1º tick {linha['primeiro_veto_tick']} / "
            f"1º ckpt {linha['primeiro_veto_checkpoint']} / válido ckpt {linha['simbolo_valido']} / "
            f"válido tick {linha['simbolo_valido_tick']} / muda {linha['veredicto_muda']} / "
            f"Gini {linha['gini_final']} / JSDrc mín {linha['jsd_richclub_min']} (tick {linha['jsd_richclub_min_tick']}) / "
            f"JSDrc final {linha['jsd_richclub_final']} / VarPn {linha['varpn_final']} / amplificações {linha['total_amplificacoes']}"
        )


if __name__ == "__main__":
    imprimir_relatorio(rodar_party_causal_vigilia_tick())
