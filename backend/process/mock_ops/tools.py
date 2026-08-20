from datetime import datetime,timedelta,timezone
from . import data

def get_logs(service:str, minutes : int=15) -> list[str]:
    if service != data.SERVICE:
        return [f"no log data for unknown service '{service}'"]

    lines = data._LOGS_AFTER if data._state["restarted"] else data._LOGS_BEFORE

    now = datetime.now(timezone.utc)

    return [
        f"{(now - timedelta(minutes=minutes - i)).isoformat()}Z [{service}] {line}"
        for i,line in enumerate(lines)
    ]


def get_metrics(service: str) -> dict:
    if service != data.SERVICE:
        return {"error": f"no metrics for unknown service '{service}'"}
    return dict(data._METRICS_AFTER if data._state["restarted"] else data._METRICS_BEFORE)

def restart_service(service: str) -> dict:
   
    if service != data.SERVICE:
        return {"status": "error", "detail": f"unknown service '{service}'"}
    data._state["restarted"] = True
    return {"status": "ok", "detail": f"{service} restarted"}