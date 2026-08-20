"""Seeded fake data for the one alert scenario we're building against:
high error rate on checkout-service, caused by a connection pool that's
maxed out talking to payments-db.
"""

SERVICE="checkout-service"

_state = {"restarted" : False}

_LOGS_BEFORE = [
    "WARN  connection pool at 92% capacity",
    "ERROR timeout connecting to payments-db (5012ms)",
    "ERROR request failed: 503 Service Unavailable",
    "WARN  connection pool at 100% capacity",
    "ERROR timeout connecting to payments-db (5044ms)",
    "ERROR request failed: 503 Service Unavailable",
]
_LOGS_AFTER = [
    "INFO  connection pool reset, 0% capacity",
    "INFO  request completed in 118ms",
    "INFO  healthcheck passed",
]

_METRICS_BEFORE = {
    "error_rate_pct": 23.4,
    "latency_p99_ms": 4980,
    "pool_capacity_pct": 98,
}

_METRICS_AFTER = {
    "error_rate_pct": 0.3,
    "latency_p99_ms": 112,
    "pool_capacity_pct": 14,
}