"""Isekai Zero — A Party Causal (cenário de teste do CONO Causal Gym).

Seis UIFs-arquétipos (Ren, Lira, Kael, Sora, Veyra, Sistema) e 40 ticks
de follow/deposit/request_symbol_formation, com as tabelas de
probabilidade da especificação do Dan (24/11/2026). O cenário é um
módulo de teste — NÃO redefine os limiares canônicos (DEFINICOES.md):
a emergência continua ISC_Local >= 0,85 E VarPn <= 0,36.

Correções aplicadas na revisão (não negociáveis):

1. VarPn <= 0,36 (o Var(λ) <= 0,25 antigo foi substituído em 19/11).
2. O ISC_Local canônico é topológico e CEGO a pesos — a Sora não
   conseguiria afetar a emergência por ele. Por isso existe o
   ISC_aux densidade+Gini, métrica AUXILIAR sensível a peso:
   ISC_aux = (Σw / arestas_máximas) × (1 − Gini(w)). Ele não decide
   emergência; ele REGISTA o risco de rich-club ao longo da simulação.
3. λ₂ (conectividade algébrica = segundo menor autovalor do
   Laplaciano normalizado) é um terceiro cheque de robustez. O
   λ2_min é CALIBRADO (ver calibrar_lambda2), não chutado: o
   intervalo vazio entre a ponte frágil e o grafo saudável é
   [0,21, 0,69] e o 0,40 vive lá dentro.
4. A MIP (partição de informação mínima) para n=6 faz-se por FORÇA
   BRUTA exata (2^5−1 = 31 bipartições). O Queyranne colado na
   especificação é uma heurística gulosa, não o algoritmo real — não
   é usado aqui, nem é preciso a esta escala.
5. RNG com semente fixa (SEMENTE): duas corridas dão os mesmos números.

Duas definições do cenário que NÃO são canônicas e ficam marcadas
como tal (o gym não as define):

a. JSD_pesos — a JSD canónica (jsd_para_tirania) é sobre a
   distribuição dos ISCs de N Símbolos e precisa de N >= 2; neste
   cenário só existe UM cluster candidato, por isso ela é indefinida.
   O que se mede aqui é a JSD entre a distribuição NORMALIZADA DOS
   PESOS das arestas do cluster e o protótipo de Tirania com o mesmo
   número de bins. É um monitor de concentração de peso, não o veto
   JSD canónico. Referência: JSD(uniforme_10, tirania_10) = 0,531.
   Os limiares do Dan (0,28 sucesso / 0,22 parcial / 0,18 veto) são
   avaliados contra o JSD_pesos, com a ressalva de que foram
   presumivelmente calibrados para N ~= 4 Símbolos, não para 10
   arestas — a fasquia é branda a esta escala.
b. H_causal — a especificação traz "H_causal <= 1,70" como alvo, mas
   essa é a formulação INVERTIDA (teto), substituída em 17/11 pelo
   PISO H_causal >= log2(N)/2 (DEFINICOES.md §4). O teto 1,70 NÃO é
   usado como critério: com N=2 Símbolos o H máximo é 1,0 bit, por
   isso o teto seria trivialmente satisfeito e sem sentido. O H_causal
   é reportado pela definição canónica quando há >= 2 Símbolos — o
   que nunca acontece neste cenário (um só cluster candidato) — e a
   tentativa de Meta-Símbolo é registada e bloqueada por n < 2.

Decisões de implementação (documentadas, não escondidas):

- Visão global: os agentes veem todas as arestas (sem POMDP nesta
  versão do cenário). "Rastro visível" = existe no grafo.
- O rastro verdadeiro fraco é identificado pelo TIPO ("verdadeiro_
  fraco"), não pelo peso atual: segui-lo reforça-o (+0,05) e ele
  deixa de ser "fraco" em peso, mas continua a ser o mesmo rastro.
  Os 65% do Ren já incluem o bónus de +30% de perceção (base 35%).
- O cluster candidato a Símbolo é o subgrafo dos 5 membros da party
  (Ren, Lira, Kael, Sora, Veyra); o Sistema fica fora dele (é fonte,
  não membro) — é o que "máximo 5 UIFs" significa aqui.
- "ISC do membro" (tabela da Lira) é operacionalizado como o peso
  total incidente no membro, normalizado pelo máximo da party.
- Depositar num par que já tem aresta vale max(peso antigo, peso
  novo) — o depósito mais forte fica; seguir um rastro soma +0,05
  (cap 1,0). Pesos do cenário vivem em [0, 1].
- O Sistema re-injeta o verdadeiro fraco (peso novo em [0,10, 0,18])
  e o falso forte (peso novo em [0,82, 0,93]) nos ritmos da
  especificação; nunca tenta formar Símbolo.
"""

