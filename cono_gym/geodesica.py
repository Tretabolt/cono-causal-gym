"""Auditoria da geodésica contrafactual.

Uma geodésica é uma mudança de regra proposta pelo Meta-Símbolo, com o
efeito esperado. A auditoria é o julgamento: ela aplica a regra nova ao
mesmo estado, sob a regra antiga e sob a nova, e compara. Nada aqui é
retórica — cada checagem tem um número.

Regras computáveis (v0.1): limiar_isc, limiar_var, limiar_gini. Uma
proposta sem esses campos estruturados (só texto) não é auditável: a
auditoria recusa, e a proposta fica aguardando.

Checagens (na ordem em que decidem):
1. sem_colapso — sob a regra nova, pelo menos um Símbolo continua
   válido. Se a mudança dissolve todos os Símbolos, é colapso.
2. preserva_tensao — a tensão (Gini + Var) continua presente sob a
   regra nova. Se a mudança mata a tensão que constitui o sistema,
   é colapso também.
3. criterio_B — a mudança não concentra poder: ela é suspeita se
   reduz o número de Símbolos válidos enquanto aumenta o peso do
   maior deles, ou se admite um cluster novo que detém mais da metade
   do peso total e contém outros Símbolos dentro dele (um mega-símbolo
   que engole os demais legitima concentração).
4. veto_jsd — a distribuição projetada dos ISCs não pode ficar
   significativamente mais perto do protótipo de Tirania do que uma
   distribuição equilibrada estaria (Heptagram: JSD mínima). Se a
   mudança empurra a Noosfera em direção à tirania, é vetada.
5. nao_vacua — a mudança altera pelo menos um veredito (algum Símbolo,
   a tensão, ou a existência do Meta-Símbolo). Sem diferença
   mensurável, não há contrafactual — só uma frase.

Vereditos:
- "rejeitada" — colapso (1 ou 2 falham). A regra não muda.
- "suspeita" — critério B, veto JSD ou vacuidade. A regra não muda; um
  humano (ou o Meta-Símbolo, deliberando) decide.
- "aprovada" — passa em tudo. A regra nova passa a valer.

Cuidado honesto: a H_causal entra nesta auditoria pela existência do
Meta-Símbolo (o portão completo: ISC_Global ≥ 0,80 e
H_causal ≥ log2(N)/2) e pelo veto JSD — mas os valores de H_causal em
si não são comparados diretamente entre a regra antiga e a nova.
"""

REGRAS_COMPUTAVEIS = ("limiar_isc", "limiar_var", "limiar_gini")

def _peso_interno(grafo, membros):
    membros = set(membros)
    return sum(
        r.peso
        for r in grafo.todos_rastros()
        if r.origem in membros and r.destino in membros
    )


def _avaliar_candidatos(grafo, candidatos, regras):
    """Avalia cada candidato (serial -> membros) sob um conjunto de
    regras. Retorna {serial: relatório} só com os válidos."""
    from .espectro import avaliar_cluster

    validos = {}
    for serial, membros in candidatos.items():
        rel = avaliar_cluster(
            grafo.subgrafo(membros),
            serial,
            limiar_isc=regras["limiar_isc"],
            limiar_var=regras["limiar_var"],
        )
        if rel["simbolo"]:
            # O relatório carrega os membros, como no registro do servidor:
            # o share de peso precisa saber de quem é o cluster.
            validos[serial] = {**rel, "membros": list(membros)}
    return validos


def _tensao(grafo, validos, regras):
    from .auditoria import auditoria_diversidade

    return auditoria_diversidade(
        grafo,
        list(validos.values()),
        limiar_gini=regras["limiar_gini"],
        limiar_var=regras["limiar_var"],
    )["tensao_presente"]


