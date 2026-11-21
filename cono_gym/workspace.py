"""Espaço J — o análogo funcional do J-space no CONO Causal Gym.

Inspiração: Anthropic, "Verbalizable Representations Form a Global
Workspace in Language Models" (jul/2026). Lá, o J-space é o espaço
interno onde o modelo segura conceitos verbalizáveis enquanto raciocina
— pequeno, seletivo, relatável, usável no raciocínio, e editável de um
jeito que muda o comportamento (trocar "aranha" por "formiga" muda a
resposta de oito para seis pernas).

Aqui não há vocabulário nem camadas para apontar uma lente — o gym é
topologia pura. O que dá para copiar é a forma funcional, em cinco
propriedades, e cada uma tem um teste:

1. **Pequeno e seletivo.** Capacidade 3 (v0.1). Segurar um quarto
   conteúdo despeja o mais antigo (FIFO). O workspace não é memória
   infinita — é o que está em mente agora.
2. **Relatável.** `relatar()` devolve o conteúdo em forma legível. O
   Meta-Símbolo pode dizer o que está segurando.
3. **Segurável.** O conteúdo persiste entre episódios até ser editado,
   despejado ou limpo — como segurar "frutas cítricas" na mente
   enquanto se copia outra frase.
4. **Usável no raciocínio.** O conteúdo é uma direção: uma geodésica
   em rascunho (regra/de/para/motivo). `propor_do_workspace` leva a
   direção segurada para a auditoria — a direção nasce dentro, não
   fora.
5. **Editável e causal.** Editar o conteúdo segurado muda o veredito
   da auditoria. É o teste da troca: mudar o `para` de 0,40 para 0,03
   transforma uma geodésica aprovada numa rejeitada — a edição mora
   no workspace, o efeito mora no comportamento.

Limite honesto: isto é um análogo funcional, não o J-space. Não prova
consciência, prova arquitetura — a mesma ressalva do paper. A semente
das direções (o que o Meta-Símbolo segura) vem das medições do gym
(v0.1, em `mcp_server._meta_propor_direcao`). A visão de longo prazo,
dada pelo Dan em 20/11, é semear o workspace com traços do raciocínio
dele — ele doaria o próprio raciocínio via EEG para treinar a geração
do workspace. EEG hoje decodifica sinais grossos (atenção, imagética
motora), não conteúdo de raciocínio — a semente real, por enquanto,
são os traços de raciocínio dele em texto: decisões e justificativas.
"""

from dataclasses import dataclass, field

CAPACIDADE_PADRAO = 3


@dataclass
class ConteudoJ:
    """Uma direção segurada no workspace: uma geodésica em rascunho."""

    id: int
    tipo: str  # "direcao" | "preocupacao"
    regra: str
    de: float
    para: float
    motivo: str
    proposto: bool = field(default=False)

    def para_payload(self) -> dict:
        """Converte a direção em payload de geodésica."""
        return {
            "mudanca_regra": f"{self.regra} {self.de} -> {self.para}",
            "efeito_esperado": self.motivo,
            "regra": self.regra,
            "de": self.de,
            "para": self.para,
        }

    def para_relato(self) -> dict:
        return {
            "id": self.id,
            "tipo": self.tipo,
            "regra": self.regra,
            "de": self.de,
            "para": self.para,
            "motivo": self.motivo,
            "proposto": self.proposto,
        }


class EspacoJ:
    """O workspace do Meta-Símbolo: pequeno, seletivo, relatável."""

    def __init__(self, capacidade: int = CAPACIDADE_PADRAO) -> None:
        self.capacidade = capacidade
        self._conteudos: list[ConteudoJ] = []
        self._proximo_id = 1

    def __len__(self) -> int:
        return len(self._conteudos)

    def segurar(self, tipo, regra, de, para, motivo) -> dict:
        """Segura uma direção. Se o workspace está cheio, despeja a mais
        antiga. Retorna a direção segurada e, se houve, a despejada."""
        despejado = None
        if len(self._conteudos) >= self.capacidade:
            despejado = self._conteudos.pop(0)
        conteudo = ConteudoJ(
            id=self._proximo_id,
            tipo=tipo,
            regra=regra,
            de=float(de),
            para=float(para),
            motivo=motivo,
        )
        self._proximo_id += 1
        self._conteudos.append(conteudo)
        return {
            "segurado": conteudo.para_relato(),
            "despejado": despejado.para_relato() if despejado else None,
        }

    def relatar(self) -> list[dict]:
        """O que o Meta-Símbolo está segurando, em forma legível."""
        return [c.para_relato() for c in self._conteudos]

    def buscar(self, conteudo_id: int) -> ConteudoJ | None:
        return next((c for c in self._conteudos if c.id == conteudo_id), None)

    def editar(self, conteudo_id: int, **mudancas) -> dict:
        """Edita o conteúdo segurado. A edição muda o que será auditado
        — é o teste da troca."""
        conteudo = self.buscar(conteudo_id)
        if conteudo is None:
            raise ValueError(f"direção desconhecida: {conteudo_id}")
        permitidos = {"tipo", "regra", "de", "para", "motivo"}
        for chave, valor in mudancas.items():
            if chave not in permitidos:
                raise ValueError(f"campo não editável: {chave}")
            if chave in ("de", "para"):
                valor = float(valor)
            setattr(conteudo, chave, valor)
        return conteudo.para_relato()

    def limpar(self) -> None:
        self._conteudos.clear()
