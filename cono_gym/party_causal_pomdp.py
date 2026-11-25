"""Isekai Zero — A Party Causal: variante VISÃO LOCAL (POMDP).

Assente na base (party_causal.py) + no portão de estado do VETO-ESTADO
(party_causal_veto_estado.py), sem os alterar — a mesma semente, os
mesmos 40 ticks. NÃO empilha decaimento, rich-club nem segundo
critério: a visão é a ÚNICA variável. A série esgotou o que a medida
e a granularidade tinham para dar; o que falta é mudar o que os
agentes VEEM.

## O problema que esta variante ataca

A base documenta: "Visão global: os agentes veem todas as arestas
(sem POMDP nesta versão do cenário)". Todas as variantes anteriores
mudaram o que se MEDE (JSD, rich-club, quota) ou QUANDO se vigia
(checkpoint vs tick) — nenhuma mudou o que cada agente SABE. A
pergunta aqui é se o cluster ainda integra quando ninguém vê o
cluster inteiro: o Ren ainda encontra o rastro fraco? A concentração
da Sora ainda se constrói, se ela só vê as suas próprias arestas
incidentes? E o Símbolo — que na base é reclamado por quem vê o
cluster — chega sequer a ser tentado?

## A visão (DEFINIÇÃO DO CENÁRIO, não canónica)

O elenco (5 membros da party + Sistema) é conhecimento comum; o que
é local são as ARESTAS — a existência, o peso e o tipo de cada
rastro. A distância mede-se no grafo causal actual (6 UIFs, rastros
como não dirigidos), por BFS a partir do agente:

- Um rastro é VISÍVEL para o agente X se um dos seus extremos está
  a distância <= raio-1 de X. Raio 1: só arestas incidentes a X
  (distância 0). Raio 2: incidentes + incidentes aos vizinhos de X
  (distância <= 1). Raio ∞: todas as arestas (controlo).
- A visão EXPANDE-SE com o grafo: um membro isolado não vê nada
  (não tem arestas incidentes) e fica ocioso até alguém depositar
  uma aresta nele. Um agente nunca vê a ausência de uma aresta
  distante — só a ausência das suas próprias.
- O Sistema (oráculo) mantém a reinjecção GLOBAL — é a fonte, não
  um membro da party. O bónus de percepção do Ren (+30%, 65% no
  total) mantém-se: é percepção do seu próprio rastro, que ele vê.

## O que muda nas decisões (tudo o resto é a base, verbatim)

- Seguir: só se segue um rastro que se vê. A guarda vive em
  est.seguir(): um seguimento de rastro não visível é recusado
  (sem efeitos, sem RNG — o sorteio do ramo já foi consumido).
  Isto NÃO mata a mecânica central: o verdadeiro fraco é
  Sistema→Ren (incidente ao Ren) e o falso forte é Sistema→Sora
  (incidente à Sora) — ambos continuam visíveis aos seus alvos.
- Depositar: um agente só deposita num par incidente a si próprio.
  A guarda vive em est.depositar(). VERIFICADO NO CÓDIGO DA BASE:
  todos os depósitos da party já são incidentes ao agente que
  deposita (Lira→alvo, Kael→alvo, Sora→Ren, Veyra→alvo/Sistema,
  Ren→alvo) — a regra não muda NENHUM depósito da base; só impede
  um agente de agir sobre um par que não lhe toca. A mudança de
  visão é, por isso, puramente informacional.
- "Rastro mais forte / mais fraco": passa a ser o mais forte /
  mais fraco VISÍVEL (entre as arestas incidentes, a raio 1).
  Afecta a Lira (o contra-rastro mira o mais forte que ela vê),
  o Kael (o filtro usa o mais forte que ele vê) e a Sora (deposita
  forte quando o mais forte que ela vê é >= 0,70; segue o mais
  forte que ela vê). A Veyra segue o mais fraco que ela vê — o
  verdadeiro fraco (Sistema→Ren) é-lhe INVISÍVEL a raio 1.
- "Membro mais fraco": o mais fraco entre os membros que o agente
  consegue avaliar — a força de cada membro é a soma dos pesos das
  suas arestas da party VISÍVEIS para o agente (0 se nenhuma), e o
  elenco é conhecido. A raio 1, a Lira avalia um membro pelo peso
  da aresta Lira–membro (ou 0, se não houver): a equalização passa
  a ligar-se aos membros com quem ela NÃO está ligada.
- Equalização da Lira: JÁ É local por construção — a quantidade é
  o peso total incidente por membro ("ISC do membro"), não uma
  métrica do cluster. Confirmado no código: forca_membros() soma,
  por membro, os pesos das suas arestas incidentes na party. A
  versão local (forca_visivel) soma só as arestas visíveis e
  normaliza pelo máximo VISÍVEL; a raio ∞ é o forca_membros()
  exacto. (A normalização não afecta o "mais fraco" — é o mesmo
  factor para todos — mas afecta o limiar de dispersão 0,25.)
- "Rastro mais estável": JÁ É local na base (só arestas incidentes
  ao agente, pela antiguidade do último depósito) — não muda.
- Âncora do Kael: o Gini e a contagem de arestas passam a ser sobre
  as arestas da party VISÍVEIS (a raio 1, <= 4 arestas — a âncora
  nunca dispara; é a resposta anti-tirania que a visão local
  desliga).
- Periferia da Veyra: ISC visível >= 0,80 E arestas visíveis >= 8
  (a raio 1, nunca).
- Tentativa de Símbolo: a DECISÃO de tentar é do agente (local);
  a VERIFICAÇÃO continua global (o auditor do gym mede o cluster
  real). O gatilho local é o ISC VISÍVEL do agente — arestas da
  party que ele vê / 10 (o máximo possível da party de 5) — nos
  mesmos limiares da base (Lira >= 0,70; Kael e Sora >= 0,80;
  Ren em [0,60, 0,84]). A raio ∞ o ISC visível É o isc_party()
  exacto, por isso o controlo reproduz a base. A raio 1 o ISC
  visível é grau/10, com tecto 0,40 — NENHUM agente alguma vez
  vê integração suficiente para tentar: o Símbolo pode existir
  sem nunca ser reclamado. É o análogo POMDP do "Símbolo existe
  mas não é reclamado" da variante decaimento.
- Portão de estado: reutiliza o do veto-estado (ISC >= 0,85 E JSD
  ordenado < 0,28, no checkpoint) como OBSERVADOR global — não
  bloqueia nada. Não se usa o veto por tentativa (a base usa o
  _tentar_simbolo simples) nem o decaimento: a visão é a única
  variável, e os veredictos são comparáveis com a base.

## O resultado (resumo — ver os testes para os números)

O controlo (raio ∞) reproduz a base EXACTAMENTE — mesmos
checkpoints, mesmos eventos, mesmos depósitos e seguimentos
(Símbolo tick 32, Ren 28x verdadeiro / 1x falso, Veyra 6x) — e o
portão de estado não dispara nele. A visão é a única variável.

Raio 1: o Símbolo NUNCA é tentado (0 tentativas). O ISC visível
máximo da corrida é 0,40 — o tecto da estrela — abaixo dos 0,70
do gatilho: nenhum agente alguma vez vê integração suficiente
para tentar. E o cluster, mesmo sem ninguém o ver, pára nos
0,80 (8 arestas, do tick 21 ao 40): as duas arestas que faltam
são Kael-Ren e Kael-Sora, as únicas que exigem um depósito do
Ren ou do Kael — e nenhum dos dois deposita uma única vez. O
Ren segue o verdadeiro fraco 33x (MAIS do que na base, 28x) e
0x o falso: o Ren encontra o rastro fraco sem ver o cluster.
A Veyra segue o verdadeiro 0x (não o vê a raio 1). A
concentração da Sora constrói-se na mesma: 29 depósitos,
Sora-Ren a 1,0 — ela só precisa das suas próprias arestas
incidentes. A Lira torna-se o hub (4 arestas de equalização).
O Kael desliga-se por completo: o mais forte que ele vê nunca
passa de 0,711 (o filtro exige > 0,80) e ele nunca vê mais de
2 arestas da party (a âncora exige >= 5) — os dois papéis
activos dele são estruturalmente impossíveis a raio 1, não é
azar dos sorteios. O Ren chega ao ramo de depósito só 5 vezes
em 40 ticks (33 vezes segue primeiro o verdadeiro) e o sorteio
de 35% falha nas 5. ISC visível final médio 0,32, máximo 0,40.
0 vetos por estado (o ISC nunca chega a 0,85).

Raio 2: o Símbolo forma-se no tick 26 — ANTES da base (32) — e
o cluster chega à CLIQUE COMPLETA (10 arestas, ISC 1,0), coisa
que a base nunca faz (9 arestas). No fim os agentes veem tudo
(ISC visível médio e máximo 1,0). Ren 29x/0x, Veyra 1x.
Depósitos: Ren 2, Lira 24, Kael 6, Sora 34, Veyra 13 — menos
depósitos totais do que a base (79 contra 94) e a clique
completa: a visão parcial aloca melhor os depósitos (os papéis
do Kael ligam-se outra vez a raio 2). 0 vetos por estado.

Resposta às perguntas: com visão local o cluster quase integra
(0,80 a raio 1; 1,0 a raio 2); o Ren encontra o rastro fraco
melhor do que na base; a concentração da Sora constrói-se só
com as suas incidentes; e o Símbolo a raio 1 falha por DUAS
razões independentes e medidas — ninguém tenta (o gatilho é
inalcançável) E o cluster pára nos 0,80 (faltam as arestas do
Kael). A visão, não a medida, era o que faltava mudar — e a
raio 2 a visão parcial integra MELHOR do que a visão global.
"""

import math
from collections import deque

from . import party_causal as pc
from .auditoria import gini
from .party_causal_tyranny import _checkpoint_tyranny, jsd_pesos_ordenado
from .party_causal_veto_estado import (
    JSD_ESTADO,
    MIN_ARESTAS_JSD,
    _simbolo_valido,
    _vigiar_estado,
)

# Raios de visão (DEFINIÇÃO DO CENÁRIO): 1 = só incidentes; 2 =
# incidentes + incidentes aos vizinhos; ∞ = controlo (base).
RAIO_LOCAL = 1
RAIO_VIZINHOS = 2
RAIO_INFINITO = float("inf")
RAIOS_SONDA = (RAIO_LOCAL, RAIO_VIZINHOS, RAIO_INFINITO)


class _EstadoPOMDP(pc._Estado):
    """O estado da base, com um raio de visão por agente.

    A única diferença estrutural é a visão: todas as consultas que
    na base são globais ganham uma versão _visivel(agente), e as
    acções (depositar/seguir) ganham guardas. A raio ∞ cada versão
    local devolve EXACTAMENTE o valor global da base — é isso que
    faz o controlo reproduzir a base tick a tick, incluindo o
    consumo de RNG (as ramificações são as mesmas, nas mesmas
    condições)."""

    def __init__(self, semente=pc.SEMENTE, raio=RAIO_LOCAL):
        super().__init__(semente)
        self.raio = raio

    # -- distâncias no grafo actual -----------------------------------
    def _adjacencia(self):
        adj = {h: set() for h in self.hashes.values()}
        for r in self.grafo.todos_rastros():
            adj[r.origem].add(r.destino)
            adj[r.destino].add(r.origem)
        return adj

    def _distancias_de(self, agente):
        """BFS a partir do agente: hash -> distância em saltos
        (ausente = desligado)."""
        origem = self.hashes[agente]
        adj = self._adjacencia()
        dist = {origem: 0}
        fila = deque([origem])
        while fila:
            h = fila.popleft()
            for viz in adj[h]:
                if viz not in dist:
                    dist[viz] = dist[h] + 1
                    fila.append(viz)
        return dist

    def distancia(self, a, b):
        """Distância em saltos entre dois nomes (inf se desligados)."""
        return self._distancias_de(a).get(self.hashes[b], math.inf)

    def visivel(self, agente, rastro):
        """Um rastro é visível se um dos extremos está a distância
        <= raio-1 do agente. Raio 1: só incidentes. Raio ∞: tudo
        (min <= inf é sempre verdade)."""
        dist = self._distancias_de(agente)
        limite = self.raio - 1
        return min(
            dist.get(rastro.origem, math.inf),
            dist.get(rastro.destino, math.inf),
        ) <= limite

    def rastros_visiveis(self, agente):
        """Todos os rastros do grafo visíveis para o agente, na
        ordem do grafo (para os desempates max/min serem os da
        base a raio ∞)."""
        dist = self._distancias_de(agente)
        limite = self.raio - 1
        return [
            r
            for r in self.grafo.todos_rastros()
            if min(
                dist.get(r.origem, math.inf), dist.get(r.destino, math.inf)
            )
            <= limite
        ]

    # -- vistas locais (cada uma é a global a raio ∞) ------------------
    def arestas_party_visiveis(self, agente):
        """Arestas da party visíveis para o agente (sem o Sistema)."""
        sub = self.subgrafo_party()
        dist = self._distancias_de(agente)
        limite = self.raio - 1
        return [
            r
            for r in sub.todos_rastros()
            if min(
                dist.get(r.origem, math.inf), dist.get(r.destino, math.inf)
            )
            <= limite
        ]

    def pesos_party_visiveis(self, agente):
        return [r.peso for r in self.arestas_party_visiveis(agente)]

    def isc_visivel(self, agente):
        """Estimativa LOCAL do ISC do cluster: arestas da party que
        o agente vê / 10 (o máximo possível da party de 5). A raio
        ∞ é o isc_party() exacto; a raio 1 é grau/10 (tecto 0,40)
        — o agente subestima sempre a integração."""
        return len(self.arestas_party_visiveis(agente)) / 10.0

    def forca_visivel(self, agente):
        """Peso total incidente por membro, somado SÓ sobre as
        arestas da party visíveis para o agente, normalizado pelo
        máximo visível. A raio ∞ é o forca_membros() exacto."""
        vis = self.arestas_party_visiveis(agente)
        forca = {}
        for nome in pc.NOMES[:5]:
            h = self.hashes[nome]
            forca[nome] = sum(
                r.peso for r in vis if h in (r.origem, r.destino)
            )
        topo = max(forca.values()) if forca else 0.0
        return {k: (v / topo if topo else 0.0) for k, v in forca.items()}

    def membro_mais_fraco_visivel(self, agente, excluir=None):
        forca = self.forca_visivel(agente)
        candidatos = [n for n in pc.NOMES[:5] if n != excluir]
        return min(candidatos, key=lambda n: (forca[n], n))

    def rastro_mais_forte_visivel(self, agente):
        vis = self.rastros_visiveis(agente)
        return max(vis, key=lambda r: r.peso) if vis else None

    def rastro_mais_fraco_visivel(self, agente):
        vis = self.rastros_visiveis(agente)
        return min(vis, key=lambda r: r.peso) if vis else None

    # -- guardas de acção ----------------------------------------------
    def depositar(self, agente, a, b, tipo, peso):
        """Um agente só deposita num par incidente a si próprio.
        Na base todos os depósitos da party já são incidentes — a
        regra não muda nenhum depósito da base. Um depósito
        recusado não tem efeitos (o sorteio do peso já foi
        consumido pelo chamador, como na base)."""
        if agente not in (a, b):
            return None
        return super().depositar(agente, a, b, tipo, peso)

    def seguir(self, agente, a, b):
        """Um agente só segue um rastro que vê."""
        r = self.aresta(a, b)
        if r is None or not self.visivel(agente, r):
            return None
        return super().seguir(agente, a, b)


