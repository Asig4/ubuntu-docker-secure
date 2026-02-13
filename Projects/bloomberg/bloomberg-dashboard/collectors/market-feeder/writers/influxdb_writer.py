import logging
import time

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from config import settings
from health import WRITES_TOTAL, WRITE_ERRORS, POINTS_WRITTEN, LAST_WRITE

logger = logging.getLogger("market-feeder.writer")


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
        logger.info("InfluxDB writer initialized — bucket=%s", self._bucket)

    async def write_points(self, points: list[dict], source: str = "unknown"):
        """Write a batch of point dicts to InfluxDB."""
        if not points:
            return

        try:
            influx_points = []
            for p in points:
                point = Point(p["measurement"])
                for k, v in p.get("tags", {}).items():
                    point = point.tag(k, v)
                for k, v in p.get("fields", {}).items():
                    point = point.field(k, v)
                if "time" in p:
                    point = point.time(p["time"], WritePrecision.NS)
                influx_points.append(point)

            self._write_api.write(bucket=self._bucket, org=self._org, record=influx_points)

            WRITES_TOTAL.labels(source=source).inc()
            POINTS_WRITTEN.labels(source=source).inc(len(influx_points))
            LAST_WRITE.labels(source=source).set(time.time())

        except Exception:
            WRITE_ERRORS.labels(source=source).inc()
            logger.exception("InfluxDB write error (source=%s, points=%d)", source, len(points))
            raise

    def close(self):
        try:
            self._write_api.close()
            self._client.close()
            logger.info("InfluxDB writer closed")
        except Exception:
            logger.exception("Error closing InfluxDB writer")