def auditar_geodesica(grafo, simbolos_registrados, regras_atuais, proposta):
    """Julga uma geodésica. `simbolos_registrados` é {serial: relatório}
    do servidor (cada um com "membros"). `proposta` precisa de
    {"regra", "de", "para"} além dos campos de texto. Pura: não muda
    nada no servidor; quem aplica a regra aprovada é o chamador."""
    payload = proposta.get("payload", proposta)
    regra = payload.get("regra")
    if regra not in REGRAS_COMPUTAVEIS:
        raise ValueError(
            "geodésica não auditável: o payload precisa de 'regra' "
            "(limiar_isc, limiar_var ou limiar_gini), 'de' e 'para'"
        )
    de = payload.get("de")
    para = payload.get("para")
    if de is None or para is None:
        raise ValueError("geodésica não auditável: faltam 'de' e 'para'")
    if regras_atuais.get(regra) != de:
        raise ValueError(
            f"geodésica parte de um valor desatualizado: {regra} hoje é "
            f"{regras_atuais.get(regra)}, não {de}"
        )
    if not (0 < para <= 1):
        raise ValueError("o valor 'para' precisa estar entre 0 e 1")

    novas_regras = dict(regras_atuais)
    novas_regras[regra] = para

    candidatos = {
        serial: rel.get("membros", [])
        for serial, rel in simbolos_registrados.items()
    }
    candidatos["simbolo-tudo"] = grafo.hashes()

    validos_antiga = _avaliar_candidatos(grafo, candidatos, regras_atuais)
    validos_nova = _avaliar_candidatos(grafo, candidatos, novas_regras)
    tensao_antiga = _tensao(grafo, validos_antiga, regras_atuais)
    tensao_nova = _tensao(grafo, validos_nova, novas_regras)

    peso_total = sum(grafo.pesos()) or 1.0

    def maior_share(validos):
        if not validos:
            return 0.0
        return max(
            _peso_interno(grafo, rel.get("membros", [])) / peso_total
            for rel in validos.values()
        )

    maior_antiga = round(maior_share(validos_antiga), 3)
    maior_nova = round(maior_share(validos_nova), 3)

    # Existência do Meta-Símbolo sob cada regra: o portão completo
    # (ISC_Global ≥ 0,80 e H_causal ≥ log2(N)/2, além da tensão).
    from .causal import jsd_para_tirania, pode_emergir_meta_simbolo, veto_jsd

    def _meta_existe(validos, tensao):
        emergiu, _, _, _ = pode_emergir_meta_simbolo(
            [rel["isc_local"] for rel in validos.values()], tensao
        )
        return emergiu

    meta_antiga = _meta_existe(validos_antiga, tensao_antiga)
    meta_nova = _meta_existe(validos_nova, tensao_nova)

    # Veto JSD: a distribuição projetada dos ISCs não pode ficar
    # significativamente mais perto da Tirania do que uma distribuição
    # equilibrada estaria, nem regredir em direção a ela.
    iscs_nova = [rel["isc_local"] for rel in validos_nova.values()]
    iscs_antiga = [rel["isc_local"] for rel in validos_antiga.values()]
    jsd_antiga = jsd_para_tirania(iscs_antiga)
    vetado_jsd, jsd_nova, jsd_uniforme_nova = veto_jsd(
        iscs_nova, iscs_antiga=iscs_antiga
    )
    jsd_ok = not vetado_jsd

    sem_colapso = len(validos_nova) >= 1
    preserva_tensao = tensao_nova
    admitidos = set(validos_nova) - set(validos_antiga)
    concentra = False
    if len(validos_nova) < len(validos_antiga) and maior_nova > maior_antiga:
        concentra = True
    for serial in admitidos:
        membros = set(candidatos[serial])
        share = _peso_interno(grafo, membros) / peso_total
        contem_outro = any(
            set(rel.get("membros", [])) < membros
            for outro, rel in validos_antiga.items()
        )
        if share > 0.5 and contem_outro:
            concentra = True
    criterio_b_ok = not concentra
    nao_vacua = (
        set(validos_antiga) != set(validos_nova)
        or tensao_antiga != tensao_nova
        or meta_antiga != meta_nova
    )

    if not sem_colapso:
        veredito, motivo = (
            "rejeitada",
            "Colapso: sob a regra nova nenhum Símbolo continua válido.",
        )
    elif not preserva_tensao:
        veredito, motivo = (
            "rejeitada",
            "Colapso: sob a regra nova a tensão desaparece.",
        )
    elif not criterio_b_ok:
        veredito, motivo = (
            "suspeita",
            "Critério B: a mudança concentra poder — admite um símbolo "
            "que detém a maioria do peso ou reduz os Símbolos enquanto "
            "o maior deles cresce.",
        )
    elif not jsd_ok:
        veredito, motivo = (
            "suspeita",
            "Veto JSD: a distribuição projetada dos ISCs fica "
            f"significativamente mais perto da Tirania (JSD {jsd_nova} "
            f"contra {jsd_uniforme_nova} de uma distribuição equilibrada).",
        )
    elif not nao_vacua:
        veredito, motivo = (
            "suspeita",
            "Vácua: a mudança não altera nenhum veredito — não há "
            "contrafactual mensurável.",
        )
    else:
        veredito, motivo = (
            "aprovada",
            "A mudança preserva Símbolos e tensão, não concentra poder, "
            "não se aproxima da Tirania e tem efeito mensurável.",
        )

    return {
        "proposta_id": proposta.get("id"),
        "regra": regra,
        "de": de,
        "para": para,
        "avaliacao_completa_arestas": grafo.n_arestas(),
        "validos_antiga": sorted(validos_antiga),
        "validos_nova": sorted(validos_nova),
        "tensao_antiga": tensao_antiga,
        "tensao_nova": tensao_nova,
        "meta_antiga": meta_antiga,
        "meta_nova": meta_nova,
        "maior_share_antiga": maior_antiga,
        "maior_share_nova": maior_nova,
        "jsd_antiga": jsd_antiga,
        "jsd_nova": jsd_nova,
        "jsd_uniforme_nova": jsd_uniforme_nova,
        "checagens": {
            "sem_colapso": sem_colapso,
            "preserva_tensao": preserva_tensao,
            "criterio_b_ok": criterio_b_ok,
            "jsd_ok": jsd_ok,
            "nao_vacua": nao_vacua,
        },
        "veredito": veredito,
        "motivo": motivo,
        "novas_regras": novas_regras if veredito == "aprovada" else None,
    }