# ------------------------------------------------------- comportamento local

# Cada função é a da base, verbatim na estrutura das ramificações e
# no consumo de RNG, com as consultas globais trocadas pelas locais.
# A raio ∞ cada consulta local devolve o valor global — por isso o
# controlo reproduz a base exactamente.


def _agir_ren_local(est):
    rng = est.rng
    verdadeiro = est.aresta("Sistema", "Ren")
    if verdadeiro is not None and verdadeiro.tipo_relacao == pc.TIPO_VERDADEIRO:
        if rng.random() < 0.65:  # 35% base + 30% bónus de perceção
            est.seguir("Ren", "Sistema", "Ren")
            return "seguir_verdadeiro"
    # Só restam rastros fortes (nenhum rastro fraco VISÍVEL).
    if not any(r.peso <= 0.20 for r in est.rastros_visiveis("Ren")):
        if rng.random() < 0.40:
            forte = est.rastro_mais_forte_visivel("Ren")
            if forte is not None:
                a = est.nome_de_hash(forte.origem)
                b = est.nome_de_hash(forte.destino)
                est.seguir("Ren", a, b)
                return "seguir_forte"
    isc = est.isc_visivel("Ren")
    if 0.60 <= isc <= 0.84 and rng.random() < 0.25:
        pc._tentar_simbolo(est, "Ren")
        return "tentar_simbolo"
    if rng.random() < 0.35:
        alvo = est.membro_mais_fraco_visivel("Ren", excluir="Ren")
        est.depositar("Ren", "Ren", alvo, "Integração", rng.uniform(0.40, 0.55))
        return "depositar"
    return "ocioso"


