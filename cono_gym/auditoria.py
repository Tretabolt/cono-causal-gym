"""Auditoria de diversidade — a prova de que a tensão ainda existe.

A tensão que constitui o sistema é a coexistência de duas coisas:
- assimetria log-normal dos pesos (rich-club): poucos rastros fortes,
  muitos fracos;
- coerência: os Símbolos mantêm Var(λ) baixa.

Medimos a assimetria com o coeficiente de Gini dos pesos dos rastros:
0.0 quando todos os pesos são iguais, perto de 1.0 quando um rastro
concentra quase todo o peso. O limiar LIMIAR_GINI = 0,30 é provisório
(v0.1): uma escolha, não um fato derivado. Se ele estiver errado, a
auditoria erra junto — e é por isso que o número vai no relatório.

A coerência já vem garantida pela própria formação de Símbolo
(VarPn <= 0,36 por construção, desde a normalização de 19/11), então a
auditoria verifica a assimetria e relata a VarPn média dos Símbolos
como contexto.

Cuidado honesto: a H_causal (entropia causal entre Símbolos) É
calculada desde 17/11 (`cono_gym/causal.py`, portão PISO H_causal ≥
log2(N)/2) e o servidor a usa na emergência do Meta-Símbolo. A versão
antiga deste parágrafo, que dizia que ela "ainda não é calculada" e
citava a regra invertida H_causal ≤ 0,1, estava errada e foi corrigida
em 20/11.
"""

LIMIAR_GINI = 0.30


def gini(valores):
    """Coeficiente de Gini de uma lista de valores não negativos."""
    xs = sorted(float(v) for v in valores)
    n = len(xs)
    if n == 0:
        return 0.0
    media = sum(xs) / n
    if media == 0:
        return 0.0
    soma_diffs = sum(abs(a - b) for a in xs for b in xs)
    return soma_diffs / (2 * n * n * media)


def auditoria_diversidade(grafo, simbolos, limiar_gini=LIMIAR_GINI, limiar_var=0.36):
    """Relatório da auditoria. `simbolos` é a lista de relatórios de
    avaliar_cluster dos Símbolos registrados. Os limiares são parâmetros
    porque a geodésica pode mudá-los: a auditoria precisa medir a tensão
    sob a regra antiga e sob a nova. Desde 19/11 a Var média é a VarP
    NORMALIZADA (limiar 0,36); a var_lambda antiga e a VarP bruta não
    decidem mais nada."""
    pesos = grafo.pesos()
    g = gini(pesos)
    var_media = (
        sum(s["var_ponderada_normalizada"] for s in simbolos) / len(simbolos)
        if simbolos
        else None
    )
    tensao = g >= limiar_gini and (var_media is not None and var_media <= limiar_var)
    return {
        "gini_pesos": round(g, 4),
        "limiar_gini": LIMIAR_GINI,
        "var_media_simbolos": round(var_media, 4) if var_media is not None else None,
        "n_simbolos": len(simbolos),
        "n_rastros": len(pesos),
        "tensao_presente": tensao,
        "veredito": (
            "Tensão presente: assimetria e coerência coexistem."
            if tensao
            else "Sem tensão: ou os pesos são homogêneos demais (sem rich-club), "
            "ou não há Símbolos coerentes para sustentar a diversidade."
        ),
    }
