import asyncio
import logging
import time
from typing import Callable

from pycoingecko import CoinGeckoAPI

from config import settings
from health import ACTIVE_SOURCES

logger = logging.getLogger("market-feeder.coingecko")

COIN_IDS = ["bitcoin", "ethereum", "solana", "binancecoin", "ripple"]
COIN_SYMBOLS = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL", "binancecoin": "BNB", "ripple": "XRP"}


async def run(write_fn: Callable, stop_event: asyncio.Event):
    """Poll CoinGecko every COINGECKO_INTERVAL seconds. Single batch call for all coins."""
    cg = CoinGeckoAPI()
    if settings.coingecko_api_key:
        cg = CoinGeckoAPI(api_key=settings.coingecko_api_key)

    interval = settings.coingecko_interval
    logger.info("CoinGecko source started — polling every %ds for %s", interval, list(COIN_SYMBOLS.values()))
    ACTIVE_SOURCES.inc()

    try:
        while not stop_event.is_set():
            try:
                data = await asyncio.to_thread(
                    cg.get_price,
                    ids=",".join(COIN_IDS),
                    vs_currencies="usd",
                    include_24hr_vol=True,
                    include_24hr_change=True,
                    include_market_cap=True,
                )

                points = []
                ts = time.time_ns()

                for coin_id, values in data.items():
                    symbol = COIN_SYMBOLS.get(coin_id, coin_id.upper())
                    points.append({
                        "measurement": "price",
                        "tags": {
                            "symbol": symbol,
                            "exchange": "coingecko",
                            "asset_type": "crypto",
                        },
                        "fields": {
                            "last": float(values.get("usd", 0)),
                            "volume_24h": float(values.get("usd_24h_vol", 0)),
                            "change_pct_24h": float(values.get("usd_24h_change", 0)),
                            "market_cap": float(values.get("usd_market_cap", 0)),
                        },
                        "time": ts,
                    })

                if points:
                    await write_fn(points, source="coingecko")
                    logger.debug("Wrote %d crypto prices", len(points))

            except Exception:
                logger.exception("CoinGecko fetch error")

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval)
                break
            except asyncio.TimeoutError:
                pass
    finally:
        ACTIVE_SOURCES.dec()
        logger.info("CoinGecko source stopped")