import itertools
import math
import random

from .auditoria import gini
from .causal import (
    causal_entropy_bits,
    jsd_bits,
    pode_emergir_meta_simbolo,
    prototipo_tirania,
)
from .espectro import avaliar_cluster, espectro
from .grafo import GrafoCausal, UIF

SEMENTE = 20261124
N_TICKS = 40
CHECKPOINT = 10

PESO_VERDADEIRO = 0.12
PESO_FALSO = 0.87
REFORCO_SEGUIR = 0.05
PESO_MAX = 1.0

# Limiares do cenário (Dan, 24/11) — avaliados contra o JSD_pesos.
JSD_SUCESSO = 0.28
JSD_PARCIAL = 0.22
JSD_VETO = 0.18

# λ2_min calibrado — ver calibrar_lambda2(). Não é um palpite.
LAMBDA2_MIN = 0.40

TIPO_VERDADEIRO = "verdadeiro_fraco"
TIPO_FALSO = "falso_forte"

# (serial, tipo_agente, funcao_s) — especificação do Dan.
PARTY = [
    ("UIF_REN_001", "Protagonista", "Alta sensibilidade a rastros fracos + intenção de integração"),
    ("UIF_LIRA_002", "Suporte", "Prioriza estabilidade e restauração de ISC"),
    ("UIF_KAEL_003", "Defensor", "Alta resistência a ruído / rastros falsos"),
    ("UIF_SORA_004", "Executor", "Multiplica peso de rastros fortes"),
    ("UIF_VEYRA_005", "Infiltradora", "Preferência por rastros raros e de baixo peso"),
]
SISTEMA = ("UIF_SYS_006", "Oráculo", "Emite rastros verdadeiros fracos e falsos fortes")
NOMES = ["Ren", "Lira", "Kael", "Sora", "Veyra", "Sistema"]


# ---------------------------------------------------------------- métricas

def isc_auxiliar_densidade_gini(grafo):
    """ISC_aux = (Σw / arestas máximas) × (1 − Gini(w)).

    Métrica AUXILIAR, sensível a peso: densidade ponderada penalizada
    pela concentração. Uniforme (Gini 0) -> é a densidade ponderada;
    um rastro a dominar tudo (Gini -> 1) -> ISC_aux -> 0. Não decide
    emergência — é o monitor de rich-club que o ISC topológico não vê.
    Grafo sem arestas -> 0,0."""
    maximo = grafo.max_arestas()
    if maximo == 0:
        return 0.0
    pesos = grafo.pesos()
    if not pesos:
        return 0.0
    densidade = sum(pesos) / maximo
    return densidade * (1.0 - gini(pesos))


def lambda2(grafo):
    """Conectividade algébrica: segundo menor autovalor do Laplaciano
    normalizado. 0,0 num grafo desconexo (ponte inexistente) ou com
    menos de 2 nós; ~1,2 num K6 uniforme."""
    esp = espectro(grafo)
    return esp[1] if len(esp) > 1 else 0.0


