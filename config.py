"""Configurações centralizadas da aplicação, carregadas de variáveis de ambiente."""

import os
from datetime import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# --- Twilio ---
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

# --- Aplicação ---
PORT = int(os.getenv("PORT", "5000"))
DEBUG = os.getenv("FLASK_ENV", "production") == "development"
NOME_EMPRESA = os.getenv("NOME_EMPRESA", "Minha Empresa")

# --- Agendamento ---
def _parse_hora(valor: str, padrao: time) -> time:
    try:
        hora, minuto = valor.split(":")
        return time(int(hora), int(minuto))
    except (ValueError, AttributeError):
        return padrao


HORARIO_ABERTURA = _parse_hora(os.getenv("HORARIO_ABERTURA", "09:00"), time(9, 0))
HORARIO_FECHAMENTO = _parse_hora(os.getenv("HORARIO_FECHAMENTO", "18:00"), time(18, 0))
DURACAO_REUNIAO_MIN = int(os.getenv("DURACAO_REUNIAO_MIN", "60"))

# --- Lembretes (pywhatkit) ---
LEMBRETES_ATIVOS = os.getenv("LEMBRETES_ATIVOS", "false").lower() == "true"
LEMBRETE_ANTECEDENCIA_MIN = int(os.getenv("LEMBRETE_ANTECEDENCIA_MIN", "30"))

# --- Arquivos de dados ---
ARQUIVO_FAQ = DATA_DIR / "faq.json"
ARQUIVO_AGENDAMENTOS = DATA_DIR / "agendamentos.json"
