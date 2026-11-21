# CONO Causal Gym — MVP fechado

Um ginásio abstrato onde a única coisa que importa é a dinâmica causal
e a formação de identidade. Não é um jogo de salas, portas e objetos.

## O que existe neste esqueleto (17/11/2026)

- `cono_gym/hasher.py` — CanonicalHasher, Camada 0 do MNHI 3.0:
  Hash_UIF (identidade imutável, nunca depende do estado), Hash_Rastro
  (cadeia de custódia causal) e Hash_Símbolo (serial + espectro ordenado).
- `cono_gym/grafo.py` — Grafo causal em memória: UIFs como nós,
  Rastros Causais como arestas, vista causal local por raio.
- `cono_gym/espectro.py` — Espectro do Laplaciano normalizado em Python
  puro (método de Jacobi, sem dependências), ISC_Local, Var(λ) e a regra
  de emergência de Símbolo: ISC_Local ≥ 0,85 E VarPn ≤ 0,36 (a Var(λ)
  antiga fica só como diagnóstico).
- `cono_gym/demo.py` — Quatro clusters, quatro vereditos.
- `testes/test_gym.py` + `testes/test_mcp.py` + `testes/test_episodios.py` + `testes/test_geodesica.py` + `testes/test_causal.py` + `testes/test_var_ponderada.py` — 89 testes (14 + 21 + 8 + 9 + 18 + 19).

Python stdlib-only, como os outros dois repos.

## Definições canônicas

`DEFINICOES.md` é a fonte única das definições (ISC, VarPn, H_causal,
veto JSD, hashes, D_hiperbólica, Heptagram/Pentacosagram) para os 4
projetos — unificação aprovada pelo Dan em 20/11. Quando um projeto
divergir dele, o projeto está errado.

## MCP server mínimo

`cono_gym/mcp_server.py` — JSON-RPC 2.0 sobre stdio, no mesmo padrão do
cono-mcp-harness (initialize, tools/list, tools/call; tool desconhecida
é recusada pela AI-Jail). Roda com:

```bash
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize"}' | python3 -m cono_gym.mcp_server
```

As 9 tools: create_uif, get_local_causal_view, deposit_trail,
follow_trail, inspect_identity (só hash + tipo, nunca o estado),
request_symbol_formation, propose_geodesic, audit_geodesic e
request_diversity_audit (as três últimas, só com Meta-Símbolo).

O servidor nasce com um grafo já construído (duas cliques K6, como o
harness nasce com um cenário), mas o agente pode CRIAR UIFs novas pela
tool `create_uif` (serial + tipo_agente + funcao_s). Uma UIF nasce
isolada, sem rastros, e só entra na causalidade quando recebe rastros
por `deposit_trail`. O serial é único: duplicá-lo é recusado
(deduplicação natural, como na ingestão do mnhi-3.0). A demo do MCP
termina crescendo uma terceira clique K6 inteira pela tool e formando
o Símbolo C — o gym pode crescer sem nenhum grafo pré-construído.

## Demo de sessão (`python3 -m cono_gym.demo_mcp`)

Duas cliques K6 formam os Símbolos A e B, mas com pesos uniformes o
Gini é 0,0: sem tensão, sem Meta-Símbolo — e a auditoria e a geodésica
são recusadas. Cinco rastros pesados (peso 8) entre as cliques elevam
o Gini a 0,4286; no terceiro deles o Meta-Símbolo se forma. A auditoria
então passa (tensão presente) e a geodésica válida é registrada com
status "aguardando_auditoria" — e auditada em seguida: no estado da
demo (A e B já válidos) a proposta limiar_var 0.36 → 0.40 é suspeita
por ser vácua, pois não altera nenhum veredito.

Regras provisórias (v0.1), marcadas no código: limiar de Gini 0,30 e
margem 0,05 do veto JSD (aprovada pelo Dan em 19/11). A H_causal É
calculada desde 17/11 (`cono_gym/causal.py`): o portão do Meta-Símbolo
é um PISO, H_causal ≥ log2(N)/2, não um teto — a versão antiga deste
parágrafo, que dizia que ela "ainda não é calculada", estava errada e
foi corrigida em 20/11.

## Resultados da demo

| cluster | nós | arestas | ISC | VarPn | Símbolo? |
|---|---|---|---|---|---|
| estrela (rede-pulsos) | 4 | 3 | 0,50 | 0,3333 | NÃO |
| ciclo-5 | 5 | 5 | 0,50 | 0,1250 | NÃO |
| clique-5 (K5) | 5 | 10 | 1,00 | 0,0625 | SIM |
| clique-6 (K6) | 6 | 15 | 1,00 | 0,0400 | SIM |

A estrela reproduz o achado da rede-pulsos: λ = [0, 1, 1, 2], VarPn 0,3333,
nunca um Símbolo por estrutura, não por treino — o ISC 0,50 barra, não a Var.

## Leitura honesta

Os primeiros Símbolos do gym são cliques densos — e ISC 1,0 sozinho é
armadilha (estagnação, Tirania Causal). Falta medir a tensão
diversidade × coerência (pesos log-normais vs homogeneidade): é o
próximo passo, não este esqueleto. O espectro também é cego aos pesos,
como o ISC — o que liga este esqueleto à meta "Invariância como
critério": definir o peso que falta nessas métricas.

## Loop de episódios (`python3 -m cono_gym.demo_episodios`)

O agente age só pelas tools (ver, depositar, formar Símbolo); o
experimentador mede com as mesmas funções verificadas. Em 12 episódios
(semente 42): os Símbolos A e B se formam no episódio 1; no episódio 4
o Gini cruza 0,30, a tensão aparece e o Meta-Símbolo se forma — as duas
condições coincidem pela primeira vez. A e B ficam estáveis nos 12
episódios (estabilidade 1,000 nos dois). A tensão pisca (6/12
episódios). O Símbolo do grafo inteiro nunca se forma (ISC ~0,5–0,67
< 0,85). H_causal é 1,0 bit nos 12 episódios (dois Símbolos com ISC
1,0); ISC_Global é 1,0 o tempo todo. Gini final 0,333, Var média final
(VarPn) 0,083.

## H_causal (`cono_gym/causal.py`) — definição real

CORREÇÃO 17/11 (informação do Dan): a primeira versão estava
INVERTIDA — media a entropia do peso dos rastros entre Símbolos com
teto H ≤ 0,1, o que premiaria a concentração. A definição real é
H_causal = -Σ P(ISC_i)·log2(P(ISC_i)), Shannon (base 2) sobre os ISCs
normalizados entre os Símbolos. H alto = diversidade; H baixo =
tirania. O portão é um PISO: ISC_Global (média) ≥ 0,80 e
H_causal ≥ log2(N)/2. O mesmo portão foi fechado no harness
(`causal_entropy_bits` + `can_emerge_meta_symbol` em
`packages/mnhi_memory/metrics.py`, teste TDD em
`scenarios/test_01_mnhi_core.py`; suíte do harness 17/17).
O veto JSD usa o protótipo de Tirania [0,9] + [0,1/(N-1)]×(N-1):
a mudança é vetada se JSD(P_nova, Tirania) ficar abaixo de
JSD(uniforme, Tirania) - 0,05.

Nota honesta: no gym, como um Símbolo válido exige ISC ≥ 0,85, os
portões de ISC_Global e H_causal são automaticamente satisfeitos
quando há 2+ válidos — eles discriminam no harness, onde shards
podem ser fracos. No gym, o que discrimina é a tensão (Gini), a
contagem de válidos e o veto JSD (que morde quando a projeção inclui
um mega-símbolo de ISC baixo: caso 2 da geodésica, JSD 0,199 contra
0,267 de uma distribuição equilibrada).

## Auditoria da geodésica (`python3 -m cono_gym.demo_geodesica`)

Nova tool `audit_geodesic`: o Meta-Símbolo julga uma mudança de regra
aplicando-a ao mesmo estado sob a regra antiga e sob a nova. Checagens:
sem colapso, preserva tensão, critério B (não concentra poder), veto
JSD (não se aproxima da Tirania) e não vácua. Três propostas sobre 3
cliques K6 (A ferido com VarPn 0,3662, B e C vivos, H_causal = 1,0 bit,
Gini 0,8102):

| proposta | veredito | por quê |
|---|---|---|
| limiar_var 0.36 → 0.40 | aprovada | A ressuscita (VarPn 0,3662), válidos 2→3, tensão mantida, JSD se afasta da tirania (0,147 → 0,267); a regra muda de verdade |
| limiar_isc 0.85 → 0.25 | suspeita | o grafo inteiro (ISC 0,301, VarPn 0,3399) viraria um mega-símbolo com 100% do peso; o veto JSD também dispara (0,199 < 0,217) |
| limiar_var 0.36 → 0.03 | rejeitada | colapso: nenhum Símbolo sobrevive |

Regras computáveis: limiar_isc, limiar_var, limiar_gini. Proposta sem
esses campos não é auditável; proposta com base desatualizada é
recusada. Uma geodésica aprovada muda as regras vigentes do servidor.
A auditoria ainda não compara H_causal sob as duas regras (os
candidatos podem se sobrepor).

## O MVP está fechado

Grafo em memória + CanonicalHasher + espectro de Laplace + MCP server
com 9 tools (create_uif, get_local_causal_view, deposit_trail,
follow_trail, inspect_identity, request_symbol_formation,
propose_geodesic, audit_geodesic, request_diversity_audit) + loop de
episódios + auditoria da geodésica com critério B e veto JSD. Suíte
com 89 testes (70 do MVP + 14 da Var ponderada, 18/11, + 5 da
normalização, 19/11).

Próximos passos (fora do MVP, a decidir): coordenadas hiperbólicas
para as UIFs no Disco de Poincaré (hoje o grafo é só topologia);
o Meta-Símbolo propondo geodésicas por conta própria no loop.

## Var ponderada (18/11)

O critério de invariância aplicado a ISC e Var (`invariancia_isc_var.py`)
mostrou: ISC cego a pesos em tudo; Var cega na estrela ([0,1,1,2]
sempre) e hipersensível no K6 (um rastro x10 mata o Símbolo). A
resposta é a Var ponderada (`cono_gym/var_ponderada.py`): Var do
espectro do Laplaciano combinatorial dividido pelo traço — invariante
a escala uniforme, sensível a reponderação relativa. Estrela [1,1,1]
0,0625, [10,1,1] 0,1328, [100,1,1] 0,1803; K6 uniforme 0,0056, um
x10 0,0243 (continua Símbolo), um x100 0,1061 (não Símbolo). Limiar
v0.1: 0,05.

**Adotada em 18/11, por decisão do Dan.** A regra de emergência agora
é ISC ≥ 0,85 E VarP ≤ 0,05 (`avaliar_cluster`); a var_lambda antiga
fica no relatório só como diagnóstico, e o Hash_Símbolo continua
sobre o espectro normalizado. Consequências verificadas: no loop de
12 episódios o Símbolo A não morre mais no episódio 4 e o
Meta-Símbolo se forma no episódio 4 (estabilidade 1,0 nos dois);
a demo da geodésica foi recalibrada (3 rastros peso 100 dentro de A,
VarP 0,0509; casos 0,05→0,06 aprovado, isc 0,85→0,25 suspeito,
0,05→0,005 rejeitado). Limite honesto: a VarP satura perto de 0,053
mesmo com pesos extremos dentro de um K6 — matar um clique por
dentro ficou difícil, e o limiar 0,05 fica a 0,0009 da morte de A.
Qualificação (20/11): a saturação perto de 0,053 só vale na
configuração de 3 rastros dominantes (3×peso 1e6 dentro do K6 dá
0,0556); com UM rastro extremo a VarP chega a 0,1350 (x1000) e ao
teto 0,1389 — a saturação depende de quantos rastros dominam, não só
do peso.

## ISC: topológico por decisão (19/11)

O teste de invariância mostrou o ISC em 1,00 sob qualquer
reponderação. A decisão (Dan delegou: "me aconselhe e execute") é
aceitar a cegueira a pesos como limite conhecido, não como defeito:
ISC_Local é uma contagem — arestas válidas sobre arestas possíveis —
e uma medida de densidade deve ser invariante a reponderação. Ponderar
o ISC ou reproduziria a contagem, ou viraria uma medida disfarçada de
uniformidade (o que a VarPn já mede), ou exigiria um corte arbitrário
de peso para a validade, sem a correção de princípio que a Var teve.
No gym não há um acerto externo como o VAI/FICA da rede-pulsos para
definir validade por ablação (C3). Divisão de trabalho: o ISC vê
quanta estrutura existe (topologia), a VarPn vê como ela está
distribuída (geometria). Condição de reabertura: se o gym ganhar um
critério externo de acerto, o ISC pode herdar sensibilidade a peso
pela validade C3. Com isso, a aplicação do critério de invariância
às duas métricas está fechada: a Var foi corrigida, o ISC foi
documentado como topológico. Suíte segue 89 testes.

## VarP normalizada (19/11)

O 0,05 não vale para todo tamanho: um rastro x10 mata um K4 (0,0808),
é tolerado num K6 (0,0243) e some num K10 (0,0036). A correção, como
o r da integral cilíndrica, pertence à quantidade, não ao limiar:
**VarPn = VarP / teto(n), teto(n) = (n-1)/n²** — o teto é o máximo
possível da VarP num grafo com n nós (autovalores em [0,1] somando 1,
pelo menos um zero; a variância é máxima com toda a massa num só
autovalor), verificado numericamente: K4 0,1875, K5 0,1600, K6 0,1389,
K8 0,1094, K10 0,0900. A VarPn vive em [0, 1] e é livre de tamanho;
o limiar único é **0,36** — a razão do K6 preservada (0,05/0,1389).

**Adotada em 19/11, por decisão do Dan.** A regra de emergência agora
é ISC ≥ 0,85 E VarPn ≤ 0,36; a VarP bruta fica no relatório como
diagnóstico. Consequências verificadas: o loop mantém a mesma história
(meta no ep 4, estabilidade 1,0, tensão em 6/12, Gini final 0,333,
Var média final 0,0827, agora normalizada); a demo da geodésica foi
recalibrada (A tem VarPn 0,3662; casos 0,36→0,40 aprovado,
isc 0,85→0,25 suspeito, 0,36→0,03 rejeitado). Um veredito muda em
relação ao 0,05: um x100 num K10 era Símbolo (0,0431 < 0,05) e agora
morre (VarPn 0,479 > 0,36) — era o caso onde o limiar antigo estava
mais frouxo. Limite honesto: a margem da morte de A na geodésica
continua fina (0,3662 contra o limiar 0,36). Suíte com 89 testes.

## Rodar tudo

```bash
cd ~/workspace/cono-causal-gym
python3 -m unittest discover -s testes -v
python3 -m cono_gym.demo
python3 -m cono_gym.demo_mcp
python3 -m cono_gym.demo_episodios
python3 -m cono_gym.demo_geodesica
```
