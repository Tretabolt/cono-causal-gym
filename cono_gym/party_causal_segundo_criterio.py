"""Isekai Zero — A Party Causal: variante SEGUNDO CRITÉRIO.

Reutiliza a variante K VARIÁVEL COM n
(party_causal_k_variavel.py) sem a alterar — a mesma semente, os
mesmos 40 ticks, o mesmo decaimento (0,95), a mesma Lira com
força total, o mesmo portão de veto por tentativa da TIRANIA
(JSD ordenado < 0,18), a mesma amplificação da Sora, a mesma
vigilância por tick lado a lado com o portão por checkpoint, o
mesmo JSD rich-club k(n) com o limiar recalibrado por n — e
troca UMA coisa: o portão de estado passa a exigir DOIS
critérios em CONJUNÇÃO. O veto só dispara quando as duas
medidas concordam: JSD rich-club k(n) abaixo do seu limiar E
a quota dos top-k acima do seu limiar. O penhasco, o outro
candidato, fica registado lado a lado na trajetória — testado,
não usado como portão (ver abaixo).

## O problema que esta variante ataca

A k variável fechou o veredicto do controlo mas não o bairro:
a folga mínima do JSD rich-club k(n) acima do limiar na fase
densa do controlo continua a ser 0,003 (tick 37, 0,1159 contra
0,1129) — o limiar passou para lá do transiente e o cluster
continua a roçar nele, agora por cima. A medida sozinha, com k
fixo ou variável, não separa o hub do controlo com margem. A
pergunta que ficou foi: um SEGUNDO CRITÉRIO, de outro tipo —
não uma variação do mesmo JSD — separa os dois estados com
margem? Dois candidatos foram medidos nas trajetórias reais
antes de escolher (diagnóstico em /tmp, não no gym):

(a) QUOTA DOS TOP-k — Q = soma dos k(n) pesos mais fortes /
soma de todos os pesos do cluster. No estado hub (a 1,50, as
quatro arestas da Sora a 0,95 e as outras seis a 0,26–0,43) a
quota dos top-4 ronda 0,65; na fase densa do controlo os pesos
são mais uniformes e a quota fica a 0,49–0,59.

(b) PENHASCO — R = w_k / w_{k+1}, o rácio entre a k-ésima
aresta mais forte e a seguinte. No hub a 4ª aresta (0,95)
contra a 5ª (0,43) dá ~2,2; no controlo o penhasco é ~1,0–1,2.

A escolha, com números: a quota separa, o penhasco não. O
penhasco calibrado na mesma posição relativa (ver abaixo) tem
limiar 3,42–3,73 — e o penhasco real do hub nunca passa de
2,65 em nenhum nível da sonda: o protótipo idealiza um
penhasco de 13,5 (0,9/4 contra 0,1/6) que o hub real, com as
suas seis arestas a 0,26–0,43, nunca aproxima. Pior: a 1,50,
ticks 19–24, o penhasco k = 3 é exactamente 1,0 — o hub tem
QUATRO arestas fortes mas k(9) = 3, por isso w_3 = w_4 = 0,95
e não há penhasco nenhum para medir. O penhasco é cego por
construção quando o hub tem mais arestas fortes do que k. A
quota, pelo contrário, vê o hub em todos os níveis — e o
controlo fica limpo por ela com folga mínima 0,0433 (tick 37),
14x a folga do JSD (0,003).

## A calibração do limiar da quota (definição do CENÁRIO, não canónica)

A mesma posição relativa do 0,28 antigo, na escala da quota.
Na escala da quota, o protótipo (rich-club perfeito) tem Q =
0,9 — os top-k partilham 0,9 do peso — e o uniforme tem Q =
k/n. O 0,28 está a r(n) = 0,28 / JSD(uniforme_n, tirania_1(n))
do caminho entre o protótipo e o uniforme na escala do JSD de
um só rastro; o limiar da quota fica à mesma fracção do
caminho entre o protótipo e o uniforme na escala da quota:

    limiar_quota(n) = 0,9 - r(n) x (0,9 - k(n)/n)

Medido (n = 5..10, o intervalo que o cluster percorre):

    n  | k(n) | Q(uniforme) | r(n)   | limiar_quota(n)
    5  |  2   |    0,4000   | 0,7048 |     0,5476
    6  |  2   |    0,3333   | 0,6403 |     0,5372
    7  |  3   |    0,4286   | 0,5979 |     0,6182
    8  |  3   |    0,3750   | 0,5676 |     0,6020
    9  |  3   |    0,3333   | 0,5450 |     0,5912
    10 |  4   |    0,4000   | 0,5273 |     0,6363

O limiar tem a mesma forma de dente-de-serra do limiar do JSD
(sobe enquanto k fica fixo e n cresce, cai quando k
incrementa). O limiar fica sempre entre o uniforme e o
protótipo (k/n < limiar < 0,9) em todos os n — a mesma
condição que levou ao 0,113: se ficasse abaixo do uniforme,
até um cluster uniforme seria "tirânico".

O limiar do penhasco, registado para comparação, usa a mesma
posição relativa em escala log — o penhasco do protótipo é
9(n-k)/k e o do uniforme é 1, por isso limiar_penhasco(n) =
(9(n-k)/k)^(1-r(n)): 2,1565 / 2,8281 / 2,7164 / 3,2247 /
3,7255 / 3,4222 para n = 5..10. O Gini continua fora do
portão — não vê o hub (final 0,2568 a 1,50), como na Sora e
na rich-club — e fica só como monitor secundário, como antes.

## O resultado (resumo — ver os testes para os números)

A hipótese confirma-se A MEIO — e a metade que falha é a
instrutiva. O controlo separa-se COM MARGEM pelo segundo
critério: na fase densa a quota fica sempre abaixo do limiar,
com folga mínima 0,0433 (tick 37, 0,593 contra 0,6363) — 14x
a folga do JSD (0,003). A conjunção não inventa vetos no
controlo: 0 vetos por tick e 0 por checkpoint a 1,00, Símbolo
válido por ambos os portões, como na k variável.

Mas o segundo critério DESFAZ vetos nos níveis amplificados.
A 1,05 a quota nunca dispara na fase densa (máximo 0,5687
contra limiar 0,5912, folga mínima 0,0225) — a conjunção tem
0 vetos e o Símbolo (tick 25) passa a ser VÁLIDO, quando sob
o JSD sozinho era inválido. A 1,50 o Símbolo já não nasce
tirânico: o primeiro veto por tick reclamado é o tick 25 (o
primeiro tick a n = 10 com a quota acima do limiar), não o 17;
só há 1 veto por checkpoint (tick 30) em vez de 3 — o tick 40
escapa por 0,0001 (quota 0,6362 contra limiar 0,6363). A 1,10
e a 1,20 o Símbolo continua a nascer tirânico (28 e 21), mas
a janela fica INTERMITENTE: a 1,10 a conjunção dispara em
28–32 e 36–40, com buracos em 33–35; a 1,20 dispara em 20,
21, 27 e 29–40, com buracos em 22–26 e 28. Os critérios da
base continuam a passar em todos os níveis (Ren 26–28x o
verdadeiro fraco, 0–2x o falso; sucesso parcial e completo).

A honestidade que o resultado impõe: a quota tem o SEU
próprio bairro concorrido, noutros ticks. A 1,10 a folga
mínima da quota é 0,0021 (tick 27) — mais fina do que a do
JSD no controlo. A 1,50 o tick final fica abaixo do limiar
por 0,0001. A quota do hub oscila à volta do limiar (0,62–
0,69 a n = 10) em vez de se afastar dele: a separação que a
quota compra no controlo (0,0433) não existe do lado do hub.
E a quota é alta também na fase esparsa (máxima 0,6046 a
1,05 e 0,6914 a 1,50, ambas no tick 11) — é a condição ISC
>= 0,85 que impede o portão de disparar aí, não a quota.

O penhasco, como previsto, nunca dispara em nenhum nível
(máximo 2,646 a 1,20 contra limiar 3,4222) e a 1,50, ticks
19–24, é exactamente 1,0. O próximo passo que o resultado
sugere: calibrar o portão para a FOLGA, não para o
veredicto — exigir uma folga mínima dos dois lados — ou
aceitar que o Símbolo a 1,05 não é tirânico pela evidência
da quota, e que a intermitência é a assinatura de um hub que
oscila, não de um portão que falha.
"""

import math

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
    jsd_pesos_richclub,
)
from .party_causal_k_variavel import (
    TABELA_CALIBRACAO,
    jsd_pesos_richclub_k,
    k_variavel,
    limiar_estado_k,
    prototipo_richclub_k,
)


def _posicao_relativa(n):
    """r(n) = 0,28 / JSD(uniforme_n, tirania_1(n)) — a fracção
    do caminho entre o protótipo e o uniforme a que o 0,28
    antigo está, na escala do JSD de um só rastro, para esse n.
    É a mesma posição relativa que a recalibração do 0,113 e
    do limiar k(n) preservam."""
    if n < 2:
        raise ValueError("a posição relativa precisa de n >= 2")
    u = [1.0 / n] * n
    return JSD_ESTADO / pc.jsd_bits(u, pc.prototipo_tirania(n))


def quota_topk(grafo):
    """Quota dos top-k (definição da VARIANTE, não canónica):
    soma dos k(n) pesos mais fortes / soma de todos os pesos do
    cluster, com k(n) = ceil(n/3) — o mesmo k do protótipo
    rich-club. 0,9 para um hub perfeito (os top-k partilham os
    0,9 do protótipo), k/n para um cluster uniforme. É uma
    evidência de concentração de outro tipo que o JSD: não
    compara distribuições, mede a fracção do peso que o clube
    segura. None com < 2 arestas, como o JSD rich-club k(n)."""
    pesos = sorted(grafo.pesos(), reverse=True)
    if len(pesos) < 2:
        return None
    total = sum(pesos)
    if total <= 0:
        return None
    return sum(pesos[:k_variavel(len(pesos))]) / total


