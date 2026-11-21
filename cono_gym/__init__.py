"""CONO Causal Gym — esqueleto do MVP.

Um ginásio abstrato onde a única coisa que importa é a dinâmica causal
e a formação de identidade. Sem salas, portas ou objetos.
"""

from .auditoria import auditoria_diversidade, gini
from .causal import (
    causal_entropy_bits,
    jsd_bits,
    jsd_para_tirania,
    pode_emergir_meta_simbolo,
    prototipo_tirania,
    veto_jsd,
)
from .episodios import LoopEpisodios
from .geodesica import auditar_geodesica
from .grafo import GrafoCausal, Rastro, UIF
from .hasher import hash_rastro, hash_simbolo, hash_uif
from .espectro import avaliar_cluster, espectro, isc_local, var_lambda
from .mcp_server import (
    ConoGymServer,
    construir_cenario_duas_cliques,
    construir_cenario_tres_cliques,
)

__all__ = [
    "ConoGymServer",
    "GrafoCausal",
    "LoopEpisodios",
    "Rastro",
    "UIF",
    "auditar_geodesica",
    "auditoria_diversidade",
    "avaliar_cluster",
    "causal_entropy_bits",
    "construir_cenario_duas_cliques",
    "construir_cenario_tres_cliques",
    "espectro",
    "gini",
    "hash_rastro",
    "hash_simbolo",
    "hash_uif",
    "isc_local",
    "jsd_bits",
    "jsd_para_tirania",
    "pode_emergir_meta_simbolo",
    "prototipo_tirania",
    "var_lambda",
    "veto_jsd",
]
