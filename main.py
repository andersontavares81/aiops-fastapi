from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import List, Dict, Any

from email_collector import refresh_email_alerts

app = FastAPI()

# CORS - liberado geral em DEV. Depois você pode restringir.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # em produção, ideal é especificar o domínio do app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def build_dashboard(alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calcula os cards do dashboard com base nos alerts reais.
    Você pode ir refinando essa lógica depois.
    """
    total_alerts = len(alerts)
    critical = sum(1 for a in alerts if a.get("severity") == "CRITICAL")
    warning = sum(1 for a in alerts if a.get("severity") == "WARNING")
    info = sum(1 for a in alerts if a.get("severity") == "INFO")

    # Devices únicos (ignorando UNKNOWN)
    devices = {
        a.get("device")
        for a in alerts
        if a.get("device") and a.get("device") != "UNKNOWN"
    }
    nodes_active = len(devices) if devices else 1  # evita zero para MVP

    # Valores “fakes” mas coerentes, derivados da quantidade de alerts
    sla = max(95.0, 100.0 - critical * 0.5 - warning * 0.2)
    lambda_invocations = total_alerts * 17  # só para dar um número “vivo”
    cpu_avg = 50 + min(total_alerts, 50) // 2
    mem_avg = 45 + min(total_alerts, 40) // 2
    snmp_events_24h = total_alerts * 23

    return {
        "nodes_active": nodes_active,
        "critical": critical,
        "warning": warning,
        "info": info,
        "alerts": total_alerts,
        "sla": round(sla, 2),
        "lambda_invocations_hour": lambda_invocations,
        "cpu_avg": min(cpu_avg, 95),
        "mem_avg": min(mem_avg, 95),
        "snmp_events_24h": snmp_events_24h,
        "last_update": datetime.utcnow().isoformat() + "Z",
    }


def build_nodes(alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Gera uma lista de nós com base nos devices dos alerts.
    Como muitos alerts estão com device = UNKNOWN,
    vamos agrupar tudo em "generic nodes" só para ilustrar.
    Se futuramente você ajustar o parser para extrair host real,
    isso fica automaticamente mais rico.
    """
    nodes: List[Dict[str, Any]] = []

    # Agrupa por device
    by_device: Dict[str, List[Dict[str, Any]]] = {}
    for a in alerts:
        dev = a.get("device") or "UNKNOWN"
        by_device.setdefault(dev, []).append(a)

    for device, dev_alerts in by_device.items():
        total = len(dev_alerts)
        critical = sum(1 for a in dev_alerts if a.get("severity") == "CRITICAL")
        warning = sum(1 for a in dev_alerts if a.get("severity") == "WARNING")
        info = sum(1 for a in dev_alerts if a.get("severity") == "INFO")

        status = "OK"
        if critical > 0:
            status = "CRIT"
        elif warning > 0:
            status = "WARN"

        # Exemplos de métricas aleatórias só para dar “vida”
        cpu = min(40 + critical * 10 + warning * 5, 97)
        temp = min(30 + critical * 5 + warning * 3, 90)

        last_event = dev_alerts[0].get("message", "")[:80]

        nodes.append(
            {
                "manufacturer": "GENERIC",
                "host": device,
                "model": "VirtualNode",
                "status": status,
                "cpu": cpu,
                "temp": temp,
                "uptime": "N/A",
                "last_event": last_event,
                "alerts_total": total,
                "alerts_critical": critical,
                "alerts_warning": warning,
                "alerts_info": info,
            }
        )

    # Ordena por criticidade
    nodes.sort(
        key=lambda n: (n["alerts_critical"], n["alerts_warning"], n["alerts_total"]),
        reverse=True,
    )
    return nodes


@app.get("/dashboard")
def get_dashboard():
    alerts = refresh_email_alerts(limit=50)
    dashboard = build_dashboard(alerts)
    return dashboard


@app.get("/nodes")
def get_nodes():
    alerts = refresh_email_alerts(limit=50)
    nodes = build_nodes(alerts)
    return nodes


@app.get("/alerts")
def get_alerts():
    alerts = refresh_email_alerts(limit=50)
    return alerts