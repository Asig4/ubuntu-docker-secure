from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # InfluxDB
    influxdb_url: str = "http://bloomberg-influxdb:8086"
    influxdb_token: str = ""
    influxdb_org: str = "bloomberg"
    influxdb_bucket: str = "news"

    # Polling interval (seconds)
    polling_interval: int = 120

    # API keys (optional)
    newsapi_key: str = ""
    cryptopanic_token: str = ""

    # Sentiment
    sentiment_enabled: bool = True

    # Health server
    health_port: int = 8080

    # Dedup
    dedup_max_urls: int = 10000

    # Logging
    log_level: str = "INFO"

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()
