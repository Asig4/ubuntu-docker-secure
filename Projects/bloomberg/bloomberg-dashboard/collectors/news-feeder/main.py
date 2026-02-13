import asyncio
import logging
import signal
import sys

import uvicorn

from config import settings
from health import app as health_app, ARTICLES_DEDUPED
from writers.influxdb_writer import InfluxDBWriter
from sources import cryptopanic, newsapi

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("news-feeder")


class DeduplicatedURLSet:
    """Set with approximate LRU eviction to limit memory usage."""

    def __init__(self, max_size: int = 10000):
        self._max_size = max_size
        self._urls: set[str] = set()
        self._order: list[str] = []

    def __contains__(self, url_hash: str) -> bool:
        return url_hash in self._urls

    def add(self, url_hash: str):
        if url_hash in self._urls:
            return
        self._urls.add(url_hash)
        self._order.append(url_hash)
        # Evict oldest entries when over limit
        while len(self._urls) > self._max_size:
            oldest = self._order.pop(0)
            self._urls.discard(oldest)


async def main():
    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("Shutdown signal received")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _signal_handler)

    writer = InfluxDBWriter()
    seen_urls = DeduplicatedURLSet(max_size=settings.dedup_max_urls)

    # Health/metrics server
    config = uvicorn.Config(
        health_app,
        host="0.0.0.0",
        port=settings.health_port,
        log_level="warning",
    )
    server = uvicorn.Server(config)

    tasks = [
        asyncio.create_task(server.serve(), name="health-server"),
        asyncio.create_task(cryptopanic.run(writer.write_articles, stop_event, seen_urls), name="cryptopanic"),
        asyncio.create_task(newsapi.run(writer.write_articles, stop_event, seen_urls), name="newsapi"),
    ]

    logger.info("News Feeder started — sources: CryptoPanic%s", ", NewsAPI" if settings.newsapi_key else "")

    await stop_event.wait()
    logger.info("Stopping all sources...")

    server.should_exit = True

    done, pending = await asyncio.wait(tasks, timeout=10)
    for t in pending:
        t.cancel()
    if pending:
        await asyncio.wait(pending, timeout=5)

    writer.close()
    logger.info("News Feeder stopped cleanly")


if __name__ == "__main__":
    asyncio.run(main())
