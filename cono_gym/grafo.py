"""Grafo causal do gym: UIFs como nós, Rastros Causais como arestas.

Não existem objetos físicos aqui. Existem apenas identidades e relações
causais entre elas. O grafo é dirigido nos rastros (origem -> destino),
mas o espectro de Laplace é calculado sobre a versão não dirigida:
a identidade de um cluster não depende da direção do olhar.
"""

from dataclasses import dataclass, field

from .hasher import hash_rastro, hash_uif


@dataclass(frozen=True)
class UIF:
    """Uma identidade. O hash é calculado dos campos de identidade,
    nunca do estado mutável (que nem existe nesta classe)."""

    serial: str
    tipo_agente: str
    funcao_s: str
    hash_uif: str = field(init=False)

    def __post_init__(self):
        object.__setattr__(
            self, "hash_uif", hash_uif(self.serial, self.tipo_agente, self.funcao_s)
        )


@dataclass(frozen=True)
class Rastro:
    """Um rastro causal entre duas UIFs, com peso e tipo de relação."""

    origem: str  # hash_uif
    destino: str  # hash_uif
    tipo_relacao: str
    peso: float = 1.0
    hash_rastro: str = field(init=False)

    def __post_init__(self):
        object.__setattr__(
            self,
            "hash_rastro",
            hash_rastro(self.origem, self.destino, self.tipo_relacao),
        )


class GrafoCausal:
    """Grafo em memória. Só causalidade e identidade."""

    def __init__(self):
        self._uifs = {}  # hash_uif -> UIF, em ordem de inserção
        self._rastros = {}  # frozenset({a, b}) -> Rastro (não dirigido p/ o espectro)

    def adicionar_uif(self, uif: UIF) -> UIF:
        """Adiciona uma UIF. O serial é único (deduplicação natural):
        um serial já usado — mesmo com outro tipo ou função — é
        recusado, porque o serial é o identificador de gênese."""
        if any(outra.serial == uif.serial for outra in self._uifs.values()):
            raise ValueError(f"serial já existe: {uif.serial}")
        if uif.hash_uif in self._uifs:
            raise ValueError(f"Hash_UIF já existe: {uif.hash_uif[:12]}…")
        self._uifs[uif.hash_uif] = uif
        return uif

    def depositar_rastro(
        self, origem: str, destino: str, tipo_relacao: str, peso: float = 1.0
    ) -> Rastro:
        """Deposita um rastro. Depositar de novo no mesmo par atualiza
        o peso (o último depósito vale); a contagem de arestas não muda."""
        if origem == destino:
            raise ValueError("rastro não pode ligar uma UIF a ela mesma")
        if origem not in self._uifs or destino not in self._uifs:
            raise ValueError("origem e destino precisam ser UIFs do grafo")
        rastro = Rastro(origem, destino, tipo_relacao, peso)
        self._rastros[frozenset((origem, destino))] = rastro
        return rastro

    def n_nos(self) -> int:
        return len(self._uifs)

    def n_arestas(self) -> int:
        return len(self._rastros)

    def max_arestas(self) -> int:
        n = len(self._uifs)
        return n * (n - 1) // 2

    def hashes(self):
        """Hashes das UIFs, na ordem em que foram adicionadas."""
        return list(self._uifs)

    def vizinhanca(self, hash_uif: str, raio: int = 1):
        """Vista causal local: hashes + pesos dos rastros até `raio` de
        distância. É o que get_local_causal_view vai expor no MCP."""
        if hash_uif not in self._uifs:
            raise ValueError("UIF desconhecida")
        vistos = {hash_uif}
        fronteira = {hash_uif}
        for _ in range(raio):
            proximos = set()
            for rastro in self._rastros.values():
                if rastro.origem in fronteira and rastro.destino not in vistos:
                    proximos.add(rastro.destino)
                if rastro.destino in fronteira and rastro.origem not in vistos:
                    proximos.add(rastro.origem)
            vistos |= proximos
            fronteira = proximos
        return {
            h: [
                (r.hash_rastro, r.peso)
                for r in self._rastros.values()
                if h in (r.origem, r.destino)
            ]
            for h in sorted(vistos)
        }

    def uif_por_hash(self, hash_uif: str):
        """A UIF, ou None. O servidor expõe só hash + tipo, nunca o resto."""
        return self._uifs.get(hash_uif)

    def rastro_por_hash(self, hash_rastro: str):
        """Um rastro pelo seu hash de custódia, ou None."""
        for rastro in self._rastros.values():
            if rastro.hash_rastro == hash_rastro:
                return rastro
        return None

    def todos_rastros(self):
        return list(self._rastros.values())

    def pesos(self):
        """Todos os pesos dos rastros — matéria-prima da auditoria."""
        return [r.peso for r in self._rastros.values()]

    def subgrafo(self, hashes):
        """Grafo induzido por um conjunto de hashes: só as UIFs dadas e
        os rastros entre elas. É assim que um cluster local é avaliado
        sem o resto do mundo interferir."""
        novo = GrafoCausal()
        for h in hashes:
            if h in self._uifs:
                novo.adicionar_uif(self._uifs[h])
        for rastro in self._rastros.values():
            if rastro.origem in novo._uifs and rastro.destino in novo._uifs:
                novo.depositar_rastro(
                    rastro.origem, rastro.destino, rastro.tipo_relacao, rastro.peso
                )
        return novo

    def matriz_adjacencia(self):
        """Matriz de adjacência simétrica, na ordem de inserção das UIFs."""
        hs = self.hashes()
        idx = {h: i for i, h in enumerate(hs)}
        n = len(hs)
        adj = [[0.0] * n for _ in range(n)]
        for rastro in self._rastros.values():
            i, j = idx[rastro.origem], idx[rastro.destino]
            adj[i][j] = rastro.peso
            adj[j][i] = rastro.peso
        return adj