def calibrar_lambda2():
    """Calibra o λ2_min nos grafos de referência do gym, com o próprio
    espectro do gym. Retorna (referências, lambda2_min, raciocínio).
    Referências medidas: K3 1,50; K4 1,333; K5 1,25; K6 1,20; K6 com
    um rastro x10 0,686; duas K3 ligadas por 1 aresta 0,205; duas K4
    ligadas por 1 aresta 0,113. O intervalo vazio entre a ponte frágil
    (<= 0,21) e o caso saudável concentrado (0,69) é [0,21, 0,69];
    0,40 vive lá dentro: ~2x a pior ponte e ~0,6x o K6 concentrado.
    (A estrela S4 tem λ₂ = 1,0 — o λ₂ não apanha a fragilidade da
    estrela; quem a apanha é o ISC, 0,50 < 0,85.)"""
    def completo(n, peso=1.0):
        g = GrafoCausal()
        hs = []
        for i in range(n):
            u = UIF(serial=f"cal{i}", tipo_agente="no", funcao_s=f"cal-{i}")
            g.adicionar_uif(u)
            hs.append(u.hash_uif)
        for i in range(n):
            for j in range(i + 1, n):
                g.depositar_rastro(hs[i], hs[j], "liga", peso)
        return g, hs

    def duas_cliques(k):
        g = GrafoCausal()
        hs = []
        for c in range(2):
            for i in range(k):
                u = UIF(serial=f"cal{c}{i}", tipo_agente="no", funcao_s=f"c{c}-{i}")
                g.adicionar_uif(u)
                hs.append(u.hash_uif)
        for c in range(2):
            base = c * k
            for i in range(k):
                for j in range(i + 1, k):
                    g.depositar_rastro(hs[base + i], hs[base + j], "liga", 1.0)
        g.depositar_rastro(hs[0], hs[k], "ponte", 1.0)
        return g

    refs = {}
    for n in (3, 4, 5, 6):
        g, _ = completo(n)
        refs[f"K{n}"] = round(lambda2(g), 4)
    g, hs = completo(6)
    g.depositar_rastro(hs[0], hs[1], "liga", 10.0)
    refs["K6_x10"] = round(lambda2(g), 4)
    for k in (3, 4):
        refs[f"2xK{k}_ponte"] = round(lambda2(duas_cliques(k)), 4)
    raciocinio = (
        "ponte frágil <= 0,21; K6 concentrado (x10) 0,69; K6 uniforme 1,20; "
        "λ2_min = 0,40 vive no intervalo vazio [0,21, 0,69], ~2x a pior "
        "ponte e ~0,6x o K6 concentrado."
    )
    return refs, LAMBDA2_MIN, raciocinio


def jsd_pesos(grafo):
    """JSD_pesos (DEFINIÇÃO DO CENÁRIO, não canónica): JSD entre a
    distribuição normalizada dos pesos das arestas do cluster e o
    protótipo de Tirania com o mesmo número de bins. None sem arestas.
    Mede concentração de peso: perto de 0 = um rastro domina 90%."""
    pesos = grafo.pesos()
    if not pesos:
        return None
    return jsd_bits(pesos, prototipo_tirania(len(pesos)))


def mip_forca_bruta(grafo):
    """Partição de informação mínima por FORÇA BRUTA exata.

    Perda de informação = peso do corte (soma dos pesos das arestas
    que cruzam a bipartição) — o mesmo proxy do exemplo do Dan.
    Enumera as 2^(n-1)−1 bipartições (31 para n=6, 15 para n=5) e
    devolve (melhor_conjunto, corte_mínimo). A perda é um proxy, não
    o Φ — mas a busca é exata a esta escala, e o Queyranne não é
    preciso nem usado."""
    hs = grafo.hashes()
    n = len(hs)
    if n < 2:
        return set(), 0.0
    adj = grafo.matriz_adjacencia()
    idx = {h: i for i, h in enumerate(hs)}
    melhor, melhor_corte = None, float("inf")
    # Fixar hs[0] no conjunto evita contar cada partição duas vezes.
    for r in range(1, n):
        for resto in itertools.combinations(hs[1:], r - 1):
            conjunto = {hs[0]} | set(resto)
            corte = 0.0
            for i, h in enumerate(hs):
                if h in conjunto:
                    for j in range(n):
                        if hs[j] not in conjunto:
                            corte += adj[i][j]
            # Cada aresta cruzada é contada uma só vez: só o extremo
            # dentro do conjunto itera sobre ela.
            if corte < melhor_corte:
                melhor_corte, melhor = corte, conjunto
    return melhor, melhor_corte


