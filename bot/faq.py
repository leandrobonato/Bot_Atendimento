"""Motor de FAQ: encontra a melhor resposta para a dúvida do cliente.

Combina duas estratégias de pontuação, sem dependências pesadas de NLP:
1. Interseção de palavras-chave cadastradas no faq.json.
2. Similaridade textual (difflib) contra as perguntas de exemplo.
"""

import json
import unicodedata
from difflib import SequenceMatcher

import config

# Pontuação mínima para considerar que a FAQ realmente responde a pergunta.
LIMIAR_CONFIANCA = 0.45

_faqs_cache: list[dict] | None = None


def _normalizar(texto: str) -> str:
    """Remove acentos, pontuação e caixa alta para comparação justa."""
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return "".join(c if c.isalnum() or c.isspace() else " " for c in texto)


def carregar_faqs() -> list[dict]:
    global _faqs_cache
    if _faqs_cache is None:
        with open(config.ARQUIVO_FAQ, encoding="utf-8") as f:
            _faqs_cache = json.load(f)
    return _faqs_cache


def _pontuar(mensagem: str, faq: dict) -> float:
    msg_norm = _normalizar(mensagem)
    palavras_msg = set(msg_norm.split())

    # Estratégia 1: proporção de palavras-chave presentes na mensagem
    chaves = {_normalizar(p).strip() for p in faq["palavras_chave"]}
    acertos = sum(1 for chave in chaves if chave in palavras_msg)
    pontos_chave = min(acertos / 2, 1.0)  # 2+ palavras-chave = confiança máxima

    # Estratégia 2: similaridade com as perguntas de exemplo
    pontos_similaridade = max(
        (
            SequenceMatcher(None, msg_norm, _normalizar(exemplo)).ratio()
            for exemplo in faq["perguntas_exemplo"]
        ),
        default=0.0,
    )

    return max(pontos_chave, pontos_similaridade)


def buscar_resposta(mensagem: str) -> str | None:
    """Retorna a resposta da FAQ mais adequada, ou None se nenhuma for confiável."""
    melhor_faq, melhor_pontuacao = None, 0.0
    for faq in carregar_faqs():
        pontuacao = _pontuar(mensagem, faq)
        if pontuacao > melhor_pontuacao:
            melhor_faq, melhor_pontuacao = faq, pontuacao

    if melhor_faq and melhor_pontuacao >= LIMIAR_CONFIANCA:
        return melhor_faq["resposta"]
    return None


def listar_topicos() -> str:
    """Monta um menu com os assuntos disponíveis na FAQ."""
    linhas = [f"• {faq['perguntas_exemplo'][0]}" for faq in carregar_faqs()]
    return "\n".join(linhas)
