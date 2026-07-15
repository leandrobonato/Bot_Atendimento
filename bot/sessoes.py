"""Gerencia o estado da conversa de cada cliente (por número de WhatsApp).

Em produção, troque o dicionário em memória por Redis ou banco de dados
para suportar múltiplas instâncias da aplicação.
"""

import threading
import time

# Sessões inativas por mais de 30 minutos são descartadas.
TEMPO_EXPIRACAO_SEG = 30 * 60

_sessoes: dict[str, dict] = {}
_trava = threading.Lock()


def obter(numero: str) -> dict:
    """Retorna a sessão do cliente, criando uma nova se necessário."""
    with _trava:
        sessao = _sessoes.get(numero)
        agora = time.time()
        if sessao is None or agora - sessao["ultimo_contato"] > TEMPO_EXPIRACAO_SEG:
            sessao = {"fluxo": None, "etapa": None, "dados": {}, "ultimo_contato": agora}
            _sessoes[numero] = sessao
        sessao["ultimo_contato"] = agora
        return sessao


def limpar(numero: str) -> None:
    """Encerra o fluxo ativo do cliente (ex.: após concluir um agendamento)."""
    with _trava:
        if numero in _sessoes:
            _sessoes[numero] = {
                "fluxo": None,
                "etapa": None,
                "dados": {},
                "ultimo_contato": time.time(),
            }
