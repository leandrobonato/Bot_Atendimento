"""Roteador de intenções: decide como responder cada mensagem recebida.

Ordem de prioridade:
1. Fluxo ativo na sessão (ex.: agendamento em andamento).
2. Comandos explícitos (agendar, menu, humano...).
3. Saudações.
4. Busca na FAQ.
5. Mensagem padrão com o menu de opções.
"""

import re

import config
from bot import agendamento, faq, sessoes

SAUDACOES = re.compile(
    r"^\s*(oi+|ol[aá]+|hey|hello|opa|e\s*a[ie]|bom\s*dia|boa\s*tarde|boa\s*noite)\b",
    re.IGNORECASE,
)

COMANDOS_AGENDAR = ("agendar", "agenda", "marcar", "reuniao", "reunião", "meeting")
COMANDOS_MENU = ("menu", "opções", "opcoes", "ajuda", "help", "inicio", "início", "0")
COMANDOS_HUMANO = ("humano", "atendente", "pessoa", "falar com alguem", "falar com alguém")


def _mensagem_boas_vindas() -> str:
    return (
        f"👋 Olá! Sou o assistente virtual da *{config.NOME_EMPRESA}*.\n\n"
        "Posso te ajudar com:\n"
        "1️⃣ *Dúvidas frequentes* — é só perguntar!\n"
        "2️⃣ *Agendar uma reunião* — digite *agendar*\n"
        "3️⃣ *Falar com um atendente* — digite *humano*\n\n"
        "Como posso ajudar? 😊"
    )


def _mensagem_menu() -> str:
    return (
        "ℹ️ *Como posso ajudar:*\n\n"
        "📅 Digite *agendar* para marcar uma reunião\n"
        "🙋 Digite *humano* para falar com um atendente\n\n"
        "Ou pergunte sobre:\n" + faq.listar_topicos()
    )


def _mensagem_nao_entendi() -> str:
    return (
        "🤔 Hmm, não encontrei uma resposta para isso.\n\n"
        "Digite *menu* para ver o que sei responder, "
        "*agendar* para marcar uma reunião ou *humano* para falar com a equipe."
    )


def _mensagem_humano() -> str:
    return (
        "🙋 Certo! Já avisei nossa equipe e um atendente vai te responder "
        "por aqui em instantes.\n\n"
        f"_Horário de atendimento humano: {config.HORARIO_ABERTURA:%H:%M} às "
        f"{config.HORARIO_FECHAMENTO:%H:%M}, de segunda a sexta._"
    )


def responder(numero: str, mensagem: str) -> str:
    """Gera a resposta do bot para a mensagem recebida de um cliente."""
    sessao = sessoes.obter(numero)
    texto = mensagem.strip().lower()

    # 1. Cliente no meio de um fluxo? Continua de onde parou.
    if sessao["fluxo"] == "agendamento":
        return agendamento.processar(sessao, mensagem, numero)

    # 2. Comandos explícitos
    if any(cmd in texto for cmd in COMANDOS_AGENDAR):
        return agendamento.iniciar(sessao)
    if texto in COMANDOS_MENU:
        return _mensagem_menu()
    if any(cmd in texto for cmd in COMANDOS_HUMANO):
        return _mensagem_humano()

    # 3. Saudações
    if SAUDACOES.match(texto):
        return _mensagem_boas_vindas()

    # 4. FAQ
    resposta_faq = faq.buscar_resposta(mensagem)
    if resposta_faq:
        return resposta_faq

    # 5. Não entendeu
    return _mensagem_nao_entendi()
