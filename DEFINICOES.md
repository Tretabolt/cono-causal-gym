# Definições canônicas — MNHI / CONO

**Documento canônico, 20/11/2026.** Esta é a fonte única das definições
usadas pelos 4 projetos (rede-pulsos, cono-mcp-harness, mnhi-3.0,
cono-causal-gym). Quando um projeto divergir daqui, o projeto está
errado — ou registra a divergência como exceção explícita, com o motivo.
A unificação foi aprovada pelo Dan em 20/11; o gym é a casa do documento
porque é onde as métricas foram testadas, não porque ele mande nos outros.

Linguagem simples primeiro: um Símbolo é um grupo coeso (muitas arestas
válidas) e homogêneo (os pesos não concentram num só lugar). A diversidade
entre Símbolos é medida por entropia, e nenhuma mudança de regra pode
empurrar o sistema para a tirania (um Símbolo dominando tudo).

## 1. ISC — topológico por decisão (19/11)

**ISC_Local = arestas válidas / arestas máximas possíveis.** É uma
contagem, uma densidade — por isso é invariante a reponderação por
construção. A decisão (19/11, aprovada pelo Dan) é que o ISC é
topológico e **não** ganha sensibilidade a pesos: qualquer esquema de
ponderação ou reproduz a contagem (continua cego), ou vira uma medida
disfarçada de uniformidade (o que a VarPn já mede), ou exige um corte
arbitrário de peso sem correção de princípio. Divisão de trabalho:
**o ISC vê quanta estrutura existe (topologia), a VarPn vê como ela
está distribuída (geometria).**

- **Validade padrão = existência.** Uma aresta existente conta como
  válida. É a validade do gym e do harness.
- **Variante C3 (só na rede-pulsos):** validade por ablação contra um
  escore externo — válida se ablar piora o acerto, nociva se ablar
  melhora. Só existe onde há ground truth (VAI/FICA). **Condição de
  reabertura:** se o gym ganhar um critério externo de acerto, o ISC
  pode herdar sensibilidade a pesos via validade C3. Até lá, o caminho
  fica aberto, não fechado.
- **ISC dinâmico (só no harness) é outra quantidade.** `1/(1+H_fase+
  H_espectral)` mede coerência de trajetória no disco de Poincaré
  (usado nos Níveis 1–4). Tem o mesmo nome por história, mas **não**
  entra na regra de emergência e **não** se compara com o ISC
  topológico. Um "ISC = 0,9" dinâmico e um "ISC = 0,9" topológico não
  significam a mesma coisa.

## 2. Regra de emergência de Símbolo

**ISC_Local ≥ 0,85 E VarPn ≤ 0,36.** As duas condições, sempre juntas:
ISC = 1,0 sozinho é armadilha (estagnação / Tirania Causal).

- Implementações: `avaliar_cluster` no gym
  (`cono_gym/espectro.py`), `can_emerge_symbol` no harness
  (`packages/mnhi_memory/metrics.py`).
- Valores de referência (K completo, uniforme): K3 VarPn 0,25
  (Símbolo — a rejeição antiga era artefato da Var quebrada), K5 0,0625,
  K6 0,040. K6 com um rastro x10: 0,175 (sobrevive); x100: 0,764 (morre).

## 3. VarPn — a Var que vê pesos (19/11)

**VarP = Var(λ_comb / tr(L))**, variância do espectro da Laplaciana
combinatória L = D − W dividida pelo traço (traço = 2 × peso total).
**VarPn = VarP / teto(n), teto(n) = (n−1)/n².** Escala uniforme cancela;
reponderação relativa fica.

- **Limiar: VarPn ≤ 0,36** (v0.1, preserva a razão do K6: 0,05/0,1389).
  Um limiar só, para todo tamanho — a correção mora na métrica, não no
  limiar (a mesma lição do r na integral cilíndrica).
- **Por que a Var(λ) antiga está errada:** cega na estrela (espectro
  normalizado sempre [0,1,1,2], Var 0,50 para qualquer peso) e
  hipersensível no K6 (um rastro x10 levava Var 0,20 → 0,2882 e matava
  o Símbolo). A Var(λ) fica só como diagnóstico. O harness usava o
  limiar antigo 0,25 — portado para VarPn ≤ 0,36 em 20/11.

## 4. H_causal — piso, não teto (corrigido 17/11)

**H_causal = −Σ P(ISC_i)·log2(P(ISC_i))**, entropia de Shannon (base 2)
sobre os ISCs normalizados dos N Símbolos/shards. H alto = diversidade;
H → 0 = um shard monopoliza (Tirania Causal).

**Portão do Meta-Símbolo: todos os componentes válidos E ISC_Global
(média) ≥ 0,80 E H_causal ≥ log2(N)/2.** É um PISO. A versão original
(teto H ≤ 0,1) estava invertida e premiaria concentração; corrigida
pelo Dan em 17/11.

- Valores: tirania [0,90, 0,033, 0,033, 0,034] → H ≈ 0,6275,
  bloqueada; equilibrado [0,90, 0,88, 0,85, 0,89] → H ≈ 2,00,
  ISC_Global 0,88, emerge.
