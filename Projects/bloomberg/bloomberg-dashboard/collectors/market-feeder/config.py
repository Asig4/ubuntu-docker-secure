from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # InfluxDB
    influxdb_url: str = "http://bloomberg-influxdb:8086"
    influxdb_token: str = ""
    influxdb_org: str = "bloomberg"
    influxdb_bucket: str = "markets"

    # Collection intervals (seconds)
    collection_interval_rest: int = 15
    coingecko_interval: int = 60

    # API keys (optional)
    binance_api_key: str = ""
    binance_secret: str = ""
    coingecko_api_key: str = ""

    # Yahoo Finance
    yahoo_finance_enabled: bool = True

    # Health server
    health_port: int = 8080

    # Logging
    log_level: str = "INFO"

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()
