from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Grafana
    grafana_url: str = "http://bloomberg-grafana:3000"

    # Kiosk defaults
    default_dashboard: str = "bloomberg-home"
    default_asset: str = "BTC"
    default_timeframe: str = "1h"
    default_exchange: str = "all"

    # Auto-cycle
    cycle_interval_min: int = 10
    cycle_interval_max: int = 300
    default_cycle_interval: int = 30

    # Server
    host: str = "0.0.0.0"
    port: int = 8001

    # Logging
    log_level: str = "INFO"

    model_config = {"env_prefix": "KIOSK_", "case_sensitive": False}


ASSETS = [
    "BTC", "ETH", "SOL", "BNB", "XRP",
    "AAPL", "MSFT", "TSLA",
    "SP500", "NASDAQ", "EURUSD", "GBPUSD",
    "GOLD", "CRUDE_OIL",
]

TIMEFRAMES = ["5m", "15m", "1h", "4h", "1d"]

EXCHANGES = ["all", "coingecko", "yahoo"]

DASHBOARDS = {
    "bloomberg-home": {"label": "Home", "has_variables": True},
    "bloomberg-deep-dive": {"label": "Deep Dive", "has_variables": True},
    "bloomberg-portfolio": {"label": "Portfolio", "has_variables": False},
    "bloomberg-infra": {"label": "Infra", "has_variables": False},
}

settings = Settings()