- **Nota honesta:** no gym o portão é automático com 2+ Símbolos válidos
  (ISC ≥ 0,85 cada) — discrimina no harness, onde shards podem ser
  fracos. No gym, o que discrimina é a tensão (Gini), a contagem de
  válidos e o veto JSD.

## 5. Veto JSD — relativo, não absoluto (margem aprovada 19/11)

Protótipo da Tirania para N Símbolos: **[0,9] + [0,1/(N−1)]×(N−1)**.
Uma mudança é **vetada** se:

1. **JSD(P_nova, Tirania) < JSD(uniforme_N, Tirania) − 0,05** — a
   proposta se aproxima demais da tirania, medida contra a uniforme;
   **OU**
2. **JSD(P_nova, Tirania) < JSD(P_antiga, Tirania)** — regressão:
   qualquer passo em direção à tirania, mesmo longe do piso.

A margem **0,05** é escolha v0.1, aprovada pelo Dan em 19/11 — não é
teorema. No gym, a checagem de regressão só se aplica quando o número
de Símbolos não muda (o protótipo depende de N); no harness as
distribuições têm tamanho fixo, então ela sempre se aplica.

**Por que não o piso absoluto 0,15 (antigo do harness):** em N=2,
JSD(uniforme, Tirania) = 0,1468 < 0,15 — o piso absoluto vetaria até
a distribuição uniforme. O veto relativo resolve a geometria apertada.

| N | JSD(uniforme, Tirania) | piso relativo (−0,05) |
|---|---|---|
| 2 | 0,1468 | 0,0968 |
| 3 | 0,2667 | 0,2167 |
| 4 | 0,3436 | 0,2936 |
| 5 | 0,3973 | 0,3473 |

Implementações: `veto_jsd` no gym (`cono_gym/causal.py`),
`Heptagram.evaluate_law_change` no harness
(`packages/mnhi_memory/heptagram.py`) — o piso absoluto 0,15 foi
substituído pelo relativo em 20/11, mantida a checagem de regressão.
O engine **não tem JSD** (tem só KL unidirecional, §6) — não promete
o que não implementa.

## 6. D_hiperbólica — mesmo nome, dois objetos, dois nomes agora

- **D_Poincaré (harness):** distância de Poincaré entre pontos do
  disco (`metrics.poincare_distance`). É a D_hiperbólica do harness.
- **D_KL (engine):** `causal_kl_divergence`, KL binária de um só
  sentido entre peso-verdade e peso-simulado
  (`extrapolation.py`). **Não** é KL simetrizada e **não** é JSD — o
  CLAUDE.MD do engine dizia que era, e foi corrigido por nota de
  verificação em 20/11.
- **A ponte** (`packages/mnhi_memory/mnhi3_bridge.py`) alimenta o PCE
  do engine com a **D_KL**, não com a distância de Poincaré. O "d_h"
  que decide se uma pista passa é a KL.
- O gym não tem coordenadas hiperbólicas (só topologia), então não tem
  D nenhuma — passo futuro, não divergência.

## 7. Hashes — identidade vs selo

**Regra canônica: o peso é estado mutável, fora da identidade.**

- **hash_rastro / hash_edge (gym e harness):** SHA-256 sobre origem +
  destino + tipo de relação. Sem peso. A mesma aresta com peso
  diferente tem o mesmo hash; mudar o peso não é adulteração, é
  aprendizado.
- **id_aresta (engine):** inclui o peso (arredondado a 6 casas). É um
  **selo de adulteração**, não uma identidade: mudar o peso gera outro
  registro e a auditoria detecta como adulteração. Conceito diferente,
  nome parecido — não são o mesmo hash e um grafo do engine não pode
  ser auditado pelo harness (nem vice-versa). Registrado como limite,
  não como bug a fundir.
- **Hash de UIF:** `hash_uif(serial, tipo_agente, funcao_s)` no harness
  e no gym (iguais). No engine, `id_canonico` sobre outro payload
  (`name + data_criacao + entity_type + extra`, `kind: VERTEX`) — de
  novo, selo de Camada 0, não a mesma identidade.

## 8. Heptagram e Pentacosagram — mesmo nome, classes diferentes

Não são o mesmo componente. Unificação aqui é nomear a diferença:

| | engine | harness | gym |
|---|---|---|---|
| **Heptagram** | PCE + regras com teto; nasce vazio | créditos/quarentena + veto JSD de mudança de lei | não implementa (só o veto JSD em `causal.py`) |
| **Pentacosagram** | cadeia linear de blocos, gênese `MNHI_3_0_GENESIS` | MerkleTree + cadeia, gênese `CONO_GENESIS_V1` | não implementa (registro append-only sem hash) |
| **PCE** | `1/(1+0,1·D_KL)`, conforme ≥ 0,5 | usa o do engine via bridge | não há |

As cadeias de auditoria **não são interoperáveis**. Fundi-las seria
outro projeto — não é esta unificação.

## 9. Sharding — camadas diferentes

