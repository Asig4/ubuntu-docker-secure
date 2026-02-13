import asyncio
import json
import logging
import time
from typing import Callable

import aiohttp

from config import settings
from health import ACTIVE_SOURCES

logger = logging.getLogger("market-feeder.binance_ws")

STREAMS = [
    "btcusdt@ticker",
    "ethusdt@ticker",
    "solusdt@ticker",
    "bnbusdt@ticker",
    "xrpusdt@ticker",
]

WS_URL = "wss://stream.binance.com:9443/ws"

SYMBOL_MAP = {
    "BTCUSDT": "BTC",
    "ETHUSDT": "ETH",
    "SOLUSDT": "SOL",
    "BNBUSDT": "BNB",
    "XRPUSDT": "XRP",
}

MAX_RECONNECT_DELAY = 60


async def run(write_fn: Callable, stop_event: asyncio.Event):
    """Connect to Binance WebSocket for real-time ticker data. Only runs if BINANCE_API_KEY is set."""
    if not settings.binance_api_key:
        logger.info("BINANCE_API_KEY not set — Binance WS source disabled")
        return

    logger.info("Binance WS source starting for %d streams", len(STREAMS))
    ACTIVE_SOURCES.inc()
    reconnect_delay = 1

    try:
        while not stop_event.is_set():
            try:
                combined_url = f"{WS_URL}/{'/'.join(STREAMS)}"
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(combined_url) as ws:
                        logger.info("Binance WS connected")
                        reconnect_delay = 1

                        async for msg in ws:
                            if stop_event.is_set():
                                break

                            if msg.type == aiohttp.WSMsgType.TEXT:
                                try:
                                    data = json.loads(msg.data)
                                    point = _parse_ticker(data)
                                    if point:
                                        await write_fn([point], source="binance_ws")
                                except Exception:
                                    logger.exception("Error parsing Binance message")

                            elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSED):
                                logger.warning("Binance WS closed/error: %s", msg.type)
                                break

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Binance WS connection error")

            if stop_event.is_set():
                break

            logger.info("Reconnecting Binance WS in %ds...", reconnect_delay)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=reconnect_delay)
                break
            except asyncio.TimeoutError:
                pass
            reconnect_delay = min(reconnect_delay * 2, MAX_RECONNECT_DELAY)
    finally:
        ACTIVE_SOURCES.dec()
        logger.info("Binance WS source stopped")


def _parse_ticker(data: dict) -> dict | None:
    """Parse a 24hr ticker event into an InfluxDB point dict."""
    symbol_raw = data.get("s", "")
    symbol = SYMBOL_MAP.get(symbol_raw)
    if not symbol:
        return None

    try:
        return {
            "measurement": "price",
            "tags": {
                "symbol": symbol,
                "exchange": "binance",
                "asset_type": "crypto",
            },
            "fields": {
                "last": float(data.get("c", 0)),
                "bid": float(data.get("b", 0)),
                "ask": float(data.get("a", 0)),
                "volume_24h": float(data.get("v", 0)),
                "change_pct_24h": float(data.get("P", 0)),
            },
            "time": time.time_ns(),
        }
    except (ValueError, TypeError):
        return None
