from typing import Dict, Any, List
from datetime import datetime

from fastapi import APIRouter, Depends

from email_collector import refresh_email_alerts

# Se você ainda NÃO usa JWT/autenticação, remova o Depends e o parâmetro current_user.
# Quando tiver get_current_user definido no main.py, você pode importar assim:
# from main import get_current_user

router = APIRouter(
    prefix="/ai",
    tags=["ai"]
)


def build_simple_ai_summary(alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Versão inicial sem IA real.
    Só organiza os dados num formato que o app já pode consumir.
    Depois vamos trocar essa lógica por uma chamada à IA.
    """
    total = len(alerts)
    critical = [a for a in alerts if a.get("severity") == "CRITICAL"]
    warning = [a for a in alerts if a.get("severity") == "WARNING"]

    # “score” simples, só para demo
    risk_score = min(100, len(critical) * 10 + len(warning) * 5)

    top_devices = {}
    for a in alerts:
        dev = a.get("device") or "UNKNOWN"
        top_devices.setdefault(dev, 0)
        top_devices[dev] += 1

    top_devices_list = sorted(
        [{"device": d, "alerts": c} for d, c in top_devices.items()],
        key=lambda x: x["alerts"],
        reverse=True
    )[:5]

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_alerts": total,
        "critical_alerts": len(critical),
        "warning_alerts": len(warning),
        "risk_score": risk_score,
        "top_devices": top_devices_list,
        "recommendation": "Integre aqui com a IA para recomendação real."
    }


@router.get("/analysis")
def ai_analysis(limit: int = 50):
    """
    Endpoint que o app Flutter vai consumir.
    Por enquanto, devolve um resumo “inteligente simples”.
    Depois vamos substituir pela chamada à IA.
    """
    alerts = refresh_email_alerts(limit=limit)
    summary = build_simple_ai_summary(alerts)
    return {
        "alerts": alerts,
        "ai_summary": summary,
    }
