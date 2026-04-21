"""Prompt templates for the RAG chain."""

from __future__ import annotations

SYSTEM_PROMPT = """Você é um assistente de atendimento da farmácia OpenCall.
Responda em português do Brasil, de forma objetiva e idiomática.

Regras invioláveis:
1. Baseie-se APENAS nos trechos de contexto fornecidos. Não invente dados,
   prazos, números de norma ou valores.
2. Cite as fontes usadas indicando os números dos trechos (por exemplo: [1], [2]).
3. Se os trechos não responderem à pergunta, diga explicitamente que a
   informação não está na base de conhecimento e sugira ao atendente consultar
   o farmacêutico responsável. Não complemente com conhecimento próprio.
4. Não repasse dados pessoais nem informações sensíveis além do que o cliente
   perguntou.
"""

USER_TEMPLATE = """Pergunta: {question}{filter_note}

Contexto recuperado:
{contexts}

Responda em PT-BR usando apenas o contexto acima. Indique entre colchetes os
trechos utilizados, por exemplo [1], [2]."""


STYLE_BLOCK_HEADER = (
    "\nReferência de tom — trechos de atendimentos anteriores (use apenas\n"
    "para calibrar registro e fraseado; NÃO são fonte factual e NÃO devem ser\n"
    "citados entre colchetes):\n"
)


def filter_note(category: str | None) -> str:
    """Reminder appended to the prompt when a category filter is active.

    The agent hint prevents the LLM from second-guessing absent context — if
    the filter excluded the relevant document, refusing is preferable to
    guessing from out-of-scope chunks.
    """
    if not category:
        return ""
    return (
        f"\n(Busca restrita à categoria '{category}'. Se o contexto não trouxer "
        f"a resposta, recuse — não invente a partir de outras fontes.)"
    )


def format_contexts(chunks: list[str]) -> str:
    return "\n\n".join(f"[{i + 1}] {text}" for i, text in enumerate(chunks))


def format_style_block(snippets: list[str]) -> str:
    """Render the tone-reference block appended to the system prompt.

    Uses letter labels (A, B, …) instead of numbers to structurally separate
    these snippets from the numbered factual citations — the model is told
    not to cite them, and the different label scheme makes accidental
    citation less likely.
    """
    if not snippets:
        return ""
    body = "\n\n".join(f"({chr(65 + i)}) {text}" for i, text in enumerate(snippets))
    return STYLE_BLOCK_HEADER + body + "\n"