- **Engine:** `int(hash[:4],16) % 4`, `prefix_bits=16`.
- **Harness:** `ConsistentHashRing`, 16 réplicas, `prefix_bits=32`.
- O gym não tem sharding (grafo único em memória). Divergência
  registrada; cada camada usa o seu.

## 10. O que cada projeto NÃO define

- **mnhi-3.0 (engine):** Camada 0 — identidade, estado, hash,
  auditoria, ingestão. **Não define** ISC, H_causal, JSD ou Var. O
  CLAUDE.MD prometia ("KL simetrizada / JSD", "auditoria em
  background", "rules engine nativo") — corrigido por nota de
  verificação em 20/11: a KL é simples, a auditoria existe como método
  síncrono mas não roda em background, e o "rules engine" é a própria
  classe Heptagram.
- **rede-pulsos:** não define hashes nem Meta-Símbolo. Define C3 (§1),
  a medição congelada (avaliar sempre com STDP desligado, 20/11) e a
  invariância de Q.
- **cono-causal-gym:** não define coordenadas hiperbólicas, Heptagram,
  Pentacosagram, sharding ou persistência.
- **cono-mcp-harness:** não define `can_emerge_symbol` até 20/11 —
  era só asserts avulsos; agora existe como função (§2).

## 11. Histórico das decisões

| data | decisão | status |
|---|---|---|
| 13/11 | H_causal como teto (H ≤ 0,1) | **errada, superseded** — invertida |
| 14/11 | ISC exato (topológico) e Var(λ) ≤ 0,25 | Var superseded 19/11 |
| 17/11 | H_causal como piso (H ≥ log2(N)/2) | adotado |
| 18/11 | VarP (vê pesos) | adotado, superseded 19/11 |
| 19/11 | VarPn ≤ 0,36 (normalizada pelo teto) | **adotado, canônico** |
| 19/11 | ISC topológico por decisão | **adotado, canônico** |
| 19/11 | margem 0,05 do veto JSD | aprovado, v0.1 |
| 20/11 | este documento; VarPn e veto relativo portados ao harness | adotado |

## 13. Espaço J — o workspace do Meta-Símbolo (20/11)

Análogo funcional do J-space (Anthropic, jul/2026). Cinco propriedades,
cada uma testada: (1) pequeno e seletivo — capacidade 3, segurar um
quarto conteúdo despeja o mais antigo; (2) relatável — `relatar()`
devolve o conteúdo em forma legível; (3) segurável — persiste entre
episódios até ser editado, despejado ou limpo; (4) usável no raciocínio
— o conteúdo é uma direção (geodésica em rascunho) que vai para a
auditoria; (5) editável e causal — editar o conteúdo segurado muda o
veredito da auditoria (teste da troca). O Meta-Símbolo propõe sozinho
(`tentar_auto_proposta`): a direção nasce das medições (v0.1 — Símbolo
morto perto da borda pede afrouxar o limiar), não de fora. Limite
honesto: análogo funcional, não o J-space — não prova consciência,
prova arquitetura. Semente de longo prazo: traços do raciocínio do
Dan (EEG como visão — EEG hoje não decodifica conteúdo de raciocínio).

## 14. Coordenadas hiperbólicas (21/11)

Cada UIF tem um ponto no Disco de Poincaré (|p| < 1), aprendido do
grafo por minimização de estresse (alvo 0,6 × distância de grafo).
d(u, v) = arcosh(1 + 2|u−v|² / ((1−|u|²)(1−|v|²))). A emergência NÃO
usa as coordenadas (continua ISC ≥ 0,85 E VarPn ≤ 0,36); o que existe
é a medição — raio hiperbólico de um cluster e separação entre
clusters. "Símbolo = bola hiperbólica" é uma proposta, não uma regra
adotada. Onde vive: `cono_gym/hiperbolico.py` (distancia_poincare,
embutir, centro_e_raio, separacao, bola_contem).

## 12. Onde vive cada implementação

| definição | gym | harness | engine |
|---|---|---|---|
| ISC topológico | `cono_gym/espectro.py:avaliar_cluster` | `packages/mnhi_memory/metrics.py:topological_isc` | — |
| VarPn | `cono_gym/var_ponderada.py` | `packages/mnhi_memory/metrics.py:var_ponderada_normalizada` | — |
| H_causal | `cono_gym/causal.py` | `packages/mnhi_memory/metrics.py:causal_entropy_bits` | — |
| veto JSD | `cono_gym/causal.py:veto_jsd` | `packages/mnhi_memory/heptagram.py:evaluate_law_change` | — |
| hash de aresta | `cono_gym/hasher.py:hash_rastro` | `packages/mnhi_memory/hasher.py:hash_edge` | `src/mnhi/layer0_hasher.py:id_aresta` (selo) |
| D hiperbólica | — | `metrics.poincare_distance` | `extrapolation.py:causal_kl_divergence` (D_KL) |
| Espaço J | `cono_gym/workspace.py:EspacoJ` | — | — |
| Coordenadas hiperbólicas | `cono_gym/hiperbolico.py:embutir` | — | — |