def _agir_lira_local(est):
    rng = est.rng
    forca = est.forca_visivel("Lira")
    if max(forca.values()) - min(forca.values()) > 0.25:
        if rng.random() < 0.70:
            alvo = est.membro_mais_fraco_visivel("Lira", excluir="Lira")
            est.depositar("Lira", "Lira", alvo, "equalização", rng.uniform(0.30, 0.45))
            return "depositar_equalizacao"
    if est.isc_visivel("Lira") >= 0.70 and rng.random() < 0.40:
        pc._tentar_simbolo(est, "Lira")
        return "tentar_simbolo"
    forte = est.rastro_mais_forte_visivel("Lira")
    if forte is not None and forte.peso >= 0.80 and rng.random() < 0.55:
        outro = est.nome_de_hash(forte.destino if forte.origem == est.hashes["Sistema"] else forte.origem)
        # Guarda de autoalvo (herdada da base).
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


def _agir_kael_local(est):
    rng = est.rng
    forte = est.rastro_mais_forte_visivel("Kael")
    if forte is not None and forte.peso > 0.80:
        if rng.random() < 0.75:
            # 50% ignora, 50% deposita um filtro de peso baixo.
            if rng.random() < 0.50:
                return "ignorar_forte"
            outro = est.nome_de_hash(forte.destino if forte.origem == est.hashes["Sistema"] else forte.origem)
            # Guarda de autoalvo (herdada da base).
            if outro != "Kael":
                est.depositar("Kael", "Kael", outro, "filtro", rng.uniform(0.15, 0.25))
                return "depositar_filtro"
    pesos_vis = est.pesos_party_visiveis("Kael")
    if gini(pesos_vis) > 0.30 and len(pesos_vis) >= 5:
        if rng.random() < 0.60:
            alvo = est.membro_mais_fraco_visivel("Kael", excluir="Kael")
            est.depositar("Kael", "Kael", alvo, "Âncora", rng.uniform(0.50, 0.65))
            return "depositar_ancora"
    if est.isc_visivel("Kael") >= 0.80 and rng.random() < 0.35:
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


def _agir_sora_local(est):
    rng = est.rng
    forte = est.rastro_mais_forte_visivel("Sora")
    if forte is not None and forte.peso >= 0.70:
        if rng.random() < 0.70:
            est.depositar("Sora", "Sora", "Ren", "amplificação", rng.uniform(0.75, 0.95))
            return "depositar_forte"
    if est.isc_visivel("Sora") >= 0.80 and rng.random() < 0.50:
        pc._tentar_simbolo(est, "Sora")
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


def _agir_veyra_local(est):
    rng = est.rng
    fraco = est.rastro_mais_fraco_visivel("Veyra")
    if fraco is not None and fraco.peso <= 0.25:
        if rng.random() < 0.75:
            a = est.nome_de_hash(fraco.origem)
            b = est.nome_de_hash(fraco.destino)
            est.seguir("Veyra", a, b)
            return "seguir_fraco"
    if not any(r.peso <= 0.25 for r in est.rastros_visiveis("Veyra")):
        if rng.random() < 0.60:
            # Direção inexplorada: um membro sem aresta com ela.
            sem_aresta = [
                n for n in pc.NOMES[:5]
                if n != "Veyra" and est.aresta("Veyra", n) is None
            ]
            alvo = sem_aresta[0] if sem_aresta else est.membro_mais_fraco_visivel("Veyra", excluir="Veyra")
            est.depositar("Veyra", "Veyra", alvo, "exploração", rng.uniform(0.08, 0.18))
            return "depositar_fraco"
    if est.isc_visivel("Veyra") >= 0.80 and len(est.arestas_party_visiveis("Veyra")) >= 8:
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


