import os
import imaplib
import email
from email.header import decode_header
from datetime import datetime
from typing import List, Dict, Any

from dotenv import load_dotenv

# Carrega o .env uma vez ao importar o módulo
load_dotenv()

IMAP_HOST = os.getenv("IMAP_HOST")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
IMAP_USER = os.getenv("IMAP_USER")
IMAP_PASS = os.getenv("IMAP_PASS")
IMAP_FOLDER = os.getenv("IMAP_FOLDER", "INBOX")


def _check_imap_config():
    """Garante que as variáveis de ambiente foram configuradas."""
    if not IMAP_HOST or not IMAP_USER or not IMAP_PASS:
        raise RuntimeError(
            "Variáveis de ambiente IMAP não configuradas. "
            "Verifique IMAP_HOST, IMAP_USER e IMAP_PASS no arquivo .env."
        )


def _connect_imap() -> imaplib.IMAP4_SSL:
    """Conecta ao servidor IMAP usando as credenciais do .env."""
    _check_imap_config()
    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    mail.login(IMAP_USER, IMAP_PASS)
    return mail


def _parse_email_message(msg) -> Dict[str, Any]:
    """
    Converte um e‑mail em um dicionário de alerta.
    Adapte esta função ao formato real dos e‑mails que você recebe.
    """
    subject, encoding = decode_header(msg.get("Subject"))[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding or "utf-8", errors="ignore")

    from_ = msg.get("From")
    date_ = msg.get("Date")

    # Exemplo de mapeamento simples – ajuste para o seu caso
    alert = {
        "id": f"{date_}-{from_}",   # pode ser outro identificador
        "title": subject,
        "source": from_,
        "severity": "INFO",         # você pode parsear a severidade do subject/body
        "timestamp": date_ or datetime.utcnow().isoformat(),
    }
    return alert


def refresh_email_alerts(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Lê os últimos 'limit' e‑mails da pasta IMAP_FOLDER e devolve como lista de alerts.
    Esta é a função que o seu main.py provavelmente já usa.
    """
    _check_imap_config()
    alerts: List[Dict[str, Any]] = []

    mail = _connect_imap()
    try:
        # Seleciona a pasta (INBOX, ou outra que você configure no .env)
        mail.select(IMAP_FOLDER)

        # Busca todos os e‑mails
        status, data = mail.search(None, "ALL")
        if status != "OK":
            return []

        # Pega os últimos 'limit' IDs
        mail_ids = data[0].split()
        mail_ids = mail_ids[-limit:] if limit > 0 else mail_ids

        for mail_id in reversed(mail_ids):  # mais recentes primeiro
            status, msg_data = mail.fetch(mail_id, "(RFC822)")
            if status != "OK":
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            alert = _parse_email_message(msg)
            alerts.append(alert)

    finally:
        try:
            mail.close()
        except Exception:
            pass
        mail.logout()

    return alerts
