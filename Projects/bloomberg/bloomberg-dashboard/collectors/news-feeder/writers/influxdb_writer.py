import logging
import time

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from config import settings
from health import WRITES_TOTAL, WRITE_ERRORS, ARTICLES_WRITTEN, ARTICLES_DEDUPED, LAST_WRITE

logger = logging.getLogger("news-feeder.writer")


class InfluxDBWriter:
    def __init__(self):
        self._client = InfluxDBClient(
            url=settings.influxdb_url,
            token=settings.influxdb_token,
            org=settings.influxdb_org,
        )
        self._write_api = self._client.write_api(write_options=SYNCHRONOUS)
        self._bucket = settings.influxdb_bucket
        self._org = settings.influxdb_org

        self._analyzer = None
        if settings.sentiment_enabled:
            self._analyzer = SentimentIntensityAnalyzer()
            logger.info("VADER sentiment analyzer enabled")

        logger.info("InfluxDB writer initialized — bucket=%s", self._bucket)

    def _analyze_sentiment(self, text: str) -> tuple[float, str]:
        """Return (compound_score, label) using VADER."""
        if not self._analyzer:
            return 0.0, "neutral"

        scores = self._analyzer.polarity_scores(text)
        compound = scores["compound"]

        if compound >= 0.05:
            label = "positive"
        elif compound <= -0.05:
            label = "negative"
        else:
            label = "neutral"

        return round(compound, 4), label

    async def write_articles(self, articles: list[dict], source: str = "unknown"):
        """Write articles to InfluxDB with sentiment analysis."""
        if not articles:
            return

        try:
            influx_points = []
            for article in articles:
                title = article.get("title", "")
                score, label = self._analyze_sentiment(title)

                point = (
                    Point("article")
                    .tag("source", article.get("source", source))
                    .tag("sentiment_label", label)
                    .tag("related_asset", article.get("related_asset", "UNKNOWN"))
                    .field("title", title)
                    .field("url", article.get("url", ""))
                    .field("score", score)
                )

                if "time" in article:
                    point = point.time(article["time"], WritePrecision.NS)

                influx_points.append(point)

            self._write_api.write(bucket=self._bucket, org=self._org, record=influx_points)

            WRITES_TOTAL.labels(source=source).inc()
            ARTICLES_WRITTEN.labels(source=source).inc(len(influx_points))
            LAST_WRITE.labels(source=source).set(time.time())

            logger.debug("Wrote %d articles (source=%s)", len(influx_points), source)

        except Exception:
            WRITE_ERRORS.labels(source=source).inc()
            logger.exception("InfluxDB write error (source=%s, articles=%d)", source, len(articles))
            raise

    def close(self):
        try:
            self._write_api.close()
            self._client.close()
            logger.info("InfluxDB writer closed")
        except Exception:
            logger.exception("Error closing InfluxDB writer")
