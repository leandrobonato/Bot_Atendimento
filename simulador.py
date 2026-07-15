"""Simulador de conversa no terminal — teste o bot sem Twilio nem WhatsApp.

Uso:
    python simulador.py
"""

from bot import roteador

NUMERO_TESTE = "whatsapp:+5511999998888"


def main() -> None:
    print("=" * 60)
    print("  Simulador do Bot de Atendimento (digite 'sair' para encerrar)")
    print("=" * 60)
    print()

    while True:
        try:
            mensagem = input("Você: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not mensagem:
            continue
        if mensagem.lower() == "sair":
            break
        resposta = roteador.responder(NUMERO_TESTE, mensagem)
        print(f"\nBot: {resposta}\n")

    print("\nAté logo! 👋")


if __name__ == "__main__":
    main()
