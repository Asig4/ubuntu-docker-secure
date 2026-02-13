import asyncio
import logging
import time
from typing import Callable

import aiohttp

from config import settings
from health import ACTIVE_SOURCES

logger = logging.getLogger("market-feeder.yahoo")

TICKERS = {
    "stocks": ["AAPL", "MSFT", "TSLA"],
    "indices": ["^GSPC", "^IXIC"],
    "forex": ["EURUSD=X", "GBPUSD=X"],
    "commodities": ["GC=F", "CL=F"],
}

ASSET_TYPE_MAP = {
    "stocks": "stock",
    "indices": "index",
    "forex": "forex",
    "commodities": "commodity",
}

SYMBOL_CLEAN = {
    "^GSPC": "SP500",
    "^IXIC": "NASDAQ",
    "EURUSD=X": "EURUSD",
    "GBPUSD=X": "GBPUSD",
    "GC=F": "GOLD",
    "CL=F": "CRUDE_OIL",
}

ALL_TICKERS = []
for tlist in TICKERS.values():
    ALL_TICKERS.extend(tlist)

CHART_API = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}


def _get_asset_type(ticker: str) -> str:
    for category, tlist in TICKERS.items():
        if ticker in tlist:
            return ASSET_TYPE_MAP[category]
    return "unknown"


async def run(write_fn: Callable, stop_event: asyncio.Event):
    """Poll Yahoo Finance every COLLECTION_INTERVAL_REST seconds."""
    if not settings.yahoo_finance_enabled:
        logger.info("Yahoo Finance disabled, skipping")
        return

    interval = settings.collection_interval_rest
    logger.info("Yahoo Finance source started — polling every %ds for %d tickers", interval, len(ALL_TICKERS))
    ACTIVE_SOURCES.inc()

    try:
        while not stop_event.is_set():
            try:
                points = await _fetch_all()
                if points:
                    await write_fn(points, source="yahoo_finance")
                    logger.debug("Wrote %d ticker prices", len(points))
            except Exception:
                logger.exception("Yahoo Finance fetch error")

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval)
                break
            except asyncio.TimeoutError:
                pass
    finally:
        ACTIVE_SOURCES.dec()
        logger.info("Yahoo Finance source stopped")


async def _fetch_all() -> list[dict]:
    """Fetch all tickers via Yahoo Chart API."""
    points = []
    ts = time.time_ns()

    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:
        tasks = [_fetch_ticker(session, ticker) for ticker in ALL_TICKERS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for ticker_str, result in zip(ALL_TICKERS, results):
        if isinstance(result, Exception):
            logger.warning("Failed to fetch %s: %s", ticker_str, result)
            continue
        if result is None:
            continue

        symbol = SYMBOL_CLEAN.get(ticker_str, ticker_str)
        asset_type = _get_asset_type(ticker_str)

        result["tags"] = {
            "symbol": symbol,
            "exchange": "yahoo",
            "asset_type": asset_type,
        }
        result["time"] = ts
        points.append(result)

    return points


async def _fetch_ticker(session: aiohttp.ClientSession, ticker: str) -> dict | None:
    """Fetch a single ticker from Yahoo Chart API."""
    url = CHART_API.format(ticker=ticker)
    params = {"interval": "1d", "range": "2d"}

    async with session.get(url, params=params) as resp:
        if resp.status != 200:
            logger.warning("Yahoo returned %d for %s", resp.status, ticker)
            return None
        data = await resp.json()

    chart = data.get("chart", {}).get("result", [])
    if not chart:
        return None

    result = chart[0]
    meta = result.get("meta", {})
    indicators = result.get("indicators", {}).get("quote", [{}])[0]

    last = meta.get("regularMarketPrice", 0)
    prev_close = meta.get("chartPreviousClose", 0) or meta.get("previousClose", 0)

    if not last or last == 0:
        return None

    change_pct = ((last - prev_close) / prev_close * 100) if prev_close else 0.0

    fields = {
        "last": float(last),
        "change_pct_24h": round(change_pct, 4),
    }

    volume_list = indicators.get("volume", [])
    if volume_list:
        vol = volume_list[-1]
        if vol and vol > 0:
            fields["volume_24h"] = float(vol)

    high_list = indicators.get("high", [])
    low_list = indicators.get("low", [])
    if high_list and high_list[-1]:
        fields["ask"] = float(high_list[-1])
    if low_list and low_list[-1]:
        fields["bid"] = float(low_list[-1])

    return {"measurement": "price", "fields": fields}
