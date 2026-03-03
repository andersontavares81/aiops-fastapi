import imaplib
import email
from email.header import decode_header
from datetime import datetime
from typing import List, Dict

# CONFIGURAÇÃO IMAP – GMAIL
IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993

# COLOQUE SEU E-MAIL GMAIL E SENHA (ou senha de app)
EMAIL_USER = "altavares81@gmail.com"      # seu Gmail
EMAIL_PASS = "nwtwmtqenkbukgka"  # NÃO use senha corporativa aqui

EMAIL_ALERTS: List[Dict] = []


def parse_subject(subject_raw: str) -> Dict:
    severity = "INFO"
    device = "UNKNOWN"
    message = subject_raw

    subj = subject_raw.upper()
    if "CRITICAL" in subj or "CRIT" in subj:
        severity = "CRITICAL"
    elif "WARNING" in subj or "WARN" in subj:
        severity = "WARNING"

    try:
        if "]" in subject_raw:
            after = subject_raw.split("]", 1)[1].strip()
            parts = after.split()
            if parts:
                device = parts[0]
    except Exception:
        pass

    return {"severity": severity, "device": device, "message": message}


def fetch_email_alerts(limit: int = 50) -> List[Dict]:
    alerts: List[Dict] = []

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(EMAIL_USER, EMAIL_PASS)
    except Exception as e:
        print("Erro ao conectar/logar no IMAP:", e)
        return alerts

    status, _ = mail.select("INBOX")
    if status != "OK":
        print("Erro ao selecionar INBOX:", status)
        mail.logout()
        return alerts

    status, data = mail.search(None, "ALL")
    if status != "OK":
        print("Erro ao buscar e-mails:", status)
        mail.close()
        mail.logout()
        return alerts

    mail_ids = data[0].split()
    mail_ids = mail_ids[-limit:]

    for num in reversed(mail_ids):
        status, msg_data = mail.fetch(num, "(RFC822)")
        if status != "OK":
            continue

        msg = email.message_from_bytes(msg_data[0][1])

        subject, encoding = decode_header(msg["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding or "utf-8", errors="ignore")

        parsed = parse_subject(str(subject))

        date_str = msg["Date"]
        try:
            timestamp = (
                datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
                .astimezone()
                .isoformat()
            )
        except Exception:
            timestamp = datetime.utcnow().isoformat() + "Z"

        alerts.append(
            {
                "id": int(num),
                "severity": parsed["severity"],
                "device": parsed["device"],
                "message": parsed["message"],
                "timestamp": timestamp,
                "status": "OPEN",
            }
        )

    mail.close()
    mail.logout()
    return alerts


def refresh_email_alerts(limit: int = 20) -> List[Dict]:
    """Função simples: devolve diretamente a lista de alertas."""
    print("Atualizando alertas a partir do IMAP Gmail...")
    alerts = fetch_email_alerts(limit=limit)
    print(f"Total de alertas lidos: {len(alerts)}")
    return alerts

if __name__ == "__main__":
    print("=== Teste do coletor de e-mails (Gmail) ===")
    alerts = refresh_email_alerts(limit=50)
    from pprint import pprint

    pprint(EMAIL_ALERTS)