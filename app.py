"""Bot de Atendimento WhatsApp — ponto de entrada da aplicação Flask.

Recebe mensagens do WhatsApp via webhook do Twilio, responde dúvidas
frequentes, agenda reuniões automaticamente e envia lembretes via pywhatkit.
"""

import logging

from flask import Flask, request
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

import config
from bot import lembretes, roteador

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


def _requisicao_valida() -> bool:
    """Confere a assinatura do Twilio para bloquear requisições forjadas."""
    if not config.TWILIO_AUTH_TOKEN:
        # Sem token configurado (ambiente de desenvolvimento), não valida.
        return True
    validador = RequestValidator(config.TWILIO_AUTH_TOKEN)
    return validador.validate(
        request.url,
        request.form,
        request.headers.get("X-Twilio-Signature", ""),
    )


@app.route("/webhook", methods=["POST"])
def webhook():
    """Endpoint chamado pelo Twilio a cada mensagem recebida no WhatsApp."""
    if not _requisicao_valida():
        logger.warning("Requisição com assinatura Twilio inválida bloqueada.")
        return "Assinatura inválida", 403

    numero = request.form.get("From", "")
    mensagem = request.form.get("Body", "")
    logger.info("Mensagem de %s: %s", numero, mensagem)

    try:
        texto_resposta = roteador.responder(numero, mensagem)
    except Exception:
        logger.exception("Erro ao processar mensagem de %s", numero)
        texto_resposta = (
            "😓 Ops, tive um problema técnico. Tente novamente em instantes, "
            "ou digite *humano* para falar com a equipe."
        )

    resposta = MessagingResponse()
    resposta.message(texto_resposta)
    return str(resposta), 200, {"Content-Type": "application/xml"}


@app.route("/health", methods=["GET"])
def health():
    """Endpoint de monitoramento (uptime checks, load balancer etc.)."""
    return {"status": "ok", "empresa": config.NOME_EMPRESA}


if __name__ == "__main__":
    lembretes.iniciar_servico()
    logger.info("Bot de atendimento iniciado na porta %d.", config.PORT)
    app.run(host="0.0.0.0", port=config.PORT, debug=config.DEBUG)
