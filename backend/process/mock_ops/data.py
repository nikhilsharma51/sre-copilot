
_state = {
    "checkout-service": {"restarted": False},
    "payments-worker": {"cleared": False},
}

RECENT_DEPLOY = {
    "checkout-service": {
        "owner": "your-org", "repo": "checkout-service",
        "bad_commit": "a1b2c3d", "deployed_minutes_ago": 22,
    }
}

_CHECKOUT_LOGS_BEFORE = [
    "INFO  deploy a1b2c3d rolled out (connection pool size 20 -> 5)",
    "WARN  connection pool at 92% capacity",
    "ERROR timeout connecting to payments-db (5012ms)",
    "ERROR request failed: 503 Service Unavailable",
    "WARN  connection pool at 100% capacity",
    "ERROR timeout connecting to payments-db (5044ms)",
    "ERROR request failed: 503 Service Unavailable",
]
_CHECKOUT_LOGS_AFTER = [
    "INFO  connection pool reset, 0% capacity",
    "INFO  request completed in 118ms",
    "INFO  healthcheck passed",
]
_CHECKOUT_METRICS_BEFORE = {"error_rate_pct": 23.4, "latency_p99_ms": 4980, "pool_capacity_pct": 98}
_CHECKOUT_METRICS_AFTER = {"error_rate_pct": 0.3, "latency_p99_ms": 112, "pool_capacity_pct": 14}

_WORKER_LOGS_BEFORE = [
    "WARN  disk usage at 94% on /var/log",
    "ERROR failed to write job result: No space left on device",
    "ERROR job queue write failed, retrying",
    "WARN  disk usage at 98% on /var/log",
    "ERROR failed to write job result: No space left on device",
]
_WORKER_LOGS_AFTER = [
    "INFO  old logs purged, disk usage at 41%",
    "INFO  job queue write succeeded",
    "INFO  healthcheck passed",
]
_WORKER_DISK_BEFORE = {"disk_used_pct": 98, "mount": "/var/log", "oldest_log_age_days": 45}
_WORKER_DISK_AFTER = {"disk_used_pct": 41, "mount": "/var/log", "oldest_log_age_days": 2}