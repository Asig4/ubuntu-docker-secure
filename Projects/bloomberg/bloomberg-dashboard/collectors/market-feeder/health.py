import time

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from prometheus_client import (
    Counter,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

app = FastAPI(title="Market Feeder Health")

# --- Prometheus metrics ---
WRITES_TOTAL = Counter("market_feeder_writes_total", "Total InfluxDB writes", ["source"])
WRITE_ERRORS = Counter("market_feeder_write_errors_total", "Total write errors", ["source"])
POINTS_WRITTEN = Counter("market_feeder_points_written_total", "Total data points written", ["source"])
ACTIVE_SOURCES = Gauge("market_feeder_active_sources", "Number of active data sources")
UPTIME = Gauge("market_feeder_uptime_seconds", "Feeder uptime in seconds")
LAST_WRITE = Gauge("market_feeder_last_write_timestamp", "Last successful write timestamp", ["source"])

_start_time = time.time()


@app.get("/health")
def health():
    UPTIME.set(time.time() - _start_time)
    return {
        "status": "healthy",
        "service": "market-feeder",
        "uptime_seconds": round(time.time() - _start_time, 1),
    }


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    UPTIME.set(time.time() - _start_time)
    return PlainTextResponse(
        content=generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )
