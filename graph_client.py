"""
graph_client.py
----------------
Integra FastAPI com o Microsoft Graph para ler e-mails de alerta
da sua conta corporativa (America Tecnologia) usando OAuth2
(Autenticação Moderna).

ANTES DE FUNCIONAR, É OBRIGATÓRIO:

1) Registrar uma aplicação no Azure AD (feito pelo TI ou por você, se tiver permissão):

   - Acessar portal.azure.com
   - Azure Active Directory > App registrations > New registration
   - Nome: por ex. "NOC Alerts Reader"
   - Supported account types: "Accounts in this organizational directory only"
   - Após criar, anotar:
       * Directory (tenant) ID         -> AZ_TENANT_ID
       * Application (client) ID       -> AZ_CLIENT_ID

2) Criar um CLIENT SECRET:
   - Na app registrada: Certificates & secrets > New client secret
   - Anotar o "Value" gerado          -> AZ_CLIENT_SECRET

3) Dar permissões de acesso ao e-mail:
   - Na app: API permissions > Add a permission
   - Microsoft Graph > Application permissions
   - Marcar: Mail.Read
   - Clicar em "Grant admin consent" (precisa de administrador do tenant)

4) No servidor/PC onde o FastAPI roda, definir estas variáveis de ambiente:

   No PowerShell:

     $env:AZ_TENANT_ID     = "GUID_DO_TENANT"
     $env:AZ_CLIENT_ID     = "GUID_DO_CLIENT"
     $env:AZ_CLIENT_SECRET = "SEGREDO_DA_APP"
     $env:AZ_USER_ID       = "anderson.lima@americatecnologia.com.br"

   (ou configurar em um arquivo .env e carregar com python-dotenv, se quiser)

Depois disso, o código abaixo consegue:

   - Obter um token OAuth2 (client credentials)
   - Ler mensagens de e-mail da pasta Inbox do usuário
   - Converter em uma lista de "alertas" para o FastAPI expor em /alerts.
"""

import os
from typing import List, Dict

import msal
import requests

# ===========================
# CONFIGURAÇÕES (preencher)
# ===========================

# Estes valores DEVEM vir do Azure AD / App Registration
TENANT_ID = os.environ.get("AZ_TENANT_ID", "AWQAm/8bAAAAPDFzLfyWgMN6MI+w/5ZFqwcaPqtXldIdUamsdsBreWlqwk+iZD0+dGbgbihUUjrXTDrbodDcMkw7/miAFxfJAnzoR72l/QCizVoiinzw3/vjF0x7h8RK4kzajLuwCuI6")
CLIENT_ID = os.environ.get("AZ_CLIENT_ID", "de8bc8b5-d9f9-48b1-a8ad-b748da725064")
CLIENT_SECRET = os.environ.get("AZ_CLIENT_SECRET", "0")

# Usuário cujo mailbox será lido (o seu e-mail corporativo)
USER_ID = os.environ.get(
    "AZ_USER_ID",
    "anderson.lima@americatecnologia.com.br",
)

# Authority e escopos do Microsoft Graph
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]
GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _get_access_token() -> str:
    """
    Obtém um access_token OAuth2 usando o fluxo de client credentials.
    Não envolve digitar usuário/senha; usa CLIENT_ID + CLIENT_SECRET.
    """
    if "1822a948-a93d-4f58-8515-9b94a3f89105" in TENANT_ID:
        raise RuntimeError("Configure TENANT_ID (AZ_TENANT_ID) antes de usar o Graph.")
    if "de8bc8b5-d9f9-48b1-a8ad-b748da725064" in CLIENT_ID:
        raise RuntimeError("Configure CLIENT_ID (AZ_CLIENT_ID) antes de usar o Graph.")
    if "0" in CLIENT_SECRET:
        raise RuntimeError("Configure CLIENT_SECRET (AZ_CLIENT_SECRET) antes de usar o Graph.")

    app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
    )

    # Tenta cache em memória primeiro
    result = app.acquire_token_silent(SCOPE, account=None)
    if not result:
        # Fluxo client_credentials (aplicação server-to-server)
        result = app.acquire_token_for_client(scopes=SCOPE)

    if "access_token" not in result:
        raise RuntimeError(f"Erro ao obter token OAuth2: {result}")

    return result["access_token"]


def fetch_mail_alerts(limit: int = 20) -> List[Dict]:
    """
    Lê os últimos 'limit' e-mails da INBOX via Microsoft Graph
    e converte em uma lista de dicts de alerta.
    """
    token = _get_access_token()

    url = f"{GRAPH_BASE}/users/{USER_ID}/mailFolders/Inbox/messages"

    params = {
        "$top": limit,
        "$select": "subject,from,receivedDateTime",
        "$orderby": "receivedDateTime desc",
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()

    data = resp.json()
    messages = data.get("value", [])

    alerts: List[Dict] = []

    for msg in messages:
        subject = msg.get("subject", "") or ""
        received = msg.get("receivedDateTime", "") or ""
        sender = (
            msg.get("from", {})
            .get("emailAddress", {})
            .get("address", "")
            or ""
        )

        # Parser simples de severidade baseado no assunto
        subj_upper = subject.upper()
        severity = "INFO"
        if "CRITICAL" in subj_upper or "CRIT" in subj_upper:
            severity = "CRITICAL"
        elif "WARNING" in subj_upper or "WARN" in subj_upper:
            severity = "WARNING"

        alerts.append(
            {
                "id": hash(subject + received + sender),
                "severity": severity,
                "device": "UNKNOWN",  # se quiser, podemos extrair do subject depois
                "message": subject,
                "timestamp": received,
                "status": "OPEN",
            }
        )

    return alerts


if __name__ == "__main__":
    # Teste rápido no terminal
    print("=== Teste de leitura de e-mails via Microsoft Graph ===")
    try:
        result = fetch_mail_alerts(limit=5)
        from pprint import pprint

        pprint(result)
    except Exception as e:
        print("ERRO AO LER E-MAILS VIA GRAPH:", e)