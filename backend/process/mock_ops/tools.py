from datetime import datetime,timedelta,timezone
from . import data

def _timestamped(lines,minutes) :
    now = datetime.now(timezone.utc)
    return [
        f"{(now - timedelta(minutes=minutes - i)).isoformat()}Z {line}"
        for i, line in enumerate(lines)
    ]

def get_logs(service:str, minutes : int=15) -> list[str]:
    """Return recent log lines for `service`."""
    if service == "checkout-service":
        lines = data._CHECKOUT_LOGS_AFTER if data._state[service]["restarted"] else data._CHECKOUT_LOGS_BEFORE
    elif service == "payments-worker":
        lines = data._WORKER_LOGS_AFTER if data._state[service]["cleared"] else data._WORKER_LOGS_BEFORE
    else:
        return [f"no log data for unknown service '{service}'"]
    return _timestamped([f"[{service}] {l}" for l in lines], minutes)


def get_metrics(service: str) -> dict:
    """Return error-rate/latency metrics -- only checkout-service tracks these."""
    if service == "checkout-service":
        return dict(data._CHECKOUT_METRICS_AFTER if data._state[service]["restarted"] else data._CHECKOUT_METRICS_BEFORE)
    return {"error": f"no error-rate/latency metrics tracked for '{service}'"}

def get_disk_usage(service: str) -> dict:
    """Return disk usage -- only payments-worker tracks this."""
    if service == "payments-worker":
        return dict(data._WORKER_DISK_AFTER if data._state[service]["cleared"] else data._WORKER_DISK_BEFORE)
    return {"error": f"no disk usage tracked for '{service}'"}

def restart_service(service: str) -> dict:
    """Restart a service. No approval gate here -- that's enforced upstream."""
    if service != "checkout-service":
        return {"status": "error", "detail": f"restart_service isn't the right fix for '{service}'"}
    data._state[service]["restarted"] = True
    return {"status": "ok", "detail": f"{service} restarted"}

def clear_old_logs(service: str) -> dict:
    """Purge old logs to free disk space."""
    if service != "payments-worker":
        return {"status": "error", "detail": f"clear_old_logs isn't the right fix for '{service}'"}
    data._state[service]["cleared"] = True
    return {"status": "ok", "detail": f"old logs cleared on {service}"}