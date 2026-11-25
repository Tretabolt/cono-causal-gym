"""Isekai Zero — A Party Causal: variante PROTÓTIPO DE TIRANIA DE RICH-CLUB.

Reutiliza a variante SORA A AMPLIFICAR (party_causal_sora.py) sem a
alterar — a mesma semente, os mesmos 40 ticks, o mesmo decaimento
(0,95), a mesma Lira com força total, o mesmo portão de veto por
tentativa da TIRANIA (JSD ordenado < 0,18) e a mesma amplificação
da Sora — e troca UMA coisa: a medida de concentração no portão
de ESTADO.

## O problema que esta variante ataca

A Sora provou que o JSD ordenado é CEGO à tirania de hub: a 1,50
o hub forma-se de facto (as quatro arestas da Sora em 0,95, as
outras seis em 0,26–0,43) e o Símbolo forma-se no tick 17, mas o
JSD ordenado na fase densa SOBE com o fator (0,30 -> 0,41) — a
amplificação afasta o cluster do limiar do veto, não o aproxima.
O motivo é o protótipo: a Tirania é UM rastro dominante
[0,9, 0,011, ...], e um hub de quatro arestas fortes está LONGE
dele em JSD. A pergunta que ficou foi: com um protótipo que
DESCREVA um hub — k arestas dominantes em vez de uma só — o
veto por estado dispara finalmente sobre um Símbolo vivo?

## O protótipo de rich-club (definição do CENÁRIO, não canónica)

    prototipo_richclub(n, k) = [0,9/k]*k + [0,1/(n-k)]*(n-k)

k arestas dominantes partilham os 0,9 do protótipo de Tirania em
partes iguais; as restantes n-k partilham os 0,1. É o análogo
fiel do protótipo de um só rastro — a mesma repartição 0,9/0,1,
só que o domínio é partilhado por k arestas em vez de uma. Com
k = 4 (o hub da Sora tem QUATRO arestas incidentes) e n = 10
(o cluster denso tem 10 arestas):

    [0,225, 0,225, 0,225, 0,225, 0,0167, 0,0167, 0,0167, 0,0167,
     0,0167, 0,0167]   (soma 1,0)

Consistência: com k = 1 o protótipo rich-club É o protótipo de
Tirania ([0,9] + [0,1/(n-1)]*(n-1)) — a medida nova contém a
antiga como caso particular, não a contradiz. O JSD rich-club
é o JSD entre os pesos ORDENADOS por ordem decrescente e este
protótipo — a mesma ordenação da TIRANIA, só o protótipo muda.

## O limiar tem de ser reescalado — e o porquê está medido

O limiar do portão de estado (0,28) NÃO pode ser transportado
tal e qual para a medida nova: o protótipo rich-club está muito
mais perto do uniforme do que o protótipo de um só rastro, por
isso a escala da JSD encolhe:

    JSD(uniforme_10, tirania_1)    = 0,5310
    JSD(uniforme_10, richclub_4)   = 0,2141   (< 0,28!)

Com o limiar 0,28 sem reescala, até um cluster PERFEITAMENTE
UNIFORME seria "tirânico" (0,2141 < 0,28) — o portão dispararia
sempre, incluindo no controlo, e não mediria nada. O limiar é
por isso reescalado na mesma proporção em que a escala
encolheu, mantendo a POSIÇÃO RELATIVA do limiar antigo — 0,28
está a 52,7% do caminho entre o protótipo (0,0) e o uniforme
(0,5310) na escala antiga:

    JSD_RC_ESTADO = 0,28 x 0,2141 / 0,5310 = 0,113

Verificação independente: o ponto médio entre o protótipo
rich-club (0,0) e o uniforme (0,2141) é 0,107 — o mesmo
bairro. O 0,28 sem reescala continua a ser reportado (o que
ele dispararia), para a comparação ser limpa: se o portão
disparar com 0,113, é o hub que o dispara — não a escala.

## O resultado (resumo — ver os testes para os números)

A hipótese CONFIRMA-SE — e é a primeira vez na série que o veto
por estado dispara sobre um Símbolo vivo. A 1,10 (omissão), o
portão rich-club dispara 2 vezes (checkpoints 30 e 40): o Símbolo
forma-se no tick 28 e é INVÁLIDO (simbolo_valido False), porque
foi reclamado num estado tirânico. Os ticks tirânicos são 23–40
sem interrupção — concentração e integração COINCIDEM desta vez,
do tick em que o ISC cruza 0,85 até ao fim. No mesmo estado, as
duas medidas discordam de frente: no tick 40, JSDord 0,4286
(limpo pela medida antiga) contra JSDrc 0,0812 (tirânico pela
nova). A 1,50 a janela abre no próprio tick do Símbolo (17) e
fica aberta até 40; a 1,05 e 1,20 abre no tick 20. Os critérios
da base continuam a passar em todos os níveis (Ren 26x o
verdadeiro fraco, 0–2x o falso; sucesso parcial e completo).

Duas honestidades. Primeira: o controlo (1,00, sem amplificação)
é TRANSITORIAMENTE tirânico pela medida nova — ticks 32–36, com
ISC 0,90 e JSDrc ~0,10 — mas o portão por checkpoint NÃO o
apanha (no checkpoint 30 o ISC ainda é 0,80; no 40 o JSDrc já
recuperou para 0,1232). A trajetória por tick vê-o; o portão
não. Segunda: o limiar 0,113 vive num bairro concorrido — o
controlo na fase densa anda a 0,10–0,12, mesmo sem hub, porque
a medida vê a dominância Sora->Ren (0,95) mesmo sem
amplificação. A separação hub/controlo existe (0,04–0,08 no hub
contra 0,10–0,12 no controlo) mas é fina; e o 0,28 sem reescala
dispararia em todo o lado, incluindo o controlo (ticks 32–40) —
a prova de que a reescala não era opcional. O Gini NÃO vê o hub:
final 0,2568 a 1,50 (< 0,30) e máximo 0,3007 a 1,10 — a
saturação uniformiza-o, como na Sora. O próximo passo que o
resultado sugere: vigilância por tick (para o portão apanhar
transientes como o do controlo) ou um k que varie com n.
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

# O hub da Sora tem 4 arestas incidentes — é o k do protótipo.
RICHCLUB_K = 4


def prototipo_richclub(n, k=RICHCLUB_K):
    """Protótipo de Tirania de rich-club (definição do CENÁRIO,
    não canónica): k arestas dominantes partilham 0,9 em partes
    iguais; as restantes n-k partilham 0,1. Soma 1,0. Com k = 1
    reproduz exatamente prototipo_tirania(n) — a medida nova
    contém a antiga como caso particular."""
    if n < 2 or k < 1 or k >= n:
        raise ValueError("rich-club precisa de 1 <= k < n, n >= 2")
    return [0.9 / k] * k + [0.1 / (n - k)] * (n - k)


def jsd_pesos_richclub(grafo, k=RICHCLUB_K):
    """JSD_pesos rich-club (definição da VARIANTE, não canónica):
    os pesos das arestas por ordem DECRESCENTE antes da JSD com
    o protótipo rich-club. É a medida de concentração de hub:
    0,0 para um hub perfeito (k arestas a 0,9/k, o resto a
    0,1/(n-k)), JSD_RC_UNIFORME para uniforme. None com < 2
    arestas, como o JSD ordenado da TIRANIA."""
    pesos = grafo.pesos()
    if len(pesos) < 2:
        return None
    return pc.jsd_bits(sorted(pesos, reverse=True), prototipo_richclub(len(pesos), k))


# Limiar DO CENÁRIO para o veto por estado com a medida rich-club
# (não canónico): o 0,28 do sucesso do Dan, reescalado na proporção
# em que a escala da JSD encolhe ao trocar o protótipo (ver o
# docstring). Calculado, não chutado — os testes fixam-no.
JSD_RC_ESTADO = round(
    JSD_ESTADO
    * pc.jsd_bits([0.1] * 10, prototipo_richclub(10, RICHCLUB_K))
    / pc.jsd_bits([0.1] * 10, pc.prototipo_tirania(10)),
    3,
)
# Referência da escala nova: JSD(uniforme_10, richclub_10).
JSD_RC_UNIFORME = round(
    pc.jsd_bits([0.1] * 10, prototipo_richclub(10, RICHCLUB_K)), 4
)


def _vigiar_estado_rc(est, jsd_rc, jsd_ord):
    """Vigilância de ESTADO no checkpoint, com a medida rich-club:
    se o cluster passa a regra canónica de Símbolo (ISC_Local
    >= 0,85) mas o JSD rich-club está abaixo do limiar reescalado
    do cenário (JSD_RC_ESTADO), regista um evento de veto por
    estado e devolve True. É um observador, não um portão — não
    bloqueia nada. O JSD ordenado antigo fica registado no evento
    lado a lado, para a comparação das duas medidas ser feita no
    mesmo estado. Com < 5 arestas, ou sem JSD, não há sinal:
    devolve False sem registar."""
    sub = est.subgrafo_party()
    if sub.n_arestas() < MIN_ARESTAS_JSD or jsd_rc is None:
        return False
    rel = pc.avaliar_cluster(sub, "SIMBOLO_PARTY_001")
    if rel["isc_local"] >= 0.85 and jsd_rc < JSD_RC_ESTADO:
        est.vetos_estado.append(
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
            }
        )
        est.eventos.append(
            (est.tick, "VETO POR ESTADO rich-club (cluster tirânico)", round(jsd_rc, 4))
        )
        return True
    return False


def rodar_party_causal_richclub(
    semente=pc.SEMENTE,
    n_ticks=pc.N_TICKS,
    fator_amplificacao=FATOR_AMPLIFICACAO,
    fator_decaimento=FATOR_DECAIMENTO,
    piso=PISO_DECAIMENTO,
    k=RICHCLUB_K,
):
    """Corre a variante (40 ticks, checkpoint a cada 10, vigilância
    de estado rich-club em cada checkpoint e no fim) e devolve o
    relatório completo. A base não é alterada: o remendo de
    _tentar_simbolo é reposto no finally, e a corrida base
    continua a dar os mesmos números depois disto. Com
    fator_amplificacao = 1,00 a variante é o veto-estado exato
    com a medida trocada — é o controlo da sonda. A trajetória
    por tick regista as DUAS medidas (JSD ordenado antigo e JSD
    rich-club novo) e o Gini no mesmo estado: é ela que prova se
    concentração e integração coincidem desta vez — ou não — e
    com que medida."""
    est = pc._Estado(semente)
    est.vetos = []
    est.vetos_estado = []
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
                # O 0,28 sem reescala na medida nova: o cruzamento
                # regista-se, mas é o artefacto da escala — o
                # uniforme já está abaixo dele (0,2141).
                if jsd_rc < JSD_ESTADO and "rc_0.28_sem_reescala" not in cruzamentos:
                    cruzamentos["rc_0.28_sem_reescala"] = tick
            if jsd_ord is not None:
                if jsd_ord_min is None or jsd_ord < jsd_ord_min:
                    jsd_ord_min, jsd_ord_min_tick = jsd_ord, tick
            if tick % pc.CHECKPOINT == 0:
                # A vigilância corre antes do checkpoint, para o
                # checkpoint contar o veto por estado deste tick.
                _vigiar_estado_rc(est, jsd_rc, jsd_ord)
                c = _checkpoint_tyranny(est, jsd_ord)
                c["jsd_richclub"] = round(jsd_rc, 4) if jsd_rc is not None else None
                c["arestas_no_piso"] = _arestas_no_piso(est, piso)
                c["vetos_estado"] = len(est.vetos_estado)
                c["amplificacoes"] = agir_sora.contador["arestas"]
                checkpoints.append(c)
                if est.simbolo_tick is not None:
                    pc._tentar_meta_simbolo(est, f"checkpoint tick {tick}")
        # Avaliação final: o tick 40 já é checkpoint (40 % 10 == 0).
        # Só se vigia o estado final fora dos checkpoints quando o
        # último tick não é um checkpoint — sem dupla contagem.
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
    # Critérios da variante (a vigilância de estado rich-club).
    criterios["veto_estado_disparou"] = len(est.vetos_estado) > 0
    criterios["cluster_tiranico"] = len(est.vetos_estado) > 0
    criterios["simbolo_valido"] = _simbolo_valido(est.simbolo_tick, est.vetos_estado)
    # Ticks em que o estado seria tirânico pela regra nova
    # (ISC >= 0,85 E JSDrc < 0,113), na trajetória por tick: se
    # esta lista está vazia, o negativo não depende da
    # granularidade dos checkpoints. E a mesma lista com o 0,28
    # sem reescala — o que o limiar antigo dispararia na medida
    # nova (o artefacto da escala, documentado no docstring).
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
        "variante": "protótipo de tirania de rich-club (k=4) + vigilância de estado",
        "semente": semente,
        "ticks": n_ticks,
        "pesos_finais": pesos_finais,
        "alavanca": {
            "nome": "protótipo de tirania de rich-club no portão de estado",
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


def sondar_richclub(
    fatores=(1.00, 1.05, 1.10, 1.20, 1.50),
    semente=pc.SEMENTE,
    fator_decaimento=FATOR_DECAIMENTO,
):
    """Sonda de dose-resposta: corre a variante em cada fator de
    amplificação (decaimento fixo em 0,95, como na Sora) e devolve,
    por fator, se o Símbolo se formou, os vetos por tentativa e
    por estado (medida rich-club, limiar reescalado), os ticks
    tirânicos pela regra nova e pelo 0,28 sem reescala, o Gini
    final, os JSDs mínimo e final (antigo e novo), o VarPn final
    e o total de amplificações. A pergunta que a sonda responde:
    com um protótipo que descreve o hub, o veto por estado
    dispara num Símbolo vivo — e a que nível?"""
    linhas = []
    for fator in fatores:
        rel = rodar_party_causal_richclub(
            semente=semente, fator_amplificacao=fator, fator_decaimento=fator_decaimento
        )
        final = rel["checkpoints"][-1] if rel["checkpoints"] else {}
        linhas.append(
            {
                "fator": fator,
                "simbolo_tick": rel["eventos"]["simbolo_tick"],
                "vetos_tentativa": len(rel["eventos"]["vetos"]),
                "vetos_estado": len(rel["eventos"]["vetos_estado"]),
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
    das duas medidas no mesmo estado."""
    print("Isekai Zero — A Party Causal: variante RICH-CLUB (k=4)")
    print(f"semente={rel['semente']}  ticks={rel['ticks']}  "
          f"fator_amplificacao={rel['alavanca']['fator_amplificacao']}  "
          f"fator_decaimento={rel['alavanca']['fator_decaimento']}  piso={rel['alavanca']['piso_decaimento']}  "
          f"jsd_rc_estado={rel['alavanca']['jsd_rc_estado']}  (0,28 sem reescala = {rel['alavanca']['jsd_estado_sem_reescala']})")
    print("tick | arest | ISC   | VarPn | ISCaux | Gini  | λ₂    | MIP   | JSDp  | JSDord | JSDrc  | VetT | VetE | Piso | Ampl | Símbolo")
    for c in rel["checkpoints"]:
        print(
            f"{c['tick']:>4} | {c['n_arestas']:>5} | {c['isc_local']:.3f} | "
            f"{c['var_ponderada_normalizada']:.3f} | {c['isc_aux']:.3f} | "
            f"{c['gini']:.3f} | {c['lambda2']:.3f} | {c['mip_corte_min']:.3f} | "
            f"{c['jsd_pesos'] if c['jsd_pesos'] is not None else '-':>5} | "
            f"{c['jsd_ordenado'] if c['jsd_ordenado'] is not None else '-':>6} | "
            f"{c['jsd_richclub'] if c['jsd_richclub'] is not None else '-':>6} | "
            f"{c['vetos']:>4} | {c['vetos_estado']:>4} | {c['arestas_no_piso']:>4} | "
            f"{c['amplificacoes']:>4} | {'SIM' if c['simbolo'] else 'não'}"
        )
    ev = rel["eventos"]
    print(f"Símbolo formado no tick: {ev['simbolo_tick']}")
    print(f"Ren seguiu o verdadeiro fraco: {ev['ren_verdadeiro']}x (falso: {ev['ren_falso']}x)")
    print(f"Vetos por tentativa: {len(ev['vetos'])} -> {ev['vetos']}")
    print(f"Vetos por estado (rich-club): {len(ev['vetos_estado'])} -> {ev['vetos_estado']}")
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
    print("Sonda de dose-resposta (fator -> Símbolo / vetos tent. / vetos estado RC / ticks tirânicos RC / Gini final / JSDrc mín / JSDord mín / VarPn final):")
    for linha in sondar_richclub():
        print(
            f"  {linha['fator']:.2f} -> tick {linha['simbolo_tick']} / "
            f"{linha['vetos_tentativa']} tent. / {linha['vetos_estado']} estado / "
            f"{linha['ticks_tiranicos']} / Gini {linha['gini_final']} / "
            f"JSDrc mín {linha['jsd_richclub_min']} (tick {linha['jsd_richclub_min_tick']}) / "
            f"JSDrc final {linha['jsd_richclub_final']} / JSDord final {linha['jsd_ordenado_final']} / "
            f"VarPn {linha['varpn_final']} / amplificações {linha['total_amplificacoes']}"
        )


if __name__ == "__main__":
    imprimir_relatorio(rodar_party_causal_richclub())
