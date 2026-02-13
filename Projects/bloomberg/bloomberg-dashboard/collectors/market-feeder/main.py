import asyncio
import logging
import signal
import sys

import uvicorn

from config import settings
from health import app as health_app
from writers.influxdb_writer import InfluxDBWriter
from sources import coingecko, yahoo_finance, binance_ws

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("market-feeder")


async def main():
    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("Shutdown signal received")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _signal_handler)

    writer = InfluxDBWriter()

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
        asyncio.create_task(coingecko.run(writer.write_points, stop_event), name="coingecko"),
        asyncio.create_task(yahoo_finance.run(writer.write_points, stop_event), name="yahoo-finance"),
        asyncio.create_task(binance_ws.run(writer.write_points, stop_event), name="binance-ws"),
    ]

    logger.info("Market Feeder started — sources: CoinGecko, Yahoo Finance, Binance WS (if key set)")

    # Wait for stop signal
    await stop_event.wait()
    logger.info("Stopping all sources...")

    # Shutdown health server
    server.should_exit = True

    # Wait for tasks with timeout
    done, pending = await asyncio.wait(tasks, timeout=10)
    for t in pending:
        t.cancel()
    if pending:
        await asyncio.wait(pending, timeout=5)

    writer.close()
    logger.info("Market Feeder stopped cleanly")


if __name__ == "__main__":
    asyncio.run(main())
