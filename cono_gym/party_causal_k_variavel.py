"""Isekai Zero — A Party Causal: variante K VARIÁVEL COM n.

Reutiliza a variante VIGILÂNCIA POR TICK
(party_causal_vigilia_tick.py) sem a alterar — a mesma semente, os
mesmos 40 ticks, o mesmo decaimento (0,95), a mesma Lira com
força total, o mesmo portão de veto por tentativa da TIRANIA
(JSD ordenado < 0,18), a mesma amplificação da Sora, a mesma
vigilância por tick lado a lado com o portão por checkpoint — e
troca UMA coisa: a MEDIDA de concentração no portão de estado.
O k do protótipo de rich-club deixa de ser fixo em 4 e passa a
variar com n, o número de arestas do cluster, e o limiar é
recalibrado para cada n.

## O problema que esta variante ataca

A vigilância por tick esgotou o que a granularidade tinha para
dar — apanhou o transiente do controlo, mas expôs que o limiar
0,113 vive num bairro concorrido: os vetos do controlo disparam
com JSDrc 0,0997–0,1045, a apenas 0,0085–0,0133 do limiar, e os
ticks 37–40 ficam logo acima dele (0,1159–0,1244). O que resta
é a medida: k = 4 fixo para qualquer n. Mas o cluster não tem
sempre 10 arestas — cresce de 5 para 10 ao longo da corrida, e
um protótipo com 4 dominantes num cluster de 5 arestas quase não
deixa resto: [0,225 x4, 0,1] é 4/5 do cluster a "dominar". A
pergunta que ficou foi: com k a variar com n — o clube a ser
sempre a mesma fracção do cluster — o limiar sai do bairro
concorrido? E o controlo continua a mudar de veredicto por tick?

## A regra k(n) (definição do CENÁRIO, não canónica)

    k(n) = ceil(n / 3)

O rich club é o TERÇO SUPERIOR das arestas do cluster. A regra
foi escolhida com números, não com palpite:

- a n = 10 reproduz o rich-club antigo exactamente: k(10) = 4,
  e o limiar recalibrado a n = 10 é 0,113 — o mesmo JSD_RC_ESTADO
  (ver a recalibração abaixo e o teste de regressão);
- mantém 1 <= k < n para todo o n >= 2 (o protótipo exige-o);
- mantém a fracção dominante perto de 1/3 em todo o intervalo
  observado (n = 5..10): k/n = 0,40 / 0,33 / 0,43 / 0,38 /
  0,33 / 0,40.

A alternativa óbvia, k = round(n/3), foi rejeitada com números:
a n = 10 daria k = 3 e limiar 0,1560 — não reproduziria o
rich-club antigo no fim denso, e o teste de regressão
falharia. O ceil é o que preserva k(10) = 4.

## A recalibração do limiar (definição do CENÁRIO, não canónica)

O mesmo raciocínio que levou ao 0,113, aplicado por n: o limiar
mantém a POSIÇÃO RELATIVA do 0,28 antigo — 52,7% do caminho
entre o protótipo (JSD 0) e o uniforme — na escala de cada n:

    limiar(n) = 0,28 x JSD(uniforme_n, richclub_k(n))
                      / JSD(uniforme_n, tirania_1(n))

Medido (JSD em bits, base 2):

    n  | k(n) | JSD(U, tir1) | JSD(U, rc_k) | limiar(n) | meio
    5  |  2   |     0,3973   |    0,2141    |  0,1509   | 0,1070
    6  |  2   |     0,4373   |    0,2667    |  0,1708   | 0,1334
    7  |  3   |     0,4683   |    0,1935    |  0,1157   | 0,0968
    8  |  3   |     0,4933   |    0,2330    |  0,1323   | 0,1165
    9  |  3   |     0,5138   |    0,2667    |  0,1454   | 0,1334
    10 |  4   |     0,5310   |    0,2141    |  0,1129   | 0,1070

O limiar VARIA com n — por isso o portão usa o limiar
correspondente ao n do tick em que vigia, e não um limiar
único. O limiar tem forma de dente-de-serra: sobe enquanto k
fica fixo e n cresce (o protótipo aproxima-se do uniforme), e
cai quando k incrementa (n = 7: 0,1708 -> 0,1157; n = 10:
0,1454 -> 0,1129). É uma propriedade da regra, não um erro:
o portão fica mais exigente exactamente quando o cluster
densifica. O ponto médio entre protótipo e uniforme acompanha
o limiar em todos os n (a mesma verificação independente do
0,113) — a reescala não é um artefacto de um n só.

Um preço medido da regra: um hub perfeito de 4 arestas a n = 9
mede JSD 0,0893 contra o protótipo k = 3, contra 0,0000 contra
o protótipo k = 4 — a medida com k(n) é MENOS sensível ao hub
de 4 arestas quando n < 10, porque o protótipo espera 3
dominantes e o hub tem 4. O limiar a n = 9 (0,1454) compensa
em parte: a distância hub-limiar é 0,0561, contra 0,113 a
n = 10. Se a variante perder o hub a n = 9, é isto — e os
testes fixam-no.

## O resultado (resumo — ver os testes para os números)

A hipótese NÃO se confirma como alívio — e é a primeira vez na
série que uma variante DESFAZ um veredicto anterior. O controlo
(1,00) deixa de mudar de veredicto: 0 vetos por tick e 0 por
checkpoint, Símbolo válido por ambos os portões. O mecanismo
está medido tick a tick: nos ticks 32–36 o cluster tem n = 9
(k = 3, limiar 0,1454) e o JSDrc_k é 0,1643/0,1608/0,1585/
0,1551/0,1538 — acima do limiar por 0,0084–0,0189 — enquanto
o mesmo estado mede 0,0997–0,1045 com k = 4 fixo (abaixo do
0,113 por 0,0085–0,0133). A medida sobe ~0,06 quando k passa
de 4 para 3; o limiar sobe só ~0,03 (0,113 -> 0,1454). A
medida move-se mais do que o limiar, e o transiente escapa.

Mas o bairro concorrido NÃO aliviou: a folga mínima acima do
limiar na fase densa do controlo continua a ser 0,003 (tick
37, JSDrc_k 0,1159 contra limiar 0,1129 — a n = 10 nada muda,
k = 4 e limiar 0,1129 ≈ 0,113), contra 0,0029 com k = 4 fixo.
O bairro mudou de lado, não de largura: o limiar passou para
lá do transiente, e o cluster continua a roçar nele, agora por
cima. A n = 9 a folga é maior (0,0084 no tick 36), mas a n = 10
a roçagem é a mesma de sempre.

Nos níveis amplificados os Símbolos continuam inválidos por
ambos os portões, mas a 1,05 o Símbolo já não nasce tirânico:
o primeiro veto por tick reclamado é o tick 26, um depois do
Símbolo no tick 25 (na vigília era o 25). A 1,10, 1,20 e 1,50
o Símbolo continua a nascer tirânico (28/21/17). Os vetos por
tick a 1,05 caem de 21 para 18 e os por checkpoint de 3 para 2;
a 1,10, 1,20 e 1,50 as contagens são as da vigília (18/21/24
por tick, 2/3/3 por checkpoint). Os critérios da base
continuam a passar em todos os níveis (Ren 26–28x o verdadeiro
fraco, 0–2x o falso; sucesso parcial e completo). A dinâmica é
idêntica à da vigília, tick a tick, em todos os níveis — a
variante só troca a medida. O próximo passo que o resultado
sugere: um segundo critério (a medida sozinha, com k fixo ou
variável, não separa o hub do controlo com margem) — ou
aceitar que o limiar 0,113/0,1129 vive no bairro e calibrar o
portão para a folga, não para o veredicto.
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
    prototipo_richclub,
)


def k_variavel(n):
    """k(n) = ceil(n/3) — o rich club é o terço superior das
    arestas do cluster (definição do CENÁRIO, não canónica).
    Reproduz k = 4 a n = 10; 1 <= k < n para n >= 2."""
    if n < 2:
        raise ValueError("k variável precisa de n >= 2")
    return math.ceil(n / 3)


def prototipo_richclub_k(n):
    """Protótipo de Tirania de rich-club com k(n): o protótipo
    antigo com o k dado pela regra, não fixo. A n = 10 é o
    protótipo rich-club k = 4 exacto."""
    return prototipo_richclub(n, k_variavel(n))


def jsd_pesos_richclub_k(grafo):
    """JSD_pesos rich-club com k(n) (definição da VARIANTE, não
    canónica): os pesos das arestas por ordem DECRESCENTE antes
    da JSD com o protótipo richclub_k(n). None com < 2 arestas,
    como o JSD ordenado da TIRANIA."""
    pesos = grafo.pesos()
    if len(pesos) < 2:
        return None
    return pc.jsd_bits(
        sorted(pesos, reverse=True), prototipo_richclub_k(len(pesos))
    )


def limiar_estado_k(n):
    """Limiar reescalado por n (definição do CENÁRIO, não
    canónica): 0,28 x JSD(uniforme_n, richclub_k(n)) /
    JSD(uniforme_n, tirania_1(n)) — a mesma posição relativa do
    0,28 antigo, na escala de cada n. A n = 10 dá 0,1129, o
    0,113 antigo a menos do arredondamento."""
    if n < 2:
        raise ValueError("o limiar precisa de n >= 2")
    u = [1.0 / n] * n
    return round(
        JSD_ESTADO
        * pc.jsd_bits(u, prototipo_richclub_k(n))
        / pc.jsd_bits(u, pc.prototipo_tirania(n)),
        4,
    )


# Tabela de calibração (n = 5..10, o intervalo que o cluster
# percorre): k(n) e o limiar correspondente, calculados, não
# chutados — os testes fixam-nos.
TABELA_CALIBRACAO = {n: (k_variavel(n), limiar_estado_k(n)) for n in range(5, 11)}


def _vigiar_estado_k(est, jsd_rc_k, jsd_ord, limiar):
    """Vigilância de ESTADO no checkpoint, com a medida rich-club
    de k(n): se o cluster passa a regra canónica de Símbolo
    (ISC_Local >= 0,85) mas o JSD rich-club k(n) está abaixo do
    limiar reescalado para o n DESSE tick, regista um evento de
    veto por estado e devolve True. É um observador, não um
    portão — não bloqueia nada. O evento regista o k e o limiar
    usados, e o JSD rich-club de k = 4 fixo lado a lado, para a
    comparação das duas medidas ser feita no mesmo estado. Com
    < 5 arestas, ou sem JSD, não há sinal: devolve False sem
    registar."""
    sub = est.subgrafo_party()
    if sub.n_arestas() < MIN_ARESTAS_JSD or jsd_rc_k is None:
        return False
    rel = pc.avaliar_cluster(sub, "SIMBOLO_PARTY_001")
    if rel["isc_local"] >= 0.85 and jsd_rc_k < limiar:
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
                "gini": round(gini(sub.pesos()), 4),
                "n_arestas": sub.n_arestas(),
                "k": k_variavel(sub.n_arestas()),
                "limiar": limiar,
                "simbolo_reclamado": est.simbolo_tick is not None,
                "simbolo_no_checkpoint": rel["simbolo"],
            }
        )
        est.eventos.append(
            (est.tick, "VETO POR ESTADO rich-club k(n)", round(jsd_rc_k, 4))
        )
        return True
    return False


def _vigiar_estado_tick_k(est, jsd_rc_k, jsd_ord, limiar):
    """Vigilância de ESTADO em CADA TICK, com a medida rich-club
    de k(n): a mesma regra do portão por checkpoint, corrida no
    fim de cada tick, com o limiar do n DESSE tick. Os eventos
    vão para est.vetos_tick, com o mesmo formato dos eventos por
    checkpoint (mais o campo "via": "tick")."""
    sub = est.subgrafo_party()
    if sub.n_arestas() < MIN_ARESTAS_JSD or jsd_rc_k is None:
        return False
    rel = pc.avaliar_cluster(sub, "SIMBOLO_PARTY_001")
    if rel["isc_local"] >= 0.85 and jsd_rc_k < limiar:
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
            (est.tick, "VETO POR ESTADO (tick) rich-club k(n)", round(jsd_rc_k, 4))
        )
        return True
    return False


def _margens_bairro(trajetoria):
    """O bairro concorrido, medido nas DUAS medidas: na fase
    densa (ISC >= 0,85), a profundidade máxima do veto — o
    quanto o JSD cai abaixo do limiar — e a folga mínima acima
    do limiar nos ticks densos que não são vetados. É isto que
    diz se o limiar novo aliviou o bairro: compara-se a folga
    mínima acima do limiar (k(n)) com a da medida antiga
    (k = 4 fixo, limiar 0,113)."""
    densa_k = [
        (t["limiar"] - t["jsd_richclub_k"], t["tick"])
        for t in trajetoria
        if t["isc_local"] >= 0.85 and t["jsd_richclub_k"] is not None
    ]
    densa_k4 = [
        (JSD_RC_ESTADO - t["jsd_richclub"], t["tick"])
        for t in trajetoria
        if t["isc_local"] >= 0.85 and t["jsd_richclub"] is not None
    ]
    def resumo(densa):
        abaixo = [d for d, _ in densa if d > 0]  # limiar - jsd > 0: vetado
        acima = [-d for d, _ in densa if d <= 0]  # jsd - limiar: folga
        return {
            "profundidade_max_veto": round(max(abaixo), 4) if abaixo else None,
            "folga_min_acima": round(min(acima), 4) if acima else None,
            "n_ticks_densos": len(densa),
        }
    return {"k_variavel": resumo(densa_k), "k_fixo_4": resumo(densa_k4)}


def rodar_party_causal_k_variavel(
    semente=pc.SEMENTE,
    n_ticks=pc.N_TICKS,
    fator_amplificacao=FATOR_AMPLIFICACAO,
    fator_decaimento=FATOR_DECAIMENTO,
    piso=PISO_DECAIMENTO,
):
    """Corre a variante (40 ticks, checkpoint a cada 10, vigilância
    de estado rich-club k(n) em CADA TICK e, em paralelo, nos
    checkpoints) e devolve o relatório completo. A base não é
    alterada: o remendo de _tentar_simbolo é reposto no finally,
    e a corrida base continua a dar os mesmos números depois
    disto. Com fator_amplificacao = 1,00 a variante é o
    veto-estado exacto com a medida trocada — é o controlo da
    sonda. A trajetória por tick regista as DUAS medidas (JSD
    ordenado antigo, JSD rich-club k(n) novo e JSD rich-club
    k = 4 fixo) e o Gini no mesmo estado, mais o k e o limiar
    desse tick: é ela que prova se o limiar novo saiu do bairro
    concorrido — ou não."""
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
                gini_tick = gini(sub.pesos())
                k_tick = k_variavel(sub.n_arestas())
                limiar_tick = limiar_estado_k(sub.n_arestas())
            else:
                jsd_ord = jsd_rck = jsd_rc = gini_tick = None
                k_tick = None
                limiar_tick = None
            trajetoria.append(
                {
                    "tick": tick,
                    "n_arestas": sub.n_arestas(),
                    "k": k_tick,
                    "limiar": limiar_tick,
                    "isc_local": round(isc_tick, 4),
                    "jsd_ordenado": round(jsd_ord, 4) if jsd_ord is not None else None,
                    "jsd_richclub_k": round(jsd_rck, 4) if jsd_rck is not None else None,
                    "jsd_richclub": round(jsd_rc, 4) if jsd_rc is not None else None,
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
            # A vigilância por tick corre no fim de CADA tick,
            # com o limiar do n DESSE tick.
            _vigiar_estado_tick_k(est, jsd_rck, jsd_ord, limiar_tick)
            if tick % pc.CHECKPOINT == 0:
                # A vigilância por checkpoint corre no mesmo lugar
                # da vigília, com o limiar do n DESSE checkpoint.
                _vigiar_estado_k(est, jsd_rck, jsd_ord, limiar_tick)
                c = _checkpoint_tyranny(est, jsd_ord)
                c["jsd_richclub_k"] = round(jsd_rck, 4) if jsd_rck is not None else None
                c["jsd_richclub"] = round(jsd_rc, 4) if jsd_rc is not None else None
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
            _vigiar_estado_k(
                est,
                jsd_pesos_richclub_k(sub),
                jsd_pesos_ordenado(sub),
                limiar_estado_k(sub.n_arestas()),
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
        "variante": "k variável com n (rich-club k=ceil(n/3), limiar reescalado por n, vigilância por tick)",
        "semente": semente,
        "ticks": n_ticks,
        "pesos_finais": pesos_finais,
        "alavanca": {
            "nome": "k variável com n no protótipo de rich-club",
            "regra_k": "k(n) = ceil(n/3)",
            "tabela_calibracao": {
                str(n): {"k": k, "limiar": lim}
                for n, (k, lim) in sorted(TABELA_CALIBRACAO.items())
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
        "ticks_tiranicos_028": ticks_tiranicos_028,
        "comparacao": comparacao,
        "margens_bairro": _margens_bairro(trajetoria),
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


def sondar_k_variavel(
    fatores=(1.00, 1.05, 1.10, 1.20, 1.50),
    semente=pc.SEMENTE,
    fator_decaimento=FATOR_DECAIMENTO,
):
    """Sonda de dose-resposta: corre a variante em cada fator de
    amplificação (decaimento fixo em 0,95, como na Sora, na
    rich-club e na vigília) e devolve, por fator, se o Símbolo
    se formou, os vetos por tentativa, por estado (checkpoint) e
    por tick, o primeiro veto de cada portão, os dois veredictos
    de validade (checkpoint e tick) e se o veredicto muda, os
    ticks tirânicos, as margens do bairro concorrido nas duas
    medidas, o Gini final, os JSDs mínimo e final (antigo, novo
    k(n) e k = 4 fixo), o VarPn final e o total de amplificações.
    A pergunta que a sonda responde: com k a variar com n, o
    limiar sai do bairro concorrido — e o controlo continua a
    mudar de veredicto por tick?"""
    linhas = []
    for fator in fatores:
        rel = rodar_party_causal_k_variavel(
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
                "margens_bairro": rel["margens_bairro"],
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
                "isc_final": final.get("isc_local"),
                "arestas_no_piso": final.get("arestas_no_piso"),
                "total_amplificacoes": rel["alavanca"]["total_amplificacoes"],
                "acoes_amplificadoras": rel["alavanca"]["acoes_amplificadoras"],
            }
        )
    return linhas


def imprimir_relatorio(rel):
    """Tabela da variante + sonda de dose-resposta + margens do
    bairro concorrido nas duas medidas."""
    print("Isekai Zero — A Party Causal: variante K VARIÁVEL COM n (k=ceil(n/3))")
    print(f"semente={rel['semente']}  ticks={rel['ticks']}  "
          f"fator_amplificacao={rel['alavanca']['fator_amplificacao']}  "
          f"fator_decaimento={rel['alavanca']['fator_decaimento']}  piso={rel['alavanca']['piso_decaimento']}")
    print(f"Tabela de calibração (n -> k, limiar): {rel['alavanca']['tabela_calibracao']}")
    print("tick | arest | k | limiar | ISC   | VarPn | ISCaux | Gini  | λ₂    | MIP   | JSDp  | JSDord | JSDrcK | JSDrc4 | VetT | VetE | VetK | Piso | Ampl | Símbolo")
    for c in rel["checkpoints"]:
        print(
            f"{c['tick']:>4} | {c['n_arestas']:>5} | {c['k']:>2} | {c['limiar']:>6} | {c['isc_local']:.3f} | "
            f"{c['var_ponderada_normalizada']:.3f} | {c['isc_aux']:.3f} | "
            f"{c['gini']:.3f} | {c['lambda2']:.3f} | {c['mip_corte_min']:.3f} | "
            f"{c['jsd_pesos'] if c['jsd_pesos'] is not None else '-':>5} | "
            f"{c['jsd_ordenado'] if c['jsd_ordenado'] is not None else '-':>6} | "
            f"{c['jsd_richclub_k'] if c['jsd_richclub_k'] is not None else '-':>6} | "
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
    print(f"Margens do bairro concorrido: {rel['margens_bairro']}")
    print(f"Ticks tirânicos k(n) (trajetória por tick): {rel['ticks_tiranicos']}")
    print(f"Ticks tirânicos com 0,28 sem reescala: {rel['ticks_tiranicos_028']}")
    print(f"Depósitos por agente: {ev['depositos_por_agente']}")
    print(f"Amplificações da Sora: {rel['alavanca']['total_amplificacoes']} arestas em "
          f"{rel['alavanca']['acoes_amplificadoras']} ações")
    print(f"JSD rich-club k(n): mínimo {rel['jsd_richclub_k_min']} (tick {rel['jsd_richclub_k_min_tick']}), "
          f"final {rel['jsd_richclub_k_final']}; JSD rich-club k=4: mínimo {rel['jsd_richclub_min']} "
          f"(tick {rel['jsd_richclub_min_tick']}), final {rel['jsd_richclub_final']}; "
          f"JSD ordenado: mínimo {rel['jsd_ordenado_min']} "
          f"(tick {rel['jsd_ordenado_min_tick']}), final {rel['jsd_ordenado_final']}; "
          f"cruzamentos: {rel['cruzamentos']}")
    print(f"Critérios: {rel['criterios']}")
    print()
    print("Sonda de dose-resposta (fator -> Símbolo / vetos tent. / vetos estado / vetos tick / 1º veto tick / 1º veto ckpt / válido ckpt / válido tick / veredicto muda / margens bairro / Gini final / JSDrcK mín / JSDrcK final / VarPn final):")
    for linha in sondar_k_variavel():
        print(
            f"  {linha['fator']:.2f} -> tick {linha['simbolo_tick']} / "
            f"{linha['vetos_tentativa']} tent. / {linha['vetos_estado']} estado / "
            f"{linha['vetos_tick']} tick / 1º tick {linha['primeiro_veto_tick']} / "
            f"1º ckpt {linha['primeiro_veto_checkpoint']} / válido ckpt {linha['simbolo_valido']} / "
            f"válido tick {linha['simbolo_valido_tick']} / muda {linha['veredicto_muda']} / "
            f"margens {linha['margens_bairro']} / Gini {linha['gini_final']} / "
            f"JSDrcK mín {linha['jsd_richclub_k_min']} (tick {linha['jsd_richclub_k_min_tick']}) / "
            f"JSDrcK final {linha['jsd_richclub_k_final']} / VarPn {linha['varpn_final']} / amplificações {linha['total_amplificacoes']}"
        )


if __name__ == "__main__":
    imprimir_relatorio(rodar_party_causal_k_variavel())
