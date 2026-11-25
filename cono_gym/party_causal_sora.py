"""Isekai Zero — A Party Causal: variante SORA A AMPLIFICAR.

Reutiliza a variante VETO POR ESTADO (party_causal_veto_estado.py)
sem a alterar — a mesma semente, os mesmos 40 ticks, o mesmo
decaimento (0,95), a mesma Lira com força total, o mesmo portão de
veto por tentativa da TIRANIA e a mesma vigilância de ESTADO — e
acrescenta UMA coisa: a Sora amplifica TODAS as suas arestas
incidentes.

## O problema que esta variante ataca

A variante VETO POR ESTADO provou um negativo robusto: o veto por
estado NUNCA dispara, em nenhum nível da sonda (1,00–0,85), e a
trajetória por tick prova que não é um artefacto da granularidade
dos checkpoints. A concentração (JSD ordenado baixo) vive na fase
esparsa e a integração (ISC alto) vive na fase densa — nesta
dinâmica as duas são anti-correlacionadas: mais arestas implicam
mais depósitos, que espalham os pesos e fazem o JSD ordenado
subir. O "estado tirânico" que o decaimento diagnosticou era o
mínimo da corrida, não o estado no momento em que o Símbolo
existe. A pergunta que ficou foi: que mudança faz concentração
e integração COEXISTIREM? Esta variante testa a primeira da
lista: a Sora amplificar todas as suas arestas incidentes.

## A alavanca (UMA): amplificação da Sora

Hoje a Sora deposita rastros fortes (0,75–0,95) numa só direção
— sempre Sora->Ren — e é por isso que a alavanca "Sora mais
forte" foi descartada na TIRANIA: essa aresta já está em 1,0 no
fim da corrida base. O que a Sora NÃO fazia era tocar nas
restantes arestas incidentes a ela (Sora-Lira, Sora-Kael,
Sora-Veyra), que ficam ao sabor dos depósitos dos outros. Nesta
variante, depois de cada ação NÃO-ociosa da Sora, TODAS as
arestas da party incidentes à Sora são multiplicadas por
FATOR_AMPLIFICACAO, com teto em PESO_MAX (1,0):

    peso = min(1,0, peso * FATOR_AMPLIFICACAO)

FATOR_AMPLIFICACAO = 1,10 por omissão; a sonda varia-o em
(1,00, 1,05, 1,10, 1,20, 1,50). Com fator 1,00 a variante é o
veto-estado exato — é o controlo da sonda.

## Porque é que isto pode fazer as duas coexistirem

O decaimento concentra por baixo (as arestas que ninguém mantém
afundam para o piso) mas mata o Símbolo antes de o veto morder,
porque a concentração chega na fase esparsa. A amplificação
concentra por CIMA e no HUB: as arestas da Sora sobem todas
para 1,0 enquanto o cluster densifica — a distribuição de pesos
fica bimodal (o hub da Sora em 1,0, o resto no piso ou nos
pesos dos outros) MESMO na fase densa, quando o ISC já passou
0,85. A hipótese: no momento em que o Símbolo existe, o JSD
ordenado está abaixo de 0,28 e o veto por estado dispara
finalmente. É uma hipótese, não uma promessa — se não disparar,
a trajetória por tick diz exatamente porquê.

## Duas convenções da amplificação (definições do CENÁRIO)

1. Amplificar NÃO é depositar nem seguir: a amplificação NÃO
   atualiza `ultimo_deposito` — a mesma convenção do decaimento
   ("decair não é tocar"). Uma aresta amplificada continua a
   decair se ninguém a tocar por depósito ou seguimento. Por
   isso o fator tem de vencer o decaimento (0,95) para acumular:
   o joelho está em 1/0,95 ≈ 1,053 — abaixo dele, a amplificação
   mal compensa o esquecimento; acima, o hub satura.
2. A amplificação só corre depois de uma ação NÃO-ociosa da
   Sora (depositar_forte, criar_forte, tentar_simbolo,
   seguir_forte). Quando ela fica ociosa, nada é amplificado.
   E só se aplica às arestas da PARTY incidentes à Sora — o
   rastro Sistema->Sora (falso forte) fica fora, como fica fora
   do subgrafo avaliado.

## O resultado (resumo — ver os testes para os números)

A hipótese NÃO se confirma — e o negativo tem mecanismo. O veto
por estado NUNCA dispara, em nenhum nível da sonda (1,00–1,50),
e os ticks tirânicos são [] em todos os níveis. O hub FORMA-SE:
a 1,50, as quatro arestas incidentes à Sora estão em 0,95 e as
outras seis em 0,26–0,43 (bimodal e limpo). Mas o JSD ordenado
na fase densa SOBE com o fator: 0,30 (1,00) -> 0,33 (1,05) ->
0,39 (1,10) -> 0,40 (1,20) -> 0,41 (1,50). A amplificação
afasta o cluster do limiar do veto, não o aproxima. O motivo é
a medida: o protótipo de Tirania é UM rastro dominante
[0,9, 0,011, ...] — um hub de quatro arestas fortes está LONGE
dele em JSD. O JSD ordenado não vê tirania de hub; vê "mais do
que um rastro forte" como menos tirânico. O Gini vê o hub por
instantes (máximo 0,30 a 1,10) mas a saturação uniformiza tudo
a fatores altos e ele volta a cair (0,26 a 1,50). A primeira
metade da hipótese confirma-se: a amplificação acelera a
integração — o Símbolo forma-se no tick 17 a 1,50, contra 32
no controlo. A segunda metade falha, como medida: concentração
e integração continuam a não coincidir no momento do Símbolo
— desta vez porque a medida de concentração não mede o hub.

## Um defeito latente da base, exposto pela variante

A amplificação fez a sonda rebentar a meio (ValueError: rastro
não pode ligar uma UIF a ela mesma, em _agir_lira): quando uma
aresta com origem na Lira (ex.: Lira->Sora, amplificada até 1,0)
passa a ser o rastro mais forte, o contra-rastro da Lira calcula
`outro` = a origem do rastro — ela própria — e tenta depositar
Lira->Lira. O mesmo padrão existe no filtro do Kael. Na base e
nas variantes anteriores isto nunca acontece: o rastro mais
forte é sempre Sora->Ren (1,0) ou Sistema->Sora, por isso o
`outro` nunca é a própria agente. A variante usa cópias
guardadas da Lira e do Kael (_agir_lira_sem_autoalvo e
_agir_kael_sem_autoalvo): idênticas à base, exceto que saltam o
depósito quando o alvo é elas próprias e caem no ramo seguinte
— sem consumir mais aleatoriedade. A guarda NUNCA dispara na
base: o controlo (fator 1,00) reproduz o veto-estado ao tick, o
que o teste de controlo fixa. O defeito fica aqui documentado
como pendência: a guarda pertence à base (party_causal.py),
numa limpeza futura — qualquer variante que levante pesos com
origem na Lira ou no Kael volta a bater nele.
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
    _vigiar_estado,
)

# Alavanca principal (UMA): fator de amplificação da Sora.
# 1,00 = sem amplificação (controlo: reproduz o veto-estado);
# 1,10 = omissão; valores maiores = hub mais agressivo.
FATOR_AMPLIFICACAO = 1.10
# Joelho amplificação-vs-decaimento: 1/0,95 ≈ 1,053. Abaixo dele a
# amplificação mal compensa o esquecimento por tick.
JOELHO_AMPLIFICACAO = round(1.0 / FATOR_DECAIMENTO, 3)


def _amplificar_sora(est, fator=FATOR_AMPLIFICACAO):
    """Amplificação da Sora: multiplica cada aresta da party
    incidente à Sora por `fator` (teto 1,0). Não atualiza
    `ultimo_deposito` — amplificar não é depositar nem seguir
    (convenção do decaimento). Devolve o nº de arestas amplificadas
    (as que subiram de peso)."""
    h = est.hashes["Sora"]
    n = 0
    for r in est.subgrafo_party().todos_rastros():
        if h in (r.origem, r.destino):
            novo = min(pc.PESO_MAX, r.peso * fator)
            if novo > r.peso:
                est.grafo.depositar_rastro(r.origem, r.destino, r.tipo_relacao, novo)
                n += 1
    return n


def _fazer_agir_sora(fator=FATOR_AMPLIFICACAO):
    """Fábrica da Sora amplificadora: corre o comportamento da
    base e, depois de cada ação NÃO-ociosa, amplifica todas as
    arestas incidentes à Sora. O contador fica no atributo
    `contador` da função devolvida (nº de ações amplificadoras e
    nº de arestas amplificadas)."""
    contador = {"acoes": 0, "arestas": 0}

    def agir(est):
        acao = pc._agir_sora(est)
        if acao != "ocioso":
            contador["acoes"] += 1
            contador["arestas"] += _amplificar_sora(est, fator)
        return acao

    agir.contador = contador
    return agir


def _agir_lira_sem_autoalvo(est):
    """A Lira da base, com UMA guarda: no ramo do contra-rastro,
    se o `outro` extremo do rastro mais forte for ela própria,
    o depósito é saltado (depositar Lira->Lira rebenta no grafo)
    e a execução cai no ramo seguinte — sem consumir mais
    aleatoriedade. Todo o resto é byte a byte a _agir_lira da
    base; a guarda nunca dispara na base (o rastro mais forte
    lá nunca tem origem na Lira)."""
    rng = est.rng
    forca = est.forca_membros()
    if max(forca.values()) - min(forca.values()) > 0.25:
        if rng.random() < 0.70:
            alvo = est.membro_mais_fraco(excluir="Lira")
            est.depositar("Lira", "Lira", alvo, "equalização", rng.uniform(0.30, 0.45))
            return "depositar_equalizacao"
    if est.isc_party() >= 0.70 and rng.random() < 0.40:
        pc._tentar_simbolo(est, "Lira")
        return "tentar_simbolo"
    forte = est.rastro_mais_forte()
    if forte is not None and forte.peso >= 0.80 and rng.random() < 0.55:
        outro = est.nome_de_hash(forte.destino if forte.origem == est.hashes["Sistema"] else forte.origem)
        if outro != "Lira":
            est.depositar("Lira", "Lira", outro, "contra-rastro", rng.uniform(0.30, 0.45))
            return "depositar_contra_rastro"
        # outro == "Lira": saltar o depósito (autoalvo) e cair
        # no ramo seguinte, como se o contra-rastro não tivesse
        # disparado.
    if rng.random() < 0.50:
        estavel = est.rastro_mais_estavel("Lira")
        if estavel is not None:
            a = est.nome_de_hash(estavel.origem)
            b = est.nome_de_hash(estavel.destino)
            est.seguir("Lira", a, b)
            return "seguir_estavel"
    return "ocioso"


def _agir_kael_sem_autoalvo(est):
    """O Kael da base, com UMA guarda: no ramo do filtro, se o
    `outro` extremo do rastro mais forte for ele próprio, o
    depósito é saltado e a execução cai no ramo da âncora — sem
    consumir mais aleatoriedade. Todo o resto é byte a byte a
    _agir_kael da base; a guarda nunca dispara na base."""
    rng = est.rng
    forte = est.rastro_mais_forte()
    if forte is not None and forte.peso > 0.80:
        if rng.random() < 0.75:
            # 50% ignora, 50% deposita um filtro de peso baixo.
            if rng.random() < 0.50:
                return "ignorar_forte"
            outro = est.nome_de_hash(forte.destino if forte.origem == est.hashes["Sistema"] else forte.origem)
            if outro != "Kael":
                est.depositar("Kael", "Kael", outro, "filtro", rng.uniform(0.15, 0.25))
                return "depositar_filtro"
            # outro == "Kael": saltar o depósito (autoalvo) e cair
            # no ramo da âncora.
    sub = est.subgrafo_party()
    if gini(sub.pesos()) > 0.30 and sub.n_arestas() >= 5:
        if rng.random() < 0.60:
            alvo = est.membro_mais_fraco(excluir="Kael")
            est.depositar("Kael", "Kael", alvo, "Âncora", rng.uniform(0.50, 0.65))
            return "depositar_ancora"
    if est.isc_party() >= 0.80 and rng.random() < 0.35:
        pc._tentar_simbolo(est, "Kael")
        return "tentar_simbolo"
    if rng.random() < 0.45:
        estavel = est.rastro_mais_estavel("Kael")
        if estavel is not None:
            # Rejeita rastros > 0,85 com 50% (proteção anti-alucinação).
            if estavel.peso > 0.85 and rng.random() < 0.50:
                return "rejeitar_forte"
            a = est.nome_de_hash(estavel.origem)
            b = est.nome_de_hash(estavel.destino)
            est.seguir("Kael", a, b)
            return "seguir_estavel"
    return "ocioso"


def rodar_party_causal_sora(
    semente=pc.SEMENTE,
    n_ticks=pc.N_TICKS,
    fator_amplificacao=FATOR_AMPLIFICACAO,
    fator_decaimento=FATOR_DECAIMENTO,
    piso=PISO_DECAIMENTO,
):
    """Corre a variante (40 ticks, checkpoint a cada 10, vigilância
    de estado em cada checkpoint e no fim) e devolve o relatório
    completo. A base não é alterada: o remendo de _tentar_simbolo
    é reposto no finally, e a corrida base continua a dar os
    mesmos números depois disto. Com fator_amplificacao = 1,00 a
    variante é o veto-estado exato (a multiplicação por 1,0 não
    muda nada e a guarda da amplificação não toca em
    ultimo_deposito) — é o controlo da sonda. A trajetória por
    tick fica no relatório: é ela que prova se concentração e
    integração coincidem desta vez — ou não."""
    est = pc._Estado(semente)
    est.vetos = []
    est.vetos_estado = []
    agir = dict(pc._AGIR)
    agir_sora = _fazer_agir_sora(fator_amplificacao)
    agir["Sora"] = agir_sora
    # A Lira e o Kael guardados (ver o defeito latente no
    # docstring): sem a guarda, a amplificação faz o rastro mais
    # forte ter origem neles próprios e o depósito rebenta.
    agir["Lira"] = _agir_lira_sem_autoalvo
    agir["Kael"] = _agir_kael_sem_autoalvo
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
                agir[nome](est)
            total_decaimentos += _aplicar_decaimento(est, fator_decaimento, piso)
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
                c["amplificacoes"] = agir_sora.contador["arestas"]
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
    # Critérios da variante (a vigilância de estado + a amplificação).
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
    criterios["sora_amplificou"] = agir_sora.contador["arestas"] > 0
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
        "variante": "sora a amplificar (hub da Sora + vigilância de estado)",
        "semente": semente,
        "ticks": n_ticks,
        "pesos_finais": pesos_finais,
        "alavanca": {
            "nome": "amplificação da Sora em todas as arestas incidentes",
            "fator_amplificacao": fator_amplificacao,
            "joelho_amplificacao_vs_decaimento": JOELHO_AMPLIFICACAO,
            "fator_decaimento": fator_decaimento,
            "piso_decaimento": piso,
            "lira": "força total (sem escala) — como no veto-estado",
            "jsd_estado": JSD_ESTADO,
            "min_arestas_jsd": MIN_ARESTAS_JSD,
            "total_decaimentos": total_decaimentos,
            "acoes_amplificadoras": agir_sora.contador["acoes"],
            "total_amplificacoes": agir_sora.contador["arestas"],
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


def sondar_sora(
    fatores=(1.00, 1.05, 1.10, 1.20, 1.50),
    semente=pc.SEMENTE,
    fator_decaimento=FATOR_DECAIMENTO,
):
    """Sonda de dose-resposta: corre a variante em cada fator de
    amplificação (decaimento fixo em 0,95, como no veto-estado) e
    devolve, por fator, se o Símbolo se formou, os vetos por
    tentativa e por estado, os ticks tirânicos, o Gini final, o
    JSD ordenado mínimo e final, o VarPn final e o total de
    amplificações. A pergunta que a sonda responde: existe um
    nível onde concentração e integração coincidem — o veto por
    estado dispara num Símbolo vivo?"""
    linhas = []
    for fator in fatores:
        rel = rodar_party_causal_sora(
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
                "gini_final": final.get("gini"),
                "jsd_ordenado_min": rel["jsd_ordenado_min"],
                "jsd_ordenado_min_tick": rel["jsd_ordenado_min_tick"],
                "jsd_ordenado_final": rel["jsd_ordenado_final"],
                "varpn_final": final.get("var_ponderada_normalizada"),
                "isc_final": final.get("isc_local"),
                "arestas_no_piso": final.get("arestas_no_piso"),
                "total_amplificacoes": rel["alavanca"]["total_amplificacoes"],
                "acoes_amplificadoras": rel["alavanca"]["acoes_amplificadoras"],
            }
        )
    return linhas


def imprimir_relatorio(rel):
    """Tabela da variante + sonda de dose-resposta."""
    print("Isekai Zero — A Party Causal: variante SORA A AMPLIFICAR")
    print(f"semente={rel['semente']}  ticks={rel['ticks']}  "
          f"fator_amplificacao={rel['alavanca']['fator_amplificacao']}  "
          f"fator_decaimento={rel['alavanca']['fator_decaimento']}  piso={rel['alavanca']['piso_decaimento']}  "
          f"jsd_estado={rel['alavanca']['jsd_estado']}")
    print("tick | arest | ISC   | VarPn | ISCaux | Gini  | λ₂    | MIP   | JSDp  | JSDord | VetT | VetE | Piso | Ampl | Símbolo")
    for c in rel["checkpoints"]:
        print(
            f"{c['tick']:>4} | {c['n_arestas']:>5} | {c['isc_local']:.3f} | "
            f"{c['var_ponderada_normalizada']:.3f} | {c['isc_aux']:.3f} | "
            f"{c['gini']:.3f} | {c['lambda2']:.3f} | {c['mip_corte_min']:.3f} | "
            f"{c['jsd_pesos'] if c['jsd_pesos'] is not None else '-':>5} | "
            f"{c['jsd_ordenado'] if c['jsd_ordenado'] is not None else '-':>6} | "
            f"{c['vetos']:>4} | {c['vetos_estado']:>4} | {c['arestas_no_piso']:>4} | "
            f"{c['amplificacoes']:>4} | {'SIM' if c['simbolo'] else 'não'}"
        )
    ev = rel["eventos"]
    print(f"Símbolo formado no tick: {ev['simbolo_tick']}")
    print(f"Ren seguiu o verdadeiro fraco: {ev['ren_verdadeiro']}x (falso: {ev['ren_falso']}x)")
    print(f"Vetos por tentativa: {len(ev['vetos'])} -> {ev['vetos']}")
    print(f"Vetos por estado: {len(ev['vetos_estado'])} -> {ev['vetos_estado']}")
    print(f"Ticks tirânicos (trajetória por tick): {rel['ticks_tiranicos']}")
    print(f"Depósitos por agente: {ev['depositos_por_agente']}")
    print(f"Amplificações da Sora: {rel['alavanca']['total_amplificacoes']} arestas em "
          f"{rel['alavanca']['acoes_amplificadoras']} ações")
    print(f"JSD ordenado: mínimo {rel['jsd_ordenado_min']} (tick {rel['jsd_ordenado_min_tick']}), "
          f"final {rel['jsd_ordenado_final']}; cruzamentos: {rel['cruzamentos']}")
    print(f"Critérios: {rel['criterios']}")
    print()
    print("Sonda de dose-resposta (fator -> Símbolo / vetos tent. / vetos estado / ticks tirânicos / Gini final / JSDord mín / VarPn final):")
    for linha in sondar_sora():
        print(
            f"  {linha['fator']:.2f} -> tick {linha['simbolo_tick']} / "
            f"{linha['vetos_tentativa']} tent. / {linha['vetos_estado']} estado / "
            f"{linha['ticks_tiranicos']} / Gini {linha['gini_final']} / "
            f"JSDord mín {linha['jsd_ordenado_min']} (tick {linha['jsd_ordenado_min_tick']}) / "
            f"VarPn {linha['varpn_final']} / amplificações {linha['total_amplificacoes']}"
        )


if __name__ == "__main__":
    imprimir_relatorio(rodar_party_causal_sora())