def penhasco(grafo):
    """Penhasco (definição da VARIANTE, não canónica): w_k /
    w_{k+1}, o rácio entre a k-ésima aresta mais forte e a
    seguinte, com k(n) = ceil(n/3). 9(n-k)/k para um hub
    perfeito, 1,0 para um cluster uniforme. Registado para
    comparação — NÃO é portão (ver o docstring: calibrado na
    mesma posição relativa, nunca dispara). None com < 2
    arestas; infinito se a (k+1)-ésima aresta pesar 0."""
    pesos = sorted(grafo.pesos(), reverse=True)
    if len(pesos) < 2:
        return None
    k = k_variavel(len(pesos))
    seguinte = pesos[k]
    if seguinte <= 0:
        return float("inf")
    return pesos[k - 1] / seguinte


def limiar_quota(n):
    """Limiar da quota por n (definição do CENÁRIO, não
    canónica): 0,9 - r(n) x (0,9 - k(n)/n) — a mesma posição
    relativa do 0,28 antigo, na escala da quota. A n = 10 dá
    0,6363. Calculado, não chutado — os testes fixam-no."""
    if n < 2:
        raise ValueError("o limiar da quota precisa de n >= 2")
    return round(0.9 - _posicao_relativa(n) * (0.9 - k_variavel(n) / n), 4)


def limiar_penhasco(n):
    """Limiar do penhasco por n (definição do CENÁRIO, não
    canónica): (9(n-k)/k)^(1-r(n)) — a mesma posição relativa,
    em escala log (o penhasco é multiplicativo: o uniforme é 1
    e o protótipo é 9(n-k)/k). A n = 10 dá 3,4222. Calculado,
    não chutado — os testes fixam-no."""
    if n < 2:
        raise ValueError("o limiar do penhasco precisa de n >= 2")
    k = k_variavel(n)
    return round((9.0 * (n - k) / k) ** (1 - _posicao_relativa(n)), 4)


# Tabela de calibração (n = 5..10, o intervalo que o cluster
# percorre): k(n), o limiar do JSD rich-club k(n) e os dois
# limiares novos — calculados, não chutados. Os testes
# fixam-nos.
TABELA_CALIBRACAO_2C = {
    n: (
        k_variavel(n),
        limiar_estado_k(n),
        limiar_quota(n),
        limiar_penhasco(n),
    )
    for n in range(5, 11)
}


def _vigiar_estado_2c(est, jsd_rc_k, quota, limiar, limiar_q, jsd_ord, penh, limiar_r):
    """Vigilância de ESTADO no checkpoint, com DOIS critérios em
    CONJUNÇÃO: se o cluster passa a regra canónica de Símbolo
    (ISC_Local >= 0,85) e o JSD rich-club k(n) está abaixo do
    seu limiar E a quota dos top-k está acima do seu limiar,
    regista um evento de veto por estado e devolve True. É um
    observador, não um portão — não bloqueia nada. O evento
    regista os dois critérios e o penhasco lado a lado, para a
    comparação ser feita no mesmo estado. Com < 5 arestas, ou
    sem JSD ou sem quota, não há sinal: devolve False sem
    registar."""
    sub = est.subgrafo_party()
    if sub.n_arestas() < MIN_ARESTAS_JSD or jsd_rc_k is None or quota is None:
        return False
    rel = pc.avaliar_cluster(sub, "SIMBOLO_PARTY_001")
    if rel["isc_local"] >= 0.85 and jsd_rc_k < limiar and quota >= limiar_q:
        est.vetos_estado.append(
            {
                "tick": est.tick,
                "isc_local": round(rel["isc_local"], 4),
                "var_ponderada_normalizada": round(
                    rel["var_ponderada_normalizada"], 4
                ),
                "jsd_richclub_k": round(jsd_rc_k, 4),
                "jsd_richclub": round(jsd_pesos_richclub(sub), 4),
                "jsd_ordenado": round(jsd_ord, 4) if jsd_ord is not None else None,
                "quota_topk": round(quota, 4),
                "limiar_quota": limiar_q,
                "penhasco": round(penh, 4) if penh is not None else None,
                "limiar_penhasco": limiar_r,
                "gini": round(gini(sub.pesos()), 4),
                "n_arestas": sub.n_arestas(),
                "k": k_variavel(sub.n_arestas()),
                "limiar": limiar,
                "simbolo_reclamado": est.simbolo_tick is not None,
                "simbolo_no_checkpoint": rel["simbolo"],
            }
        )
        est.eventos.append(
            (est.tick, "VETO POR ESTADO dois critérios", round(jsd_rc_k, 4))
        )
        return True
    return False


def _vigiar_estado_tick_2c(est, jsd_rc_k, quota, limiar, limiar_q, jsd_ord, penh, limiar_r):
    """Vigilância de ESTADO em CADA TICK, com os dois critérios
    em conjunção: a mesma regra do portão por checkpoint, corrida
    no fim de cada tick, com os limiares do n DESSE tick. Os
    eventos vão para est.vetos_tick, com o mesmo formato dos
    eventos por checkpoint (mais o campo "via": "tick")."""
    sub = est.subgrafo_party()
    if sub.n_arestas() < MIN_ARESTAS_JSD or jsd_rc_k is None or quota is None:
        return False
    rel = pc.avaliar_cluster(sub, "SIMBOLO_PARTY_001")
    if rel["isc_local"] >= 0.85 and jsd_rc_k < limiar and quota >= limiar_q:
        est.vetos_tick.append(
            {
                "tick": est.tick,
                "isc_local": round(rel["isc_local"], 4),
                "var_ponderada_normalizada": round(
                    rel["var_ponderada_normalizada"], 4
                ),
                "jsd_richclub_k": round(jsd_rc_k, 4),
                "jsd_richclub": round(jsd_pesos_richclub(sub), 4),
                "jsd_ordenado": round(jsd_ord, 4) if jsd_ord is not None else None,
                "quota_topk": round(quota, 4),
                "limiar_quota": limiar_q,
                "penhasco": round(penh, 4) if penh is not None else None,
                "limiar_penhasco": limiar_r,
                "gini": round(gini(sub.pesos()), 4),
                "n_arestas": sub.n_arestas(),
                "k": k_variavel(sub.n_arestas()),
                "limiar": limiar,
                "simbolo_reclamado": est.simbolo_tick is not None,
                "simbolo_no_checkpoint": rel["simbolo"],
                "via": "tick",
            }
        )
        est.eventos.append(
            (est.tick, "VETO POR ESTADO (tick) dois critérios", round(jsd_rc_k, 4))
        )
        return True
    return False


def _margens_dois_criterios(trajetoria):
    """As folgas dos DOIS critérios, na fase densa (ISC >= 0,85):
    para o JSD rich-club k(n), a profundidade máxima do veto
    (limiar - JSD, quando o JSD está abaixo) e a folga mínima
    acima do limiar (JSD - limiar, nos ticks limpos); para a
    quota, ao contrário — a profundidade máxima do veto é
    quota - limiar (quando a quota está acima) e a folga mínima
    acima do limiar é limiar - quota (nos ticks limpos). É isto
    que diz se o controlo separa COM MARGEM agora — e de que
    lado está o bairro de cada critério."""
    def resumo(densa, profundidade, folga):
        abaixo = [profundidade(t) for t in densa if profundidade(t) is not None and profundidade(t) > 0]
        acima = [folga(t) for t in densa if folga(t) is not None and folga(t) > 0]
        return {
            "profundidade_max_veto": round(max(abaixo), 4) if abaixo else None,
            "folga_min_acima": round(min(acima), 4) if acima else None,
            "n_ticks_densos": len(densa),
        }
    densa = [
        t for t in trajetoria
        if t["isc_local"] >= 0.85
        and t["jsd_richclub_k"] is not None
        and t["quota_topk"] is not None
    ]
    return {
        "jsd_richclub_k": resumo(
            densa,
            lambda t: t["limiar"] - t["jsd_richclub_k"],
            lambda t: t["jsd_richclub_k"] - t["limiar"],
        ),
        "quota_topk": resumo(
            densa,
            lambda t: t["quota_topk"] - t["limiar_quota"],
            lambda t: t["limiar_quota"] - t["quota_topk"],
        ),
    }


def rodar_party_causal_segundo_criterio(
    semente=pc.SEMENTE,
    n_ticks=pc.N_TICKS,
    fator_amplificacao=FATOR_AMPLIFICACAO,
    fator_decaimento=FATOR_DECAIMENTO,
    piso=PISO_DECAIMENTO,
):
    """Corre a variante (40 ticks, checkpoint a cada 10, vigilância
    de estado com DOIS critérios em conjunção em CADA TICK e, em
    paralelo, nos checkpoints) e devolve o relatório completo. A
    base não é alterada: o remendo de _tentar_simbolo é reposto
    no finally, e a corrida base continua a dar os mesmos
    números depois disto. Com fator_amplificacao = 1,00 a
    variante é o veto-estado exacto com o portão trocado — é o
    controlo da sonda. A trajetória por tick regista as TRÊS
    medidas (JSD ordenado antigo, JSD rich-club k(n), quota dos
    top-k e penhasco) e o Gini no mesmo estado, mais o k e os
    três limiares desse tick: é ela que prova se o controlo
    separa com margem agora — e de que lado fica o bairro de
    cada critério."""
    est = pc._Estado(semente)
    est.vetos = []
    est.vetos_estado = []
    est.vetos_tick = []
    agir = dict(pc._AGIR)
    agir_sora = _fazer_agir_sora(fator_amplificacao)
    agir["Sora"] = agir_sora
    checkpoints = []
    trajetoria = []
    jsd_rck_min = None
    jsd_rck_min_tick = None
    jsd_rc_min = None
    jsd_rc_min_tick = None
    jsd_ord_min = None
    jsd_ord_min_tick = None
    quota_max = None
    quota_max_tick = None
    penh_max = None
    penh_max_tick = None
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
                jsd_rck = jsd_pesos_richclub_k(sub)
                jsd_rc = jsd_pesos_richclub(sub)
                quota = quota_topk(sub)
                penh = penhasco(sub)
                gini_tick = gini(sub.pesos())
                k_tick = k_variavel(sub.n_arestas())
                limiar_tick = limiar_estado_k(sub.n_arestas())
                limiar_q_tick = limiar_quota(sub.n_arestas())
                limiar_r_tick = limiar_penhasco(sub.n_arestas())
            else:
                jsd_ord = jsd_rck = jsd_rc = quota = penh = gini_tick = None
                k_tick = None
                limiar_tick = None
                limiar_q_tick = None
                limiar_r_tick = None
            trajetoria.append(
                {
                    "tick": tick,
                    "n_arestas": sub.n_arestas(),
                    "k": k_tick,
                    "limiar": limiar_tick,
                    "limiar_quota": limiar_q_tick,
                    "limiar_penhasco": limiar_r_tick,
                    "isc_local": round(isc_tick, 4),
                    "jsd_ordenado": round(jsd_ord, 4) if jsd_ord is not None else None,
                    "jsd_richclub_k": round(jsd_rck, 4) if jsd_rck is not None else None,
                    "jsd_richclub": round(jsd_rc, 4) if jsd_rc is not None else None,
                    "quota_topk": round(quota, 4) if quota is not None else None,
                    "penhasco": round(penh, 4) if penh is not None else None,
                    "gini": round(gini_tick, 4) if gini_tick is not None else None,
                }
            )
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
            if quota is not None:
                if quota_max is None or quota > quota_max:
                    quota_max, quota_max_tick = quota, tick
                if quota >= limiar_q_tick and "quota_estado" not in cruzamentos:
                    cruzamentos["quota_estado"] = tick
            if penh is not None:
                if penh_max is None or penh > penh_max:
                    penh_max, penh_max_tick = penh, tick
                if penh >= limiar_r_tick and "penhasco_estado" not in cruzamentos:
                    cruzamentos["penhasco_estado"] = tick
            # A vigilância por tick corre no fim de CADA tick,
            # com os limiares do n DESSE tick.
            _vigiar_estado_tick_2c(
                est, jsd_rck, quota, limiar_tick, limiar_q_tick,
                jsd_ord, penh, limiar_r_tick,
            )
            if tick % pc.CHECKPOINT == 0:
                # A vigilância por checkpoint corre no mesmo lugar
                # da vigília, com os limiares do n DESSE checkpoint.
                _vigiar_estado_2c(
                    est, jsd_rck, quota, limiar_tick, limiar_q_tick,
                    jsd_ord, penh, limiar_r_tick,
                )
                c = _checkpoint_tyranny(est, jsd_ord)
                c["jsd_richclub_k"] = round(jsd_rck, 4) if jsd_rck is not None else None
                c["jsd_richclub"] = round(jsd_rc, 4) if jsd_rc is not None else None
                c["quota_topk"] = round(quota, 4) if quota is not None else None
                c["limiar_quota"] = limiar_q_tick
                c["penhasco"] = round(penh, 4) if penh is not None else None
                c["limiar_penhasco"] = limiar_r_tick
                c["k"] = k_tick
                c["limiar"] = limiar_tick
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
            _vigiar_estado_2c(
                est,
                jsd_pesos_richclub_k(sub),
                quota_topk(sub),
                limiar_estado_k(sub.n_arestas()),
                limiar_quota(sub.n_arestas()),
                jsd_pesos_ordenado(sub),
                penhasco(sub),
                limiar_penhasco(sub.n_arestas()),
            )
    finally:
        pc._tentar_simbolo = original
    jsd_finais = [c["jsd_pesos"] for c in checkpoints if c["jsd_pesos"] is not None]
    jsd_min = min(jsd_finais) if jsd_finais else None
    jsd_final = jsd_finais[-1] if jsd_finais else None
    jsd_ord_finais = [c["jsd_ordenado"] for c in checkpoints if c["jsd_ordenado"] is not None]
    jsd_ord_final = jsd_ord_finais[-1] if jsd_ord_finais else None
    jsd_rck_finais = [c["jsd_richclub_k"] for c in checkpoints if c["jsd_richclub_k"] is not None]
    jsd_rck_final = jsd_rck_finais[-1] if jsd_rck_finais else None
    jsd_rc_finais = [c["jsd_richclub"] for c in checkpoints if c["jsd_richclub"] is not None]
    jsd_rc_final = jsd_rc_finais[-1] if jsd_rc_finais else None
    quota_finais = [c["quota_topk"] for c in checkpoints if c["quota_topk"] is not None]
    quota_final = quota_finais[-1] if quota_finais else None
    penh_finais = [c["penhasco"] for c in checkpoints if c["penhasco"] is not None]
    penh_final = penh_finais[-1] if penh_finais else None
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
    # Critérios da variante — os dois portões (conjunção), lado a lado.
    criterios["veto_estado_disparou"] = len(est.vetos_estado) > 0
    criterios["veto_tick_disparou"] = len(est.vetos_tick) > 0
    criterios["cluster_tiranico"] = len(est.vetos_estado) > 0
    criterios["simbolo_valido"] = _simbolo_valido(est.simbolo_tick, est.vetos_estado)
    criterios["simbolo_valido_checkpoint"] = criterios["simbolo_valido"]
    criterios["simbolo_valido_tick"] = _simbolo_valido(est.simbolo_tick, est.vetos_tick)
    criterios["veredicto_muda"] = (
        criterios["simbolo_valido"] != criterios["simbolo_valido_tick"]
    )
    # Ticks em que o estado seria tirânico pela CONJUNÇÃO
    # (ISC >= 0,85 E JSDrc_k < limiar E quota >= limiar_quota),
    # na trajetória por tick — e as mesmas listas para cada
    # critério sozinho, para a comparação ser feita no mesmo
    # estado. Os vetos por tick têm de ser exactamente os ticks
    # da conjunção — é o cheque de consistência entre a
    # trajetória e o portão.
    ticks_tiranicos = [
        t["tick"]
        for t in trajetoria
        if t["isc_local"] >= 0.85
        and t["jsd_richclub_k"] is not None
        and t["jsd_richclub_k"] < t["limiar"]
        and t["quota_topk"] is not None
        and t["quota_topk"] >= t["limiar_quota"]
    ]
    ticks_tiranicos_jsd = [
        t["tick"]
        for t in trajetoria
        if t["isc_local"] >= 0.85
        and t["jsd_richclub_k"] is not None
        and t["jsd_richclub_k"] < t["limiar"]
    ]
    ticks_quota = [
        t["tick"]
        for t in trajetoria
        if t["isc_local"] >= 0.85
        and t["quota_topk"] is not None
        and t["quota_topk"] >= t["limiar_quota"]
    ]
    ticks_penhasco = [
        t["tick"]
        for t in trajetoria
        if t["isc_local"] >= 0.85
        and t["penhasco"] is not None
        and t["penhasco"] >= t["limiar_penhasco"]
    ]
    ticks_tiranicos_028 = [
        t["tick"]
        for t in trajetoria
        if t["isc_local"] >= 0.85
        and t["jsd_richclub_k"] is not None
        and t["jsd_richclub_k"] < JSD_ESTADO
    ]
    criterios["segundo_criterio_disparou"] = len(ticks_quota) > 0
    criterios["penhasco_dispararia"] = len(ticks_penhasco) > 0
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
        "variante": "segundo critério (quota dos top-k em conjunção com o JSD rich-club k(n), vigilância por tick)",
        "semente": semente,
        "ticks": n_ticks,
        "pesos_finais": pesos_finais,
        "alavanca": {
            "nome": "segundo critério no portão de estado: quota dos top-k",
            "regra_k": "k(n) = ceil(n/3)",
            "tabela_calibracao": {
                str(n): {"k": k, "limiar_jsd": lim, "limiar_quota": lim_q, "limiar_penhasco": lim_r}
                for n, (k, lim, lim_q, lim_r) in sorted(TABELA_CALIBRACAO_2C.items())
            },
            "jsd_rc_estado_k4": JSD_RC_ESTADO,
            "jsd_rc_uniforme_k4": JSD_RC_UNIFORME,
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
        "ticks_tiranicos_jsd": ticks_tiranicos_jsd,
        "ticks_quota": ticks_quota,
        "ticks_penhasco": ticks_penhasco,
        "ticks_tiranicos_028": ticks_tiranicos_028,
        "comparacao": comparacao,
        "margens_dois_criterios": _margens_dois_criterios(trajetoria),
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
        "quota_max": round(quota_max, 4) if quota_max is not None else None,
        "quota_max_tick": quota_max_tick,
        "quota_final": round(quota_final, 4) if quota_final is not None else None,
        "penhasco_max": round(penh_max, 4) if penh_max is not None else None,
        "penhasco_max_tick": penh_max_tick,
        "penhasco_final": round(penh_final, 4) if penh_final is not None else None,
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


def sondar_segundo_criterio(
    fatores=(1.00, 1.05, 1.10, 1.20, 1.50),
    semente=pc.SEMENTE,
    fator_decaimento=FATOR_DECAIMENTO,
):
    """Sonda de dose-resposta: corre a variante em cada fator de
    amplificação (decaimento fixo em 0,95, como na Sora, na
    rich-club, na vigília e na k variável) e devolve, por fator,
    se o Símbolo se formou, os vetos por tentativa, por estado
    (checkpoint) e por tick (CONJUNÇÃO), o primeiro veto de cada
    portão, os dois veredictos de validade (checkpoint e tick) e
    se o veredicto muda, os ticks tirânicos pela conjunção e por
    cada critério sozinho, as margens dos dois critérios, o Gini
    final, os JSDs mínimo e final (antigo, novo k(n) e k = 4
    fixo), a quota máxima e final, o penhasco máximo, o VarPn
    final e o total de amplificações. A pergunta que a sonda
    responde: com um segundo critério em conjunção, o controlo
    separa-se COM MARGEM — e o hub continua a ser apanhado?"""
    linhas = []
    for fator in fatores:
        rel = rodar_party_causal_segundo_criterio(
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
                "ticks_tiranicos_jsd": list(rel["ticks_tiranicos_jsd"]),
                "ticks_quota": list(rel["ticks_quota"]),
                "ticks_penhasco": list(rel["ticks_penhasco"]),
                "margens_dois_criterios": rel["margens_dois_criterios"],
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
                "quota_max": rel["quota_max"],
                "quota_max_tick": rel["quota_max_tick"],
                "quota_final": rel["quota_final"],
                "penhasco_max": rel["penhasco_max"],
                "penhasco_max_tick": rel["penhasco_max_tick"],
                "varpn_final": final.get("var_ponderada_normalizada"),
                "isc_final": final.get("isc_local"),
                "arestas_no_piso": final.get("arestas_no_piso"),
                "total_amplificacoes": rel["alavanca"]["total_amplificacoes"],
                "acoes_amplificadoras": rel["alavanca"]["acoes_amplificadoras"],
            }
        )
    return linhas


def imprimir_relatorio(rel):
    """Tabela da variante + sonda de dose-resposta + margens dos
    dois critérios."""
    print("Isekai Zero — A Party Causal: variante SEGUNDO CRITÉRIO (quota dos top-k em conjunção)")
    print(f"semente={rel['semente']}  ticks={rel['ticks']}  "
          f"fator_amplificacao={rel['alavanca']['fator_amplificacao']}  "
          f"fator_decaimento={rel['alavanca']['fator_decaimento']}  piso={rel['alavanca']['piso_decaimento']}")
    print(f"Tabela de calibração (n -> k, limiar JSD, limiar quota, limiar penhasco): {rel['alavanca']['tabela_calibracao']}")
    print("tick | arest | k | limJSD | limQ | ISC   | VarPn | ISCaux | Gini  | λ₂    | MIP   | JSDp  | JSDord | JSDrcK | JSDrc4 | Q     | Penh  | VetT | VetE | VetK | Piso | Ampl | Símbolo")
    for c in rel["checkpoints"]:
        print(
            f"{c['tick']:>4} | {c['n_arestas']:>5} | {c['k']:>2} | {c['limiar']:>6} | {c['limiar_quota']:>6} | {c['isc_local']:.3f} | "
            f"{c['var_ponderada_normalizada']:.3f} | {c['isc_aux']:.3f} | "
            f"{c['gini']:.3f} | {c['lambda2']:.3f} | {c['mip_corte_min']:.3f} | "
            f"{c['jsd_pesos'] if c['jsd_pesos'] is not None else '-':>5} | "
            f"{c['jsd_ordenado'] if c['jsd_ordenado'] is not None else '-':>6} | "
            f"{c['jsd_richclub_k'] if c['jsd_richclub_k'] is not None else '-':>6} | "
            f"{c['jsd_richclub'] if c['jsd_richclub'] is not None else '-':>6} | "
            f"{c['quota_topk'] if c['quota_topk'] is not None else '-':>5} | "
            f"{c['penhasco'] if c['penhasco'] is not None else '-':>5} | "
            f"{c['vetos']:>4} | {c['vetos_estado']:>4} | {c['vetos_tick']:>4} | {c['arestas_no_piso']:>4} | "
            f"{c['amplificacoes']:>4} | {'SIM' if c['simbolo'] else 'não'}"
        )
    ev = rel["eventos"]
    print(f"Símbolo formado no tick: {ev['simbolo_tick']}")
    print(f"Ren seguiu o verdadeiro fraco: {ev['ren_verdadeiro']}x (falso: {ev['ren_falso']}x)")
    print(f"Vetos por tentativa: {len(ev['vetos'])} -> {ev['vetos']}")
    print(f"Vetos por estado (checkpoint, conjunção): {len(ev['vetos_estado'])} -> {[v['tick'] for v in ev['vetos_estado']]}")
    print(f"Vetos por estado (tick, conjunção): {len(ev['vetos_tick'])} -> {[v['tick'] for v in ev['vetos_tick']]}")
    print(f"Comparação: {rel['comparacao']}")
    print(f"Margens dos dois critérios: {rel['margens_dois_criterios']}")
    print(f"Ticks tirânicos (conjunção): {rel['ticks_tiranicos']}")
    print(f"Ticks tirânicos (só JSD): {rel['ticks_tiranicos_jsd']}")
    print(f"Ticks com quota acima do limiar: {rel['ticks_quota']}")
    print(f"Ticks com penhasco acima do limiar: {rel['ticks_penhasco']}")
    print(f"Ticks tirânicos com 0,28 sem reescala: {rel['ticks_tiranicos_028']}")
    print(f"Depósitos por agente: {ev['depositos_por_agente']}")
    print(f"Amplificações da Sora: {rel['alavanca']['total_amplificacoes']} arestas em "
          f"{rel['alavanca']['acoes_amplificadoras']} ações")
    print(f"JSD rich-club k(n): mínimo {rel['jsd_richclub_k_min']} (tick {rel['jsd_richclub_k_min_tick']}), "
          f"final {rel['jsd_richclub_k_final']}; JSD rich-club k=4: mínimo {rel['jsd_richclub_min']} "
          f"(tick {rel['jsd_richclub_min_tick']}), final {rel['jsd_richclub_final']}; "
          f"JSD ordenado: mínimo {rel['jsd_ordenado_min']} "
          f"(tick {rel['jsd_ordenado_min_tick']}), final {rel['jsd_ordenado_final']}; "
          f"quota: máxima {rel['quota_max']} (tick {rel['quota_max_tick']}), final {rel['quota_final']}; "
          f"penhasco: máximo {rel['penhasco_max']} (tick {rel['penhasco_max_tick']}), final {rel['penhasco_final']}; "
          f"cruzamentos: {rel['cruzamentos']}")
    print(f"Critérios: {rel['criterios']}")
    print()
    print("Sonda de dose-resposta (fator -> Símbolo / vetos tent. / vetos estado / vetos tick / 1º veto tick / 1º veto ckpt / válido ckpt / válido tick / veredicto muda / ticks conjunção / ticks quota / margens / Gini final / quota máx / penhasco máx / VarPn final):")
    for linha in sondar_segundo_criterio():
        print(
            f"  {linha['fator']:.2f} -> tick {linha['simbolo_tick']} / "
            f"{linha['vetos_tentativa']} tent. / {linha['vetos_estado']} estado / "
            f"{linha['vetos_tick']} tick / 1º tick {linha['primeiro_veto_tick']} / "
            f"1º ckpt {linha['primeiro_veto_checkpoint']} / válido ckpt {linha['simbolo_valido']} / "
            f"válido tick {linha['simbolo_valido_tick']} / muda {linha['veredicto_muda']} / "
            f"conj {linha['ticks_tiranicos']} / quota {linha['ticks_quota']} / "
            f"margens {linha['margens_dois_criterios']} / Gini {linha['gini_final']} / "
            f"quota máx {linha['quota_max']} (tick {linha['quota_max_tick']}) / "
            f"penhasco máx {linha['penhasco_max']} / VarPn {linha['varpn_final']} / amplificações {linha['total_amplificacoes']}"
        )


if __name__ == "__main__":
    imprimir_relatorio(rodar_party_causal_segundo_criterio())
