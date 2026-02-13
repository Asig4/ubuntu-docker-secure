import time

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from prometheus_client import (
    Counter,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

app = FastAPI(title="News Feeder Health")

# --- Prometheus metrics ---
WRITES_TOTAL = Counter("news_feeder_writes_total", "Total InfluxDB writes", ["source"])
WRITE_ERRORS = Counter("news_feeder_write_errors_total", "Total write errors", ["source"])
ARTICLES_WRITTEN = Counter("news_feeder_articles_written_total", "Total articles written", ["source"])
ARTICLES_DEDUPED = Counter("news_feeder_articles_deduped_total", "Total articles skipped (dedup)", ["source"])
ACTIVE_SOURCES = Gauge("news_feeder_active_sources", "Number of active news sources")
UPTIME = Gauge("news_feeder_uptime_seconds", "Feeder uptime in seconds")
LAST_WRITE = Gauge("news_feeder_last_write_timestamp", "Last successful write timestamp", ["source"])

_start_time = time.time()


@app.get("/health")
def health():
    UPTIME.set(time.time() - _start_time)
    return {
        "status": "healthy",
        "service": "news-feeder",
        "uptime_seconds": round(time.time() - _start_time, 1),
    }


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    UPTIME.set(time.time() - _start_time)
    return PlainTextResponse(
        content=generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )
