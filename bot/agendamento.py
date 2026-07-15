"""Fluxo de agendamento de reuniões conduzido pelo bot.

Máquina de estados simples: nome → data → horário → confirmação.
Os agendamentos são persistidos em JSON e o bot valida automaticamente
horário comercial, datas passadas e conflitos de agenda.
"""

import json
import re
import threading
from datetime import date, datetime, time, timedelta

import config

_trava_arquivo = threading.Lock()

ETAPA_NOME = "nome"
ETAPA_DATA = "data"
ETAPA_HORARIO = "horario"
ETAPA_CONFIRMACAO = "confirmacao"

DIAS_SEMANA = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------

def _carregar_agendamentos() -> list[dict]:
    if not config.ARQUIVO_AGENDAMENTOS.exists():
        return []
    with open(config.ARQUIVO_AGENDAMENTOS, encoding="utf-8") as f:
        return json.load(f)


def _salvar_agendamento(registro: dict) -> None:
    with _trava_arquivo:
        agendamentos = _carregar_agendamentos()
        agendamentos.append(registro)
        with open(config.ARQUIVO_AGENDAMENTOS, "w", encoding="utf-8") as f:
            json.dump(agendamentos, f, ensure_ascii=False, indent=2)


def listar_agendamentos_pendentes() -> list[dict]:
    """Agendamentos futuros — usado pelo serviço de lembretes."""
    agora = datetime.now()
    pendentes = []
    for ag in _carregar_agendamentos():
        inicio = datetime.fromisoformat(ag["inicio"])
        if inicio > agora:
            pendentes.append(ag)
    return pendentes


# ---------------------------------------------------------------------------
# Interpretação de data e hora em linguagem natural (pt-BR)
# ---------------------------------------------------------------------------

def _interpretar_data(texto: str) -> date | None:
    texto = texto.strip().lower()
    hoje = date.today()

    if "hoje" in texto:
        return hoje
    if "amanha" in texto or "amanhã" in texto:
        return hoje + timedelta(days=1)

    # Nome do dia da semana ("quinta", "sexta-feira") → próxima ocorrência
    for indice, nome in enumerate(DIAS_SEMANA):
        if nome in texto or nome.replace("ç", "c").replace("á", "a") in texto:
            delta = (indice - hoje.weekday()) % 7
            return hoje + timedelta(days=delta or 7)

    # Formatos numéricos: 25/12, 25/12/2026, 25-12
    match = re.search(r"(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?", texto)
    if match:
        dia, mes = int(match.group(1)), int(match.group(2))
        ano = int(match.group(3)) if match.group(3) else hoje.year
        if ano < 100:
            ano += 2000
        try:
            data_informada = date(ano, mes, dia)
        except ValueError:
            return None
        # Sem ano explícito e data já passou? Assume o próximo ano.
        if not match.group(3) and data_informada < hoje:
            data_informada = date(ano + 1, mes, dia)
        return data_informada

    return None


def _interpretar_horario(texto: str) -> time | None:
    texto = texto.strip().lower()

    # Formatos: 14:30, 14h30, 14h, 14 horas, 9
    match = re.search(r"(\d{1,2})(?:[:h](\d{2}))?", texto)
    if not match:
        return None

    hora = int(match.group(1))
    minuto = int(match.group(2)) if match.group(2) else 0

    # "2 da tarde" → 14h
    if hora <= 12 and ("tarde" in texto or "noite" in texto):
        hora += 12

    if not (0 <= hora <= 23 and 0 <= minuto <= 59):
        return None
    return time(hora, minuto)


# ---------------------------------------------------------------------------
# Validações de agenda
# ---------------------------------------------------------------------------

def _validar_data(data_reuniao: date) -> str | None:
    """Retorna mensagem de erro, ou None se a data for válida."""
    if data_reuniao < date.today():
        return "📅 Essa data já passou! Me diga uma data futura, por favor."
    if data_reuniao.weekday() >= 5:
        return (
            "📅 Atendemos apenas em *dias úteis* (segunda a sexta). "
            "Qual outro dia fica bom para você?"
        )
    return None


def _validar_horario(data_reuniao: date, horario: time) -> str | None:
    inicio = datetime.combine(data_reuniao, horario)
    fim = inicio + timedelta(minutes=config.DURACAO_REUNIAO_MIN)

    abertura = datetime.combine(data_reuniao, config.HORARIO_ABERTURA)
    fechamento = datetime.combine(data_reuniao, config.HORARIO_FECHAMENTO)
    if inicio < abertura or fim > fechamento:
        return (
            f"🕘 Nosso horário para reuniões é das "
            f"*{config.HORARIO_ABERTURA:%H:%M} às {config.HORARIO_FECHAMENTO:%H:%M}*. "
            "Qual horário dentro desse período prefere?"
        )

    if inicio <= datetime.now():
        return "⏰ Esse horário já passou! Me diga um horário futuro, por favor."

    # Conflito com reuniões já marcadas
    for ag in _carregar_agendamentos():
        inicio_existente = datetime.fromisoformat(ag["inicio"])
        fim_existente = inicio_existente + timedelta(minutes=config.DURACAO_REUNIAO_MIN)
        if inicio < fim_existente and fim > inicio_existente:
            sugestao = fim_existente.strftime("%H:%M")
            return (
                "😕 Esse horário já está reservado. "
                f"O próximo horário livre é às *{sugestao}*. Pode ser?"
            )

    return None


# ---------------------------------------------------------------------------
# Máquina de estados do fluxo de agendamento
# ---------------------------------------------------------------------------

def iniciar(sessao: dict) -> str:
    sessao["fluxo"] = "agendamento"
    sessao["etapa"] = ETAPA_NOME
    sessao["dados"] = {}
    return (
        "📅 Ótimo, vamos agendar sua reunião!\n\n"
        "Para começar, qual é o seu *nome*?\n\n"
        "_(Digite *cancelar* a qualquer momento para desistir.)_"
    )


def processar(sessao: dict, mensagem: str, numero: str) -> str:
    """Avança o fluxo de agendamento com base na resposta do cliente."""
    if mensagem.strip().lower() in ("cancelar", "cancela", "desistir", "sair"):
        sessao["fluxo"] = None
        sessao["etapa"] = None
        return "Tudo bem, agendamento cancelado! Se precisar, é só digitar *agendar*. 😉"

    etapa = sessao["etapa"]
    dados = sessao["dados"]

    if etapa == ETAPA_NOME:
        nome = mensagem.strip()
        if len(nome) < 2:
            return "Não entendi seu nome. 😅 Pode digitar de novo?"
        dados["nome"] = nome.title()
        sessao["etapa"] = ETAPA_DATA
        return (
            f"Prazer, {dados['nome']}! 🤝\n\n"
            "Para qual *dia* você quer a reunião?\n"
            "Pode responder como preferir: _amanhã_, _sexta_, _25/07_..."
        )

    if etapa == ETAPA_DATA:
        data_reuniao = _interpretar_data(mensagem)
        if data_reuniao is None:
            return (
                "Não consegui entender a data. 😅\n"
                "Tente algo como: *amanhã*, *quinta* ou *25/07*."
            )
        erro = _validar_data(data_reuniao)
        if erro:
            return erro
        dados["data"] = data_reuniao.isoformat()
        sessao["etapa"] = ETAPA_HORARIO
        return (
            f"Perfeito, dia *{data_reuniao:%d/%m/%Y}*! 📆\n\n"
            f"E qual *horário*? Atendemos das "
            f"{config.HORARIO_ABERTURA:%H:%M} às {config.HORARIO_FECHAMENTO:%H:%M}."
        )

    if etapa == ETAPA_HORARIO:
        horario = _interpretar_horario(mensagem)
        if horario is None:
            return "Não entendi o horário. 😅 Tente algo como *14h*, *14:30* ou *2 da tarde*."
        data_reuniao = date.fromisoformat(dados["data"])
        erro = _validar_horario(data_reuniao, horario)
        if erro:
            return erro
        dados["horario"] = horario.strftime("%H:%M")
        sessao["etapa"] = ETAPA_CONFIRMACAO
        return (
            "Confira os dados da reunião: 👇\n\n"
            f"👤 *Nome:* {dados['nome']}\n"
            f"📆 *Data:* {data_reuniao:%d/%m/%Y}\n"
            f"🕐 *Horário:* {dados['horario']}\n"
            f"⏱️ *Duração:* {config.DURACAO_REUNIAO_MIN} min\n\n"
            "Posso confirmar? (*sim* / *não*)"
        )

    if etapa == ETAPA_CONFIRMACAO:
        resposta = mensagem.strip().lower()
        if resposta in ("sim", "s", "pode", "confirmar", "confirma", "ok", "yes"):
            inicio = datetime.combine(
                date.fromisoformat(dados["data"]),
                datetime.strptime(dados["horario"], "%H:%M").time(),
            )
            # Revalida: outro cliente pode ter reservado durante a conversa.
            erro = _validar_horario(inicio.date(), inicio.time())
            if erro:
                sessao["etapa"] = ETAPA_HORARIO
                return erro
            _salvar_agendamento(
                {
                    "nome": dados["nome"],
                    "numero": numero,
                    "inicio": inicio.isoformat(),
                    "duracao_min": config.DURACAO_REUNIAO_MIN,
                    "criado_em": datetime.now().isoformat(),
                    "lembrete_enviado": False,
                }
            )
            sessao["fluxo"] = None
            sessao["etapa"] = None
            return (
                "✅ *Reunião confirmada!*\n\n"
                f"Te esperamos dia *{inicio:%d/%m/%Y}* às *{inicio:%H:%M}*.\n"
                "Você receberá um lembrete antes da reunião. Até lá! 👋"
            )
        if resposta in ("não", "nao", "n", "no"):
            sessao["etapa"] = ETAPA_DATA
            return "Sem problemas! Vamos ajustar: para qual *dia* você prefere?"
        return "Não entendi. 😅 Responda *sim* para confirmar ou *não* para ajustar."

    # Estado desconhecido: reinicia o fluxo por segurança.
    return iniciar(sessao)
