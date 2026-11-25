"""Isekai Zero — A Party Causal: variante TIRANIA (dureza explícita).

Reutiliza o módulo base (party_causal.py) sem o alterar: a mesma
semente, os mesmos 40 ticks, os mesmos limiares canónicos
(ISC_Local >= 0,85 E VarPn <= 0,36). O que muda é UMA alavanca e UM
monitor — e os dois estão documentados aqui, com o diagnóstico que
os escolheu.

## A alavanca (UMA): a Lira está menos presente como reguladora

LIRA_REGULACAO = 0,20 — multiplica as duas probabilidades
reguladoras da Lira: equalização 0,70 -> 0,14 e contra-rastro
0,55 -> 0,11. Todo o resto (Ren, Kael, Sora, Veyra, Sistema,
pesos, ritmos) é idêntico à corrida base.

## Porque NÃO é a Sora (o diagnóstico que decidiu a alavanca)

A sugestão natural era "Sora mais forte" — mas o diagnóstico
(/tmp/diagnostico_tirania.py, corrida base, semente 20261124)
mostrou que a aresta Sora->Ren JÁ está em 1,0 no fim da corrida
base (27 depósitos, regra max): subir a faixa dela de 0,75–0,95
para 0,85–1,00 não muda nada, a aresta já está no teto. O que
segura a uniformidade da distribuição de pesos é a equalização
da Lira (32 depósitos de 0,30–0,45 nos membros mais fracos): é
ela que mantém as restantes arestas em 0,3–0,55 e impede a
concentração. Por isso a alavanca é a Lira, não a Sora.

## O monitor: JSD_pesos_ordenado (a versão base é sensível à ordem)

O JSD_pesos da base compara os pesos das arestas NA ORDEM DE
DEPÓSITO com o protótipo [0,9, 0,011, ...] — o bin de 0,9 alinha
com a PRIMEIRA aresta depositada, não com a maior. Na corrida
base a aresta dominante (Sora->Ren, 1,0) é a segunda depositada,
e o diagnóstico mostrou que, sob concentração, a versão não
ordenada aponta para o LADO ERRADO: com as restantes arestas a
x0,25, o JSD não ordenado SOBE 0,53 -> 0,63 enquanto o ordenado
DESCE 0,37 -> 0,12. A versão ordenada (pesos por ordem
decrescente antes da JSD) é a medida de concentração que o
cenário pretendia; a versão base continua a ser reportada lado
a lado, para a comparação ser limpa. Isto é uma definição do
CENÁRIO (o próprio módulo base diz que o JSD_pesos não é
canónico) — nenhum limiar canónico é redefinido.

## O veto (o que a variante testa)

Em cada tentativa de formação de Símbolo, a variante verifica
primeiro o JSD ordenado: se < JSD_VETO (0,18, limiar do Dan),
a formação é BLOQUEADA e o veto fica registado (tick, agente,
JSD ordenado, ISC, VarPn, e se o Símbolo se teria formado sem
o veto). O veto é um portão real na variante, não um monitor:
a pergunta "o veto dispara?" tem resposta observável.

Implementação do portão: _tentar_simbolo_veto substitui
party_causal._tentar_simbolo DURANTE a corrida (monkey-patch
contido, com try/finally a repor) para que TODOS os agentes
(Ren, Lira, Kael, Sora, Veyra) passem pelo portão — copiar as
cinco funções de comportamento só para trocar uma chamada
seria 200 linhas de duplicação a divergir. A Lira fraca é uma
cópia explícita de _agir_lira com as probabilidades escaladas.
"""

from . import party_causal as pc
from .causal import jsd_bits, prototipo_tirania

# Alavanca principal (UMA): presença reguladora da Lira.
# 1,00 = base; 0,20 = a variante: equalização 0,70 -> 0,14,
# contra-rastro 0,55 -> 0,11.
LIRA_REGULACAO = 0.20


def jsd_pesos_ordenado(grafo):
    """JSD_pesos ORDENADO (definição da VARIANTE, não canónica):
    os pesos das arestas por ordem DECRESCENTE antes da JSD com
    o protótipo de Tirania. É a medida de concentração: invariante
    à ordem de depósito, 0,531 para uniforme, < 0,10 para tirania
    perfeita, como o teste da base. None sem arestas."""
    pesos = grafo.pesos()
    if len(pesos) < 2:
        # Sem arestas, ou só uma: o protótipo de tirania precisa de
        # n >= 2 (e o JSD não é um sinal com menos de 5 — ver o
        # rodar). None, como a base faz sem arestas.
        return None
    return jsd_bits(sorted(pesos, reverse=True), prototipo_tirania(len(pesos)))