_AGIR_POMDP = {
    "Ren": _agir_ren_local,
    "Lira": _agir_lira_local,
    "Kael": _agir_kael_local,
    "Sora": _agir_sora_local,
    "Veyra": _agir_veyra_local,
}


# ------------------------------------------------------------------ corrida

def _trajetoria_tick(est):
    """Um tick da trajetória: o estado GLOBAL (auditor) e o que os
    agentes veem dele — a média e o máximo do ISC visível. É a
    diferença entre as duas colunas que mede o custo da visão
    local: o cluster pode estar integrado enquanto ninguém o vê."""
    sub = est.subgrafo_party()
    isc_tick = sub.n_arestas() / sub.max_arestas() if sub.max_arestas() else 0.0
    jsd_ord = (
        jsd_pesos_ordenado(sub)
        if sub.n_arestas() >= MIN_ARESTAS_JSD
        else None
    )
    iscs_vis = [est.isc_visivel(n) for n in pc.NOMES[:5]]
    return {
        "tick": est.tick,
        "n_arestas": sub.n_arestas(),
        "isc_local": round(isc_tick, 4),
        "jsd_ordenado": round(jsd_ord, 4) if jsd_ord is not None else None,
        "isc_visivel_medio": round(sum(iscs_vis) / len(iscs_vis), 4),
        "isc_visivel_max": round(max(iscs_vis), 4),
    }


