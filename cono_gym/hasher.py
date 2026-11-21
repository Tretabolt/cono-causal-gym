"""CanonicalHasher — Camada 0 do MNHI 3.0, versão do gym.

Separação irredutível: identidade imutável vs estado mutável.

- Hash_UIF depende só de (Serial, Tipo_Agente, Função_S). Nunca do estado.
  Dois UIFs com a mesma identidade têm o mesmo hash, qualquer que seja
  o estado mutável que carreguem depois.
- Hash_Rastro encadeia origem, destino e tipo de relação: é a cadeia
  de custódia causal. A ordem importa: (A, B) não é (B, A).
- Hash_Símbolo amarra o espectro de Laplace normalizado ordenado do
  cluster: o símbolo é identificado pela sua forma, não pelos seus pesos.
"""

import hashlib


def _sha(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def hash_uif(serial: str, tipo_agente: str, funcao_s: str) -> str:
    """Identidade imutável de uma UIF. Não recebe estado."""
    return _sha(f"{serial}|{tipo_agente}|{funcao_s}")


def hash_rastro(hash_origem: str, hash_destino: str, tipo_relacao: str) -> str:
    """Um rastro causal: de onde veio, para onde vai, que relação é."""
    return _sha(f"{hash_origem}|{hash_destino}|{tipo_relacao}")


def hash_simbolo(serial_simbolo: str, espectro_ordenado) -> str:
    """Identidade de um Símbolo: seu serial + seu espectro ordenado."""
    espectro_txt = ",".join(f"{v:.10f}" for v in espectro_ordenado)
    return _sha(f"{serial_simbolo}|{espectro_txt}")