def _agir_lira_fraca(est):
    """A Lira com a regulação escalada por LIRA_REGULACAO.
    Estrutura idêntica a party_causal._agir_lira; só as duas
    probabilidades reguladoras mudam (0,70 -> 0,14 e 0,55 -> 0,11).
    A tentativa de Símbolo passa pelo portão de veto da variante
    (pc._tentar_simbolo está remendado durante a corrida)."""
    rng = est.rng
    forca = est.forca_membros()
    if max(forca.values()) - min(forca.values()) > 0.25:
        if rng.random() < 0.70 * LIRA_REGULACAO:
            alvo = est.membro_mais_fraco(excluir="Lira")
            est.depositar("Lira", "Lira", alvo, "equalização", rng.uniform(0.30, 0.45))
            return "depositar_equalizacao"
    if est.isc_party() >= 0.70 and rng.random() < 0.40:
        pc._tentar_simbolo(est, "Lira")
        return "tentar_simbolo"
    forte = est.rastro_mais_forte()
    if forte is not None and forte.peso >= 0.80 and rng.random() < 0.55 * LIRA_REGULACAO:
        outro = est.nome_de_hash(forte.destino if forte.origem == est.hashes["Sistema"] else forte.origem)
        est.depositar("Lira", "Lira", outro, "contra-rastro", rng.uniform(0.30, 0.45))
        return "depositar_contra_rastro"
    if rng.random() < 0.50:
        estavel = est.rastro_mais_estavel("Lira")
        if estavel is not None:
            a = est.nome_de_hash(estavel.origem)
            b = est.nome_de_hash(estavel.destino)
            est.seguir("Lira", a, b)
            return "seguir_estavel"
    return "ocioso"


def _tentar_simbolo_veto(est, agente):
    """request_symbol_formation com o PORTÃO DE VETO da variante:
    se o JSD ordenado < JSD_VETO (0,18), a formação é bloqueada
    mesmo que ISC e VarPn passem. Caso contrário, delega na
    lógica da base (sem dupla contagem de tentativas)."""
    est.tentativas_simbolo += 1
    jsd_ord = jsd_pesos_ordenado(est.subgrafo_party())
    if jsd_ord is not None and jsd_ord < pc.JSD_VETO:
        sub = est.subgrafo_party()
        rel = pc.avaliar_cluster(sub, "SIMBOLO_PARTY_001")
        est.vetos.append(
            {
                "tick": est.tick,
                "agente": agente,
                "jsd_ordenado": round(jsd_ord, 4),
                "jsd_pesos": round(pc.jsd_pesos(sub), 4),
                "isc_local": round(rel["isc_local"], 4),
                "var_ponderada_normalizada": round(rel["var_ponderada_normalizada"], 4),
                "bloqueou_formacao": bool(
                    rel["isc_local"] >= 0.85
                    and rel["var_ponderada_normalizada"] <= 0.36
                ),
            }
        )
        est.eventos.append((est.tick, f"VETO de tirania ({agente})", round(jsd_ord, 4)))
        return False
    rel = pc.avaliar_cluster(est.subgrafo_party(), "SIMBOLO_PARTY_001")
    if rel["simbolo"] and est.simbolo_tick is None:
        est.simbolo_tick = est.tick
        est.simbolo_serial = rel["hash_simbolo"]
        est.eventos.append((est.tick, f"Símbolo formado por {agente}", rel["hash_simbolo"][:12]))
        pc._tentar_meta_simbolo(est, "primeiro Símbolo formado")
    return rel["simbolo"]


def _checkpoint_tyranny(est, jsd_ord):
    """Checkpoint da base + JSD ordenado + nº de vetos até aqui."""
    c = pc._checkpoint(est)
    c["jsd_ordenado"] = round(jsd_ord, 4) if jsd_ord is not None else None
    c["vetos"] = len(est.vetos)
    return c


def rodar_party_causal_tyranny(semente=pc.SEMENTE, n_ticks=pc.N_TICKS):
    """Corre a variante (40 ticks, checkpoint a cada 10) e devolve
    o relatório completo. A base não é alterada: o remendo de
    _tentar_simbolo é reposto no finally, e a corrida base
    continua a dar os mesmos números depois disto."""
    est = pc._Estado(semente)
    est.vetos = []
    agir = dict(pc._AGIR)
    agir["Lira"] = _agir_lira_fraca
    checkpoints = []
    jsd_ord_min = None
    jsd_ord_min_tick = None
    cruzamentos = {}
    original = pc._tentar_simbolo
    pc._tentar_simbolo = _tentar_simbolo_veto
    try:
        for tick in range(1, n_ticks + 1):
            est.tick = tick
            pc._agir_sistema(est)
            for nome in pc.NOMES[:5]:
                agir[nome](est)
            jsd_ord = jsd_pesos_ordenado(est.subgrafo_party())
            # O JSD só é um sinal de tirania com grafo minimamente
            # denso: com 1–2 arestas o protótipo de n<5 bins é
            # degenerado (qualquer aresta dominante "parece" tirania
            # — na primeira corrida os cruzamentos caíram todos no
            # tick 1, artefacto, não tirania). O mínimo e os
            # cruzamentos só contam a partir de 5 arestas.
            if jsd_ord is not None and est.subgrafo_party().n_arestas() >= 5:
                if jsd_ord_min is None or jsd_ord < jsd_ord_min:
                    jsd_ord_min, jsd_ord_min_tick = jsd_ord, tick
                for limiar in (pc.JSD_SUCESSO, pc.JSD_PARCIAL, pc.JSD_VETO):
                    if jsd_ord < limiar and limiar not in cruzamentos:
                        cruzamentos[limiar] = tick
            if tick % pc.CHECKPOINT == 0:
                checkpoints.append(_checkpoint_tyranny(est, jsd_ord))
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
    # Critérios da variante (sobre o JSD ordenado, o monitor que vê
    # concentração): o Gini subiu? O JSD ordenado caiu às zonas de
    # perigo? O veto disparou — e bloqueou alguma formação?
    gini_final = checkpoints[-1]["gini"] if checkpoints else None
    criterios["gini_final_ge_0.30"] = bool(gini_final is not None and gini_final >= 0.30)
    criterios["jsd_ordenado_min_lt_0.28"] = bool(jsd_ord_min is not None and jsd_ord_min < pc.JSD_SUCESSO)
    criterios["jsd_ordenado_min_lt_0.22"] = bool(jsd_ord_min is not None and jsd_ord_min < pc.JSD_PARCIAL)
    criterios["veto_disparou"] = len(est.vetos) > 0
    criterios["veto_bloqueou_formacao"] = any(v["bloqueou_formacao"] for v in est.vetos)
    refs, _, _ = pc.calibrar_lambda2()
    return {
        "variante": "tirania (Lira fraca)",
        "semente": semente,
        "ticks": n_ticks,
        "alavanca": {
            "nome": "presença reguladora da Lira",
            "lira_regulacao": LIRA_REGULACAO,
            "equalizacao_base": 0.70,
            "equalizacao_variante": round(0.70 * LIRA_REGULACAO, 3),
            "contra_rastro_base": 0.55,
            "contra_rastro_variante": round(0.55 * LIRA_REGULACAO, 3),
            "porque_nao_sora": (
                "Sora->Ren já está em 1,0 no fim da corrida base "
                "(27 depósitos, regra max) — subir a faixa dela não "
                "muda nada; o que segura a uniformidade é a Lira."
            ),
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


def imprimir_relatorio(rel):
    """Tabela da variante + comparação lado a lado com a base."""
    print("Isekai Zero — A Party Causal: variante TIRANIA (Lira fraca)")
    print(f"semente={rel['semente']}  ticks={rel['ticks']}  "
          f"lira_regulacao={rel['alavanca']['lira_regulacao']}")
    print("tick | arest | ISC   | VarPn | ISCaux | Gini  | λ₂    | MIP   | JSDp  | JSDord | Vetos | Símbolo")
    for c in rel["checkpoints"]:
        print(
            f"{c['tick']:>4} | {c['n_arestas']:>5} | {c['isc_local']:.3f} | "
            f"{c['var_ponderada_normalizada']:.3f} | {c['isc_aux']:.3f} | "
            f"{c['gini']:.3f} | {c['lambda2']:.3f} | {c['mip_corte_min']:.3f} | "
            f"{c['jsd_pesos'] if c['jsd_pesos'] is not None else '-':>5} | "
            f"{c['jsd_ordenado'] if c['jsd_ordenado'] is not None else '-':>6} | "
            f"{c['vetos']:>5} | {'SIM' if c['simbolo'] else 'não'}"
        )
    ev = rel["eventos"]
    print(f"Símbolo formado no tick: {ev['simbolo_tick']}")
    print(f"Ren seguiu o verdadeiro fraco: {ev['ren_verdadeiro']}x (falso: {ev['ren_falso']}x)")
    print(f"Vetos: {len(ev['vetos'])} -> {ev['vetos']}")
    print(f"Depósitos por agente: {ev['depositos_por_agente']}")
    print(f"JSD ordenado: mínimo {rel['jsd_ordenado_min']} (tick {rel['jsd_ordenado_min_tick']}), "
          f"final {rel['jsd_ordenado_final']}; cruzamentos: {rel['cruzamentos']}")
    print(f"Critérios: {rel['criterios']}")
    print()
    print("Comparação com a base (mesma semente):")
    base = pc.rodar_party_causal()
    print("tick | ISC base/var | VarPn base/var | Gini base/var | JSDp base/var | JSDord var | Símb base/var")
    for b, v in zip(base["checkpoints"], rel["checkpoints"]):
        print(
            f"{b['tick']:>4} | {b['isc_local']:.3f}/{v['isc_local']:.3f} | "
            f"{b['var_ponderada_normalizada']:.3f}/{v['var_ponderada_normalizada']:.3f} | "
            f"{b['gini']:.3f}/{v['gini']:.3f} | "
            f"{b['jsd_pesos']}/{v['jsd_pesos']} | {v['jsd_ordenado']} | "
            f"{'SIM' if b['simbolo'] else 'não'}/{'SIM' if v['simbolo'] else 'não'}"
        )


if __name__ == "__main__":
    imprimir_relatorio(rodar_party_causal_tyranny())