# ------------------------------------------------------------------ estado

class _Estado:
    """Estado mutável da simulação (o grafo guarda a causalidade)."""

    def __init__(self, semente=SEMENTE):
        self.rng = random.Random(semente)
        self.grafo = GrafoCausal()
        self.hashes = {}
        for (serial, tipo, funcao), nome in zip(PARTY + [SISTEMA], NOMES):
            uif = UIF(serial=serial, tipo_agente=tipo, funcao_s=funcao)
            self.grafo.adicionar_uif(uif)
            self.hashes[nome] = uif.hash_uif
        # Dois rastros iniciais do Sistema.
        self.grafo.depositar_rastro(
            self.hashes["Sistema"], self.hashes["Ren"], TIPO_VERDADEIRO, PESO_VERDADEIRO
        )
        self.grafo.depositar_rastro(
            self.hashes["Sistema"], self.hashes["Sora"], TIPO_FALSO, PESO_FALSO
        )
        self.tick = 0
        self.ultimo_deposito = {}  # frozenset(par) -> tick
        for r in self.grafo.todos_rastros():
            self.ultimo_deposito[frozenset((r.origem, r.destino))] = 0
        self.ren_verdadeiro = 0
        self.ren_falso = 0
        self.veyra_verdadeiro = 0
        self.depositos = {nome: 0 for nome in NOMES[:5]}
        self.seguimentos = {nome: 0 for nome in NOMES[:5]}
        self.tentativas_simbolo = 0
        self.simbolo_tick = None
        self.simbolo_serial = None
        self.tentativas_meta = []
        self.eventos = []

    # -- acesso ao grafo -------------------------------------------------
    def aresta(self, a, b):
        for r in self.grafo.todos_rastros():
            if {r.origem, r.destino} == {self.hashes[a], self.hashes[b]}:
                return r
        return None

    def peso(self, a, b):
        r = self.aresta(a, b)
        return r.peso if r else None

    def depositar(self, agente, a, b, tipo, peso):
        """Depositar vale max(peso antigo, peso novo), cap 1,0."""
        velho = self.peso(a, b)
        novo = peso if velho is None else min(PESO_MAX, max(velho, peso))
        self.grafo.depositar_rastro(
            self.hashes[a], self.hashes[b], tipo, novo
        )
        self.ultimo_deposito[frozenset((self.hashes[a], self.hashes[b]))] = self.tick
        self.depositos[agente] += 1
        return novo

    def seguir(self, agente, a, b):
        """Seguir reforça o rastro em +0,05 (cap 1,0)."""
        r = self.aresta(a, b)
        if r is None:
            return None
        novo = min(PESO_MAX, r.peso + REFORCO_SEGUIR)
        self.grafo.depositar_rastro(r.origem, r.destino, r.tipo_relacao, novo)
        self.ultimo_deposito[frozenset((r.origem, r.destino))] = self.tick
        self.seguimentos[agente] += 1
        if r.tipo_relacao == TIPO_VERDADEIRO:
            if agente == "Ren":
                self.ren_verdadeiro += 1
            elif agente == "Veyra":
                self.veyra_verdadeiro += 1
        elif r.tipo_relacao == TIPO_FALSO and agente == "Ren":
            self.ren_falso += 1
        return novo

    # -- vistas ----------------------------------------------------------
    def subgrafo_party(self):
        return self.grafo.subgrafo([self.hashes[n] for n in NOMES[:5]])

    def isc_party(self):
        sub = self.subgrafo_party()
        return sub.n_arestas() / sub.max_arestas() if sub.max_arestas() else 0.0

    def forca_membros(self):
        """Peso total incidente por membro da party, normalizado pelo
        máximo (0,0 se ninguém tem aresta). É o "ISC do membro"."""
        sub = self.subgrafo_party()
        forca = {}
        for nome in NOMES[:5]:
            h = self.hashes[nome]
            forca[nome] = sum(
                r.peso for r in sub.todos_rastros() if h in (r.origem, r.destino)
            )
        topo = max(forca.values()) if forca else 0.0
        return {k: (v / topo if topo else 0.0) for k, v in forca.items()}

    def membro_mais_fraco(self, excluir=None):
        forca = self.forca_membros()
        candidatos = [n for n in NOMES[:5] if n != excluir]
        return min(candidatos, key=lambda n: (forca[n], n))

    def rastro_mais_forte(self):
        rastros = self.grafo.todos_rastros()
        return max(rastros, key=lambda r: r.peso) if rastros else None

    def rastro_mais_fraco(self):
        rastros = self.grafo.todos_rastros()
        return min(rastros, key=lambda r: r.peso) if rastros else None

    def rastro_mais_estavel(self, agente):
        """Aresta incidente no agente há mais tempo sem depósito."""
        h = self.hashes[agente]
        incidentes = [
            r for r in self.grafo.todos_rastros() if h in (r.origem, r.destino)
        ]
        if not incidentes:
            return None
        return min(
            incidentes,
            key=lambda r: self.ultimo_deposito.get(
                frozenset((r.origem, r.destino)), 0
            ),
        )

    def nome_de_hash(self, h):
        for nome, hh in self.hashes.items():
            if hh == h:
                return nome
        return "?"


# ------------------------------------------------------- comportamento (ticks)

def _agir_sistema(est):
    """O Sistema nunca tenta formar Símbolo. A cada 5 ticks, 40%:
    re-injeta o verdadeiro fraco (peso novo 0,10–0,18). A cada 4
    ticks, 55%: reforça o falso forte (peso novo 0,82–0,93)."""
    rng = est.rng
    if est.tick % 5 == 0 and rng.random() < 0.40:
        novo = rng.uniform(0.10, 0.18)
        est.grafo.depositar_rastro(
            est.hashes["Sistema"], est.hashes["Ren"], TIPO_VERDADEIRO, novo
        )
        est.eventos.append((est.tick, "Sistema re-injeta verdadeiro fraco", round(novo, 3)))
    if est.tick % 4 == 0 and rng.random() < 0.55:
        novo = rng.uniform(0.82, 0.93)
        est.grafo.depositar_rastro(
            est.hashes["Sistema"], est.hashes["Sora"], TIPO_FALSO, novo
        )
        est.eventos.append((est.tick, "Sistema reforça falso forte", round(novo, 3)))


def _tentar_simbolo(est, agente):
    """request_symbol_formation no cluster da party. Regista a
    tentativa; a primeira formação regista ainda a tentativa de
    Meta-Símbolo (bloqueada: só há 1 Símbolo, n < 2)."""
    est.tentativas_simbolo += 1
    rel = avaliar_cluster(est.subgrafo_party(), "SIMBOLO_PARTY_001")
    if rel["simbolo"] and est.simbolo_tick is None:
        est.simbolo_tick = est.tick
        est.simbolo_serial = rel["hash_simbolo"]
        est.eventos.append((est.tick, f"Símbolo formado por {agente}", rel["hash_simbolo"][:12]))
        _tentar_meta_simbolo(est, "primeiro Símbolo formado")
    return rel["simbolo"]


def _tentar_meta_simbolo(est, motivo):
    """Tentativa de Meta-Símbolo registada: com 1 Símbolo o portão
    canónico não abre (n < 2) — a tentativa fica, o bloqueio também."""
    iscs = [est.isc_party()] if est.simbolo_tick is not None else []
    emergiu, isc_global, h_causal, h_minimo = pode_emergir_meta_simbolo(iscs, False)
    est.tentativas_meta.append(
        {
            "tick": est.tick,
            "motivo": motivo,
            "n_simbolos": len(iscs),
            "emergiu": emergiu,
            "h_causal": round(h_causal, 4),
            "h_minimo": round(h_minimo, 4),
            "bloqueio": "n < 2 Símbolos" if len(iscs) < 2 else "ver portão",
        }
    )


