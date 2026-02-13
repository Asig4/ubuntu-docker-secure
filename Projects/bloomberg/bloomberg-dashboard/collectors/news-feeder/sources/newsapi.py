import asyncio
import hashlib
import logging
import time
from typing import Callable

import aiohttp

from config import settings
from health import ACTIVE_SOURCES

logger = logging.getLogger("news-feeder.newsapi")

API_URL = "https://newsapi.org/v2/everything"

QUERIES = [
    ("bitcoin OR ethereum OR crypto", "CRYPTO"),
    ("stock market OR S&P 500 OR nasdaq", "STOCKS"),
    ("forex OR dollar OR euro", "FOREX"),
]

ASSET_KEYWORDS = {
    "bitcoin": "BTC", "btc": "BTC",
    "ethereum": "ETH", "eth": "ETH",
    "tesla": "TSLA", "apple": "AAPL", "microsoft": "MSFT",
    "s&p": "SP500", "nasdaq": "NASDAQ",
    "euro": "EURUSD", "dollar": "USD",
    "gold": "GOLD", "oil": "CRUDE_OIL",
}


def _detect_asset(title: str, default: str) -> str:
    title_lower = title.lower()
    for keyword, symbol in ASSET_KEYWORDS.items():
        if keyword in title_lower:
            return symbol
    return default


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


async def run(write_fn: Callable, stop_event: asyncio.Event, seen_urls: set):
    """Poll NewsAPI every POLLING_INTERVAL seconds. Only runs if NEWSAPI_KEY is set."""
    if not settings.newsapi_key:
        logger.info("NEWSAPI_KEY not set — NewsAPI source disabled")
        return

    interval = settings.polling_interval
    logger.info("NewsAPI source started — polling every %ds", interval)
    ACTIVE_SOURCES.inc()

    try:
        while not stop_event.is_set():
            try:
                all_articles = []
                for query, default_asset in QUERIES:
                    articles = await _fetch_query(query, default_asset, seen_urls)
                    all_articles.extend(articles)

                if all_articles:
                    await write_fn(all_articles, source="newsapi")
                    logger.debug("Wrote %d NewsAPI articles", len(all_articles))

            except Exception:
                logger.exception("NewsAPI fetch error")

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval)
                break
            except asyncio.TimeoutError:
                pass
    finally:
        ACTIVE_SOURCES.dec()
        logger.info("NewsAPI source stopped")


async def _fetch_query(query: str, default_asset: str, seen_urls: set) -> list[dict]:
    """Fetch articles for a single query."""
    headers = {"X-Api-Key": settings.newsapi_key}
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 20,
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                logger.warning("NewsAPI returned %d for query '%s'", resp.status, query)
                return []
            data = await resp.json()

    articles = []
    ts = time.time_ns()

    for item in data.get("articles", []):
        url = item.get("url", "")
        url_h = _url_hash(url)
        if url_h in seen_urls:
            continue
        seen_urls.add(url_h)

        title = item.get("title", "").strip()
        if not title or title == "[Removed]":
            continue

        source_name = (item.get("source") or {}).get("name", "unknown")

        articles.append({
            "title": title,
            "url": url,
            "source": source_name,
            "related_asset": _detect_asset(title, default_asset),
            "published": item.get("publishedAt", ""),
            "time": ts,
        })

    return articles
