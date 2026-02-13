import asyncio
import hashlib
import logging
import time
from typing import Callable

import aiohttp
import feedparser

from config import settings
from health import ACTIVE_SOURCES

logger = logging.getLogger("news-feeder.cryptopanic")

# Public RSS feed (no token needed)
RSS_URL = "https://cryptopanic.com/news/rss/"

# API endpoint (requires token)
API_URL = "https://cryptopanic.com/api/v1/posts/"

# Known crypto symbols to tag related_asset
CRYPTO_KEYWORDS = {
    "bitcoin": "BTC", "btc": "BTC",
    "ethereum": "ETH", "eth": "ETH",
    "solana": "SOL", "sol": "SOL",
    "bnb": "BNB", "binance": "BNB",
    "xrp": "XRP", "ripple": "XRP",
}


def _detect_asset(title: str) -> str:
    title_lower = title.lower()
    for keyword, symbol in CRYPTO_KEYWORDS.items():
        if keyword in title_lower:
            return symbol
    return "CRYPTO"


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


async def run(write_fn: Callable, stop_event: asyncio.Event, seen_urls: set):
    """Poll CryptoPanic every POLLING_INTERVAL seconds."""
    interval = settings.polling_interval
    use_api = bool(settings.cryptopanic_token)
    mode = "API" if use_api else "RSS"
    logger.info("CryptoPanic source started — mode=%s, polling every %ds", mode, interval)
    ACTIVE_SOURCES.inc()

    try:
        while not stop_event.is_set():
            try:
                if use_api:
                    articles = await _fetch_api(seen_urls)
                else:
                    articles = await _fetch_rss(seen_urls)

                if articles:
                    await write_fn(articles, source="cryptopanic")
                    logger.debug("Wrote %d CryptoPanic articles", len(articles))

            except Exception:
                logger.exception("CryptoPanic fetch error")

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval)
                break
            except asyncio.TimeoutError:
                pass
    finally:
        ACTIVE_SOURCES.dec()
        logger.info("CryptoPanic source stopped")


async def _fetch_rss(seen_urls: set) -> list[dict]:
    """Fetch from public RSS feed (no token needed)."""
    feed = await asyncio.to_thread(feedparser.parse, RSS_URL)
    articles = []
    ts = time.time_ns()

    for entry in feed.entries:
        url = entry.get("link", "")
        url_h = _url_hash(url)
        if url_h in seen_urls:
            continue
        seen_urls.add(url_h)

        title = entry.get("title", "").strip()
        if not title:
            continue

        articles.append({
            "title": title,
            "url": url,
            "source": "cryptopanic",
            "related_asset": _detect_asset(title),
            "published": entry.get("published", ""),
            "time": ts,
        })

    return articles


async def _fetch_api(seen_urls: set) -> list[dict]:
    """Fetch from CryptoPanic API (requires token)."""
    params = {
        "auth_token": settings.cryptopanic_token,
        "kind": "news",
        "filter": "important",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                logger.warning("CryptoPanic API returned %d", resp.status)
                return []
            data = await resp.json()

    articles = []
    ts = time.time_ns()

    for post in data.get("results", []):
        url = post.get("url", "")
        url_h = _url_hash(url)
        if url_h in seen_urls:
            continue
        seen_urls.add(url_h)

        title = post.get("title", "").strip()
        if not title:
            continue

        # Extract related asset from currencies
        related = "CRYPTO"
        currencies = post.get("currencies", [])
        if currencies:
            related = currencies[0].get("code", "CRYPTO")

        articles.append({
            "title": title,
            "url": url,
            "source": "cryptopanic",
            "related_asset": related,
            "published": post.get("published_at", ""),
            "time": ts,
        })

    return articles