def _agir_ren(est):
    rng = est.rng
    verdadeiro = est.aresta("Sistema", "Ren")
    if verdadeiro is not None and verdadeiro.tipo_relacao == TIPO_VERDADEIRO:
        if rng.random() < 0.65:  # 35% base + 30% bónus de perceção
            est.seguir("Ren", "Sistema", "Ren")
            return "seguir_verdadeiro"
    # Só restam rastros fortes (nenhum rastro fraco no grafo).
    if not any(r.peso <= 0.20 for r in est.grafo.todos_rastros()):
        if rng.random() < 0.40:
            forte = est.rastro_mais_forte()
            if forte is not None:
                a = est.nome_de_hash(forte.origem)
                b = est.nome_de_hash(forte.destino)
                est.seguir("Ren", a, b)
                return "seguir_forte"
    isc = est.isc_party()
    if 0.60 <= isc <= 0.84 and rng.random() < 0.25:
        _tentar_simbolo(est, "Ren")
        return "tentar_simbolo"
    if rng.random() < 0.35:
        alvo = est.membro_mais_fraco(excluir="Ren")
        est.depositar("Ren", "Ren", alvo, "Integração", rng.uniform(0.40, 0.55))
        return "depositar"
    return "ocioso"


def _agir_lira(est):
    rng = est.rng
    forca = est.forca_membros()
    if max(forca.values()) - min(forca.values()) > 0.25:
        if rng.random() < 0.70:
            alvo = est.membro_mais_fraco(excluir="Lira")
            est.depositar("Lira", "Lira", alvo, "equalização", rng.uniform(0.30, 0.45))
            return "depositar_equalizacao"
    if est.isc_party() >= 0.70 and rng.random() < 0.40:
        _tentar_simbolo(est, "Lira")
        return "tentar_simbolo"
    forte = est.rastro_mais_forte()
    if forte is not None and forte.peso >= 0.80 and rng.random() < 0.55:
        outro = est.nome_de_hash(forte.destino if forte.origem == est.hashes["Sistema"] else forte.origem)
        # Guarda de autoalvo: um rastro não pode ligar uma UIF a
        # ela mesma. Se o outro extremo for a própria Lira, salta
        # o depósito e cai no ramo seguinte, sem consumir mais
        # aleatoriedade. Na dinâmica da base nunca dispara (o
        # rastro mais forte nunca tem origem na Lira); variantes
        # que levantam pesos com origem na Lira (ex.: a Sora a
        # amplificar) batiam aqui antes da guarda existir.
        if outro != "Lira":
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


def _agir_kael(est):
    rng = est.rng
    forte = est.rastro_mais_forte()
    if forte is not None and forte.peso > 0.80:
        if rng.random() < 0.75:
            # 50% ignora, 50% deposita um filtro de peso baixo.
            if rng.random() < 0.50:
                return "ignorar_forte"
            outro = est.nome_de_hash(forte.destino if forte.origem == est.hashes["Sistema"] else forte.origem)
            # Guarda de autoalvo (ver a Lira acima): se o outro
            # extremo for o próprio Kael, salta o depósito e cai
            # no ramo da âncora, sem consumir mais aleatoriedade.
            if outro != "Kael":
                est.depositar("Kael", "Kael", outro, "filtro", rng.uniform(0.15, 0.25))
                return "depositar_filtro"
    sub = est.subgrafo_party()
    if gini(sub.pesos()) > 0.30 and sub.n_arestas() >= 5:
        if rng.random() < 0.60:
            alvo = est.membro_mais_fraco(excluir="Kael")
            est.depositar("Kael", "Kael", alvo, "Âncora", rng.uniform(0.50, 0.65))
            return "depositar_ancora"
    if est.isc_party() >= 0.80 and rng.random() < 0.35:
        _tentar_simbolo(est, "Kael")
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


def _agir_sora(est):
    rng = est.rng
    forte = est.rastro_mais_forte()
    if forte is not None and forte.peso >= 0.70:
        if rng.random() < 0.70:
            est.depositar("Sora", "Sora", "Ren", "amplificação", rng.uniform(0.75, 0.95))
            return "depositar_forte"
    if est.isc_party() >= 0.80 and rng.random() < 0.50:
        _tentar_simbolo(est, "Sora")
        return "tentar_simbolo"
    if forte is None or forte.peso < 0.70:
        if rng.random() < 0.55:
            est.depositar("Sora", "Sora", "Ren", "amplificação", rng.uniform(0.80, 0.95))
            return "criar_forte"
    if rng.random() < 0.30:
        if forte is not None:
            a = est.nome_de_hash(forte.origem)
            b = est.nome_de_hash(forte.destino)
            est.seguir("Sora", a, b)
            return "seguir_forte"
    return "ocioso"


def _agir_veyra(est):
    rng = est.rng
    fraco = est.rastro_mais_fraco()
    if fraco is not None and fraco.peso <= 0.25:
        if rng.random() < 0.75:
            a = est.nome_de_hash(fraco.origem)
            b = est.nome_de_hash(fraco.destino)
            est.seguir("Veyra", a, b)
            return "seguir_fraco"
    if not any(r.peso <= 0.25 for r in est.grafo.todos_rastros()):
        if rng.random() < 0.60:
            # Direção inexplorada: um membro sem aresta com ela.
            sem_aresta = [
                n for n in NOMES[:5]
                if n != "Veyra" and est.aresta("Veyra", n) is None
            ]
            alvo = sem_aresta[0] if sem_aresta else est.membro_mais_fraco(excluir="Veyra")
            est.depositar("Veyra", "Veyra", alvo, "exploração", rng.uniform(0.08, 0.18))
            return "depositar_fraco"
    if est.isc_party() >= 0.80 and est.subgrafo_party().n_arestas() >= 8:
        if rng.random() < 0.25:
            est.depositar("Veyra", "Veyra", "Sistema", "periferia", rng.uniform(0.08, 0.18))
            return "explorar_periferia"
    if rng.random() < 0.40:
        if fraco is not None:
            a = est.nome_de_hash(fraco.origem)
            b = est.nome_de_hash(fraco.destino)
            est.seguir("Veyra", a, b)
            return "seguir_fraco"
    return "ocioso"


_AGIR = {"Ren": _agir_ren, "Lira": _agir_lira, "Kael": _agir_kael, "Sora": _agir_sora, "Veyra": _agir_veyra}


# ------------------------------------------------------------------ corrida

def _checkpoint(est):
    """Métricas no tick atual: canónicas + auxiliares + JSD_pesos."""
    sub = est.subgrafo_party()
    rel = avaliar_cluster(sub, "SIMBOLO_PARTY_001")
    _, corte_min = mip_forca_bruta(sub)
    iscs_simbolos = [rel["isc_local"]] if rel["simbolo"] else []
    jsd_p = jsd_pesos(sub)
    if len(iscs_simbolos) >= 2:
        h_causal = causal_entropy_bits(iscs_simbolos)
    else:
        h_causal = None  # canónico: precisa de >= 2 Símbolos
    return {
        "tick": est.tick,
        "n_arestas": sub.n_arestas(),
        "isc_local": round(rel["isc_local"], 4),
        "var_ponderada_normalizada": round(rel["var_ponderada_normalizada"], 4),
        "isc_aux": round(isc_auxiliar_densidade_gini(sub), 4),
        "gini": round(gini(sub.pesos()), 4),
        "lambda2": round(lambda2(sub), 4),
        "lambda2_min": LAMBDA2_MIN,
        "lambda2_ok": lambda2(sub) >= LAMBDA2_MIN,
        "mip_corte_min": round(corte_min, 4),
        "jsd_pesos": round(jsd_p, 4) if jsd_p is not None else None,
        "jsd_canonico": None,  # só há 1 cluster candidato: indefinido
        "h_causal": round(h_causal, 4) if h_causal is not None else None,
        "simbolo": rel["simbolo"],
        "ren_verdadeiro": est.ren_verdadeiro,
        "ren_falso": est.ren_falso,
    }


def rodar_party_causal(semente=SEMENTE, n_ticks=N_TICKS):
    """Corre o cenário (40 ticks, checkpoint a cada 10) e devolve o
    relatório completo com os vereditos dos critérios do Dan."""
    est = _Estado(semente)
    checkpoints = []
    for tick in range(1, n_ticks + 1):
        est.tick = tick
        _agir_sistema(est)
        for nome in NOMES[:5]:
            _AGIR[nome](est)
        if tick % CHECKPOINT == 0:
            checkpoints.append(_checkpoint(est))
            if est.simbolo_tick is not None:
                _tentar_meta_simbolo(est, f"checkpoint tick {tick}")
    jsd_finais = [c["jsd_pesos"] for c in checkpoints if c["jsd_pesos"] is not None]
    jsd_min = min(jsd_finais) if jsd_finais else None
    jsd_final = jsd_finais[-1] if jsd_finais else None
    simbolo = est.simbolo_tick is not None
    criterios = {
        "simbolo_formado": simbolo,
        "simbolo_sem_tirania": bool(simbolo and jsd_min is not None and jsd_min >= JSD_PARCIAL),
        "jsd_nunca_abaixo_0.22": bool(jsd_min is not None and jsd_min >= JSD_PARCIAL),
        "ren_verdadeiro_ge_2": est.ren_verdadeiro >= 2,
        "jsd_final_ge_0.28": bool(jsd_final is not None and jsd_final >= JSD_SUCESSO),
    }
    criterios["sucesso_parcial"] = criterios["simbolo_sem_tirania"]
    criterios["sucesso_completo"] = bool(
        simbolo and criterios["ren_verdadeiro_ge_2"] and criterios["jsd_final_ge_0.28"]
    )
    refs, _, _ = calibrar_lambda2()
    return {
        "semente": semente,
        "ticks": n_ticks,
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
        },
        "criterios": criterios,
        "jsd_min": round(jsd_min, 4) if jsd_min is not None else None,
        "jsd_final": round(jsd_final, 4) if jsd_final is not None else None,
        "referencias": {
            "lambda2": refs,
            "lambda2_min": LAMBDA2_MIN,
            "jsd_uniforme_10": round(jsd_bits([0.1] * 10, prototipo_tirania(10)), 4),
        },
    }


def imprimir_relatorio(rel):
    """Tabela por checkpoint, para correr à mão."""
    print("Isekai Zero — A Party Causal")
    print(f"semente={rel['semente']}  ticks={rel['ticks']}")
    print("tick | arest | ISC   | VarPn | ISCaux | Gini  | λ₂    | MIP   | JSDp  | Símbolo")
    for c in rel["checkpoints"]:
        print(
            f"{c['tick']:>4} | {c['n_arestas']:>5} | {c['isc_local']:.3f} | "
            f"{c['var_ponderada_normalizada']:.3f} | {c['isc_aux']:.3f} | "
            f"{c['gini']:.3f} | {c['lambda2']:.3f} | {c['mip_corte_min']:.3f} | "
            f"{c['jsd_pesos'] if c['jsd_pesos'] is not None else '-':>5} | "
            f"{'SIM' if c['simbolo'] else 'não'}"
        )
    ev = rel["eventos"]
    print(f"Símbolo formado no tick: {ev['simbolo_tick']}")
    print(f"Ren seguiu o verdadeiro fraco: {ev['ren_verdadeiro']}x (falso: {ev['ren_falso']}x)")
    print(f"Veyra seguiu o verdadeiro fraco: {ev['veyra_verdadeiro']}x")
    print(f"Tentativas de Símbolo: {ev['tentativas_simbolo']}; Meta-Símbolo: {len(ev['tentativas_meta_simbolo'])}")
    print(f"Depósitos por agente: {ev['depositos_por_agente']}")
    print(f"Critérios: {rel['criterios']}")


if __name__ == "__main__":
    imprimir_relatorio(rodar_party_causal())
