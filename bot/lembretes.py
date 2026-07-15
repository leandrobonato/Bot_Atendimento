"""Lembretes automáticos de reunião enviados via pywhatkit.

O pywhatkit envia mensagens pelo WhatsApp Web, portanto exige uma máquina
com navegador e sessão do WhatsApp logada. Por isso este serviço é opcional
e controlado pela variável de ambiente LEMBRETES_ATIVOS.

Um thread em segundo plano verifica a agenda a cada minuto e dispara o
lembrete quando falta LEMBRETE_ANTECEDENCIA_MIN minutos para a reunião.
"""

import json
import logging
import threading
import time as time_module
from datetime import datetime, timedelta

import config
from bot import agendamento

logger = logging.getLogger(__name__)

INTERVALO_VERIFICACAO_SEG = 60


def _numero_para_pywhatkit(numero: str) -> str:
    """Converte 'whatsapp:+5511999998888' para '+5511999998888'."""
    return numero.replace("whatsapp:", "").strip()


def _enviar_whatsapp(numero: str, mensagem: str) -> None:
    # Importação tardia: o pywhatkit acessa a internet e o navegador ao ser
    # importado, o que quebraria a aplicação em servidores sem interface.
    import pywhatkit

    pywhatkit.sendwhatmsg_instantly(
        phone_no=_numero_para_pywhatkit(numero),
        message=mensagem,
        wait_time=15,
        tab_close=True,
    )


def _marcar_lembrete_enviado(registro: dict) -> None:
    with agendamento._trava_arquivo:
        todos = agendamento._carregar_agendamentos()
        for ag in todos:
            if ag["numero"] == registro["numero"] and ag["inicio"] == registro["inicio"]:
                ag["lembrete_enviado"] = True
        with open(config.ARQUIVO_AGENDAMENTOS, "w", encoding="utf-8") as f:
            json.dump(todos, f, ensure_ascii=False, indent=2)


def _verificar_e_enviar() -> None:
    agora = datetime.now()
    janela = timedelta(minutes=config.LEMBRETE_ANTECEDENCIA_MIN)

    for ag in agendamento.listar_agendamentos_pendentes():
        if ag.get("lembrete_enviado"):
            continue
        inicio = datetime.fromisoformat(ag["inicio"])
        if agora >= inicio - janela:
            mensagem = (
                f"🔔 Olá, {ag['nome']}! Lembrete da sua reunião com a "
                f"{config.NOME_EMPRESA} hoje às *{inicio:%H:%M}*. Até já!"
            )
            try:
                _enviar_whatsapp(ag["numero"], mensagem)
                _marcar_lembrete_enviado(ag)
                logger.info("Lembrete enviado para %s (reunião %s)", ag["numero"], ag["inicio"])
            except Exception:
                logger.exception("Falha ao enviar lembrete para %s", ag["numero"])


def _laco_principal() -> None:
    logger.info(
        "Serviço de lembretes ativo (antecedência: %d min).",
        config.LEMBRETE_ANTECEDENCIA_MIN,
    )
    while True:
        try:
            _verificar_e_enviar()
        except Exception:
            logger.exception("Erro no ciclo de verificação de lembretes.")
        time_module.sleep(INTERVALO_VERIFICACAO_SEG)


def iniciar_servico() -> None:
    """Inicia o thread de lembretes, se habilitado nas configurações."""
    if not config.LEMBRETES_ATIVOS:
        logger.info("Serviço de lembretes desativado (LEMBRETES_ATIVOS=false).")
        return
    thread = threading.Thread(target=_laco_principal, daemon=True, name="lembretes")
    thread.start()