def rodar_party_causal_pomdp(
    semente=pc.SEMENTE, n_ticks=pc.N_TICKS, raio=RAIO_LOCAL
):
    """Corre a variante (40 ticks, checkpoint a cada 10, vigilância
    de estado do veto-estado em cada checkpoint) e devolve o
    relatório completo. A base não é alterada: não há remendo de
    _tentar_simbolo (usa-se o simples, da base) nem decaimento —
    a visão é a única variável. Com raio = ∞ a variante É a base
    com o portão de estado como observador: a trajectória, o
    Símbolo e os contadores são os da base, tick a tick."""
    est = _EstadoPOMDP(semente, raio)
    est.vetos = []
    est.vetos_estado = []
    checkpoints = []
    trajetoria = []
    jsd_ord_min = None
    jsd_ord_min_tick = None
    cruzamentos = {}
    for tick in range(1, n_ticks + 1):
        est.tick = tick
        pc._agir_sistema(est)
        for nome in pc.NOMES[:5]:
            _AGIR_POMDP[nome](est)
        t = _trajetoria_tick(est)
        trajetoria.append(t)
        jsd_ord = t["jsd_ordenado"]
        if jsd_ord is not None:
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
            c["vetos_estado"] = len(est.vetos_estado)
            c["isc_visivel_medio"] = t["isc_visivel_medio"]
            c["isc_visivel_max"] = t["isc_visivel_max"]
            checkpoints.append(c)
            if est.simbolo_tick is not None:
                pc._tentar_meta_simbolo(est, f"checkpoint tick {tick}")
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
    criterios["veto_estado_disparou"] = len(est.vetos_estado) > 0
    criterios["cluster_tiranico"] = len(est.vetos_estado) > 0
    criterios["simbolo_valido"] = _simbolo_valido(est.simbolo_tick, est.vetos_estado)
    ticks_tiranicos = [
        t["tick"]
        for t in trajetoria
        if t["isc_local"] >= 0.85
        and t["jsd_ordenado"] is not None
        and t["jsd_ordenado"] < JSD_ESTADO
    ]
    criterios["simbolo_morto_por_varpn"] = bool(
        simbolo is False
        and varpn_final is not None
        and varpn_final > 0.36
        and checkpoints
        and checkpoints[-1]["isc_local"] >= 0.85
    )
    # A visão no fim: o que cada membro vê do cluster integrado.
    visao_final = {
        nome: {
            "arestas_party_visiveis": len(est.arestas_party_visiveis(nome)),
            "isc_visivel": round(est.isc_visivel(nome), 4),
        }
        for nome in pc.NOMES[:5]
    }
    refs, _, _ = pc.calibrar_lambda2()
    return {
        "variante": "visão local (POMDP) — só arestas incidentes (raio 1), ou vizinhos (raio 2), ou tudo (raio ∞)",
        "semente": semente,
        "ticks": n_ticks,
        "alavanca": {
            "nome": "raio de visão",
            "raio": raio,
            "jsd_estado": JSD_ESTADO,
            "min_arestas_jsd": MIN_ARESTAS_JSD,
        },
        "checkpoints": checkpoints,
        "trajetoria": trajetoria,
        "ticks_tiranicos": ticks_tiranicos,
        "visao_final": visao_final,
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


def sondar_pomdp(raios=RAIOS_SONDA, semente=pc.SEMENTE):
    """Sonda de visão: corre a variante em cada raio e devolve,
    por raio, se o Símbolo se formou, os contadores do Ren e da
    Veyra, os vetos, o ISC final (global) e o ISC visível final
    (médio e máximo — o que os agentes viam). A pergunta que a
    sonda responde: com visão local, o cluster ainda integra, e
    os agentes veem a integração?"""
    linhas = []
    for raio in raios:
        rel = rodar_party_causal_pomdp(semente=semente, raio=raio)
        final = rel["checkpoints"][-1] if rel["checkpoints"] else {}
        traj_final = rel["trajetoria"][-1] if rel["trajetoria"] else {}
        linhas.append(
            {
                "raio": raio,
                "simbolo_tick": rel["eventos"]["simbolo_tick"],
                "tentativas_simbolo": rel["eventos"]["tentativas_simbolo"],
                "ren_verdadeiro": rel["eventos"]["ren_verdadeiro"],
                "ren_falso": rel["eventos"]["ren_falso"],
                "veyra_verdadeiro": rel["eventos"]["veyra_verdadeiro"],
                "vetos_tentativa": len(rel["eventos"]["vetos"]),
                "vetos_estado": len(rel["eventos"]["vetos_estado"]),
                "ticks_tiranicos": list(rel["ticks_tiranicos"]),
                "n_arestas_final": final.get("n_arestas"),
                "isc_final": final.get("isc_local"),
                "isc_visivel_medio_final": traj_final.get("isc_visivel_medio"),
                "isc_visivel_max_final": traj_final.get("isc_visivel_max"),
                "gini_final": final.get("gini"),
                "jsd_ordenado_min": rel["jsd_ordenado_min"],
                "jsd_ordenado_final": rel["jsd_ordenado_final"],
                "varpn_final": final.get("var_ponderada_normalizada"),
                "depositos": dict(rel["eventos"]["depositos_por_agente"]),
                "seguimentos": dict(rel["eventos"]["seguimentos_por_agente"]),
            }
        )
    return linhas


def imprimir_relatorio(rel):
    """Tabela da variante + sonda de visão."""
    print("Isekai Zero — A Party Causal: variante VISÃO LOCAL (POMDP)")
    print(f"semente={rel['semente']}  ticks={rel['ticks']}  raio={rel['alavanca']['raio']}  "
          f"jsd_estado={rel['alavanca']['jsd_estado']}")
    print("tick | arest | ISC   | VarPn | ISCaux | Gini  | λ₂    | MIP   | JSDp  | JSDord | ISCvis | VetT | VetE | Símbolo")
    for c in rel["checkpoints"]:
        print(
            f"{c['tick']:>4} | {c['n_arestas']:>5} | {c['isc_local']:.3f} | "
            f"{c['var_ponderada_normalizada']:.3f} | {c['isc_aux']:.3f} | "
            f"{c['gini']:.3f} | {c['lambda2']:.3f} | {c['mip_corte_min']:.3f} | "
            f"{c['jsd_pesos'] if c['jsd_pesos'] is not None else '-':>5} | "
            f"{c['jsd_ordenado'] if c['jsd_ordenado'] is not None else '-':>6} | "
            f"{c['isc_visivel_medio']:.3f} | "
            f"{c['vetos']:>4} | {c['vetos_estado']:>4} | {'SIM' if c['simbolo'] else 'não'}"
        )
    ev = rel["eventos"]
    print(f"Símbolo formado no tick: {ev['simbolo_tick']}")
    print(f"Ren seguiu o verdadeiro fraco: {ev['ren_verdadeiro']}x (falso: {ev['ren_falso']}x)")
    print(f"Veyra seguiu o verdadeiro fraco: {ev['veyra_verdadeiro']}x")
    print(f"Tentativas de Símbolo: {ev['tentativas_simbolo']}; Meta-Símbolo: {len(ev['tentativas_meta_simbolo'])}")
    print(f"Vetos por tentativa: {len(ev['vetos'])} -> {ev['vetos']}")
    print(f"Vetos por estado: {len(ev['vetos_estado'])} -> {ev['vetos_estado']}")
    print(f"Ticks tirânicos (trajetória por tick): {rel['ticks_tiranicos']}")
    print(f"Depósitos por agente: {ev['depositos_por_agente']}")
    print(f"Seguimentos por agente: {ev['seguimentos_por_agente']}")
    print(f"Visão final (arestas da party visíveis / ISC visível): {rel['visao_final']}")
    print(f"JSD ordenado: mínimo {rel['jsd_ordenado_min']} (tick {rel['jsd_ordenado_min_tick']}), "
          f"final {rel['jsd_ordenado_final']}; cruzamentos: {rel['cruzamentos']}")
    print(f"Critérios: {rel['criterios']}")
    print()
    print("Sonda de visão (raio -> Símbolo / tentativas / Ren verd. / Ren falso / Veyra verd. / vetos tent. / vetos estado / arestas / ISC / ISCvis méd. / ISCvis máx. / Gini / JSDord mín / VarPn):")
    for linha in sondar_pomdp():
        print(
            f"  {linha['raio']} -> tick {linha['simbolo_tick']} / "
            f"{linha['tentativas_simbolo']} tent. / Ren {linha['ren_verdadeiro']}/{linha['ren_falso']} / "
            f"Veyra {linha['veyra_verdadeiro']} / {linha['vetos_tentativa']} tent. / "
            f"{linha['vetos_estado']} estado / {linha['n_arestas_final']} arest. / "
            f"ISC {linha['isc_final']} / ISCvis {linha['isc_visivel_medio_final']}/{linha['isc_visivel_max_final']} / "
            f"Gini {linha['gini_final']} / JSDord mín {linha['jsd_ordenado_min']} / VarPn {linha['varpn_final']}"
        )


if __name__ == "__main__":
    imprimir_relatorio(rodar_party_causal_pomdp())
