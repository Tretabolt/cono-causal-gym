"""H_causal: entropia causal entre Símbolos — definição real.

CORREÇÃO (17/11, informação do Dan): a versão anterior deste módulo
estava INVERTIDA. Ela media a entropia do peso dos rastros ENTRE os
Símbolos e exigia H_causal ≤ 0,1 como teto — o que premiaria a
concentração, ou seja, a própria Tirania Causal. A definição certa,
consolidada no glossário do projeto e com teste TDD no harness, é:

    H_causal = -Σ P(ISC_i) · log2(P(ISC_i)),  P(ISC_i) = ISC_i / Σ ISC_j

a entropia de Shannon (base 2) sobre a distribuição normalizada dos
ISCs entre os N Símbolos. H ALTO = diversidade (ordem sem tirania);
H BAIXO = um único Símbolo monopoliza (tirania, H -> 0).

O portão de emergência do Meta-Símbolo é um PISO, não um teto:
    1. todos os Símbolos componentes válidos;
    2. ISC_Global (média) ≥ 0,80 (integração);
    3. H_causal ≥ log2(N) / 2 (diversidade mínima).

E a JSD entra como veto: se a distribuição projetada P_nova fica
perto demais do protótipo de Tirania, a mudança é vetada. O protótipo
para N Símbolos é [0,9] + [0,1/(N-1)] × (N-1) — para N=4, é
[0,9, 0,033, 0,033, 0,034], o protótipo do glossário. O veto dispara
quando JSD(P_nova, Tirania) fica abaixo de JSD(uniforme, Tirania) -
0,05: a mudança deixa a distribuição significativamente mais perto da
tirania do que uma distribuição perfeitamente equilibrada estaria.
(Regra v0.1: a margem 0,05 é uma escolha, não um teorema — aprovada
pelo Dan em 19/11/2026.)

Ciência por trás (dada pelo Dan): forças entrópicas causais
(Wissner-Gross & Freer, PRL 2013) — inteligência como maximização da
diversidade de futuros causais; emergência causal (Hoel, 2017/2025) —
a macroescala precisa evitar degenerescência; IIT (Tononi) — integração
sem diferenciação é monotonia (crise epiléptica), não cognição.

Nota honesta sobre o gym: como um Símbolo válido exige ISC ≥ 0,85,
os ISCs dos Símbolos válidos vivem em [0,85, 1,0] — a distribuição é
sempre quase uniforme, então os portões 2 e 3 são automaticamente
satisfeitos quando há 2+ Símbolos válidos. No gym, eles não
discriminam além da validade; discriminam no harness, onde shards
podem ser fracos (o exemplo de tirania [0,90, 0,033, 0,033, 0,034]).
O que discrimina no gym continua sendo a tensão (Gini) e a contagem
de Símbolos válidos — e o veto JSD, que morde quando a projeção inclui
um mega-símbolo de ISC baixo.
"""

import math

MIN_ISC_GLOBAL = 0.80
MARGEM_JSD_VETO = 0.05


def causal_entropy_bits(iscs):
    """H_causal em bits sobre a lista de ISCs. Lista vazia -> 0,0."""
    total = sum(v for v in iscs if v > 0.0)
    if total <= 0.0:
        return 0.0
    return -sum(
        (v / total) * math.log2(v / total) for v in iscs if v > 0.0
    )


def prototipo_tirania(n):
    """Protótipo de Tirania Causal para n Símbolos: um domina 90%."""
    if n < 2:
        raise ValueError("o protótipo de tirania precisa de ao menos 2 Símbolos")
    return [0.9] + [0.1 / (n - 1)] * (n - 1)


def jsd_bits(p, q):
    """Divergência de Jensen-Shannon em bits (base 2), em [0, 1]."""
    if len(p) != len(q) or len(p) == 0:
        raise ValueError("as distribuições precisam ter o mesmo tamanho > 0")
    sp, sq = sum(p), sum(q)
    if sp <= 0.0 or sq <= 0.0:
        raise ValueError("a soma das distribuições precisa ser positiva")
    pn = [x / sp for x in p]
    qn = [x / sq for x in q]
    m = [0.5 * (a + b) for a, b in zip(pn, qn)]

    def kl2(a, b):
        return sum(
            x * math.log2(x / y) for x, y in zip(a, b) if x > 0.0 and y > 0.0
        )

    return min(1.0, max(0.0, 0.5 * kl2(pn, m) + 0.5 * kl2(qn, m)))


def _normalizar(iscs):
    total = sum(iscs)
    if total <= 0.0:
        raise ValueError("ISCs precisam somar mais que zero")
    return [v / total for v in iscs]


def jsd_para_tirania(iscs):
    """JSD entre a distribuição normalizada dos ISCs e o protótipo de
    Tirania. None quando há menos de 2 ISCs."""
    if len(iscs) < 2:
        return None
    return jsd_bits(_normalizar(iscs), prototipo_tirania(len(iscs)))


def jsd_uniforme_para_tirania(n):
    """JSD entre a distribuição perfeitamente equilibrada e o protótipo
    de Tirania — a referência do veto."""
    if n < 2:
        return None
    return jsd_bits([1.0 / n] * n, prototipo_tirania(n))


def veto_jsd(iscs_nova, margem=MARGEM_JSD_VETO):
    """Veto JSD: a distribuição projetada está significativamente mais
    perto da Tirania do que uma distribuição equilibrada estaria?
    Retorna (vetado, jsd_nova, jsd_uniforme). Sem distribuição
    projetada (menos de 2 ISCs), não há o que vetar."""
    if len(iscs_nova) < 2:
        return False, None, None
    jsd_nova = jsd_para_tirania(iscs_nova)
    jsd_uniforme = jsd_uniforme_para_tirania(len(iscs_nova))
    return jsd_nova < jsd_uniforme - margem, jsd_nova, jsd_uniforme


def pode_emergir_meta_simbolo(iscs, tensao_presente, min_isc_global=MIN_ISC_GLOBAL):
    """Portão de emergência do Meta-Símbolo. Retorna
    (emergiu, isc_global, h_causal, h_minimo)."""
    n = len(iscs)
    if n < 2:
        return False, 0.0, 0.0, 0.0
    isc_global = sum(iscs) / n
    h_causal = causal_entropy_bits(iscs)
    h_minimo = math.log2(n) / 2.0
    emergiu = (
        tensao_presente
        and isc_global >= min_isc_global
        and h_causal >= h_minimo
    )
    return emergiu, isc_global, h_causal, h_minimo
