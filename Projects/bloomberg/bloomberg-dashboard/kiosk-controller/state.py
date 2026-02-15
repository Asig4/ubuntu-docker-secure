import time
from urllib.parse import urlencode

from pydantic import BaseModel, Field

from config import settings, DASHBOARDS


class PipState(BaseModel):
    enabled: bool = False
    url: str = ""  # HLS stream URL
    position: str = "bottom-right"  # top-left, top-right, bottom-left, bottom-right
    size: int = 25  # percentage of screen width (10-50)
    opacity: int = 100  # 50-100


class KioskState(BaseModel):
    dashboard: str = Field(default_factory=lambda: settings.default_dashboard)
    asset: str = Field(default_factory=lambda: settings.default_asset)
    timeframe: str = Field(default_factory=lambda: settings.default_timeframe)
    exchange: str = Field(default_factory=lambda: settings.default_exchange)
    cycle_mode: str = "off"  # off, assets, dashboards, both
    cycle_interval: int = Field(default_factory=lambda: settings.default_cycle_interval)
    pip: PipState = Field(default_factory=PipState)
    updated_at: float = Field(default_factory=time.time)

    @property
    def grafana_url(self) -> str:
        """Relative URL for browser iframe (served via nginx on same host)."""
        dash = self.dashboard
        params = {"orgId": "1", "kiosk": "tv", "refresh": "10s"}

        if DASHBOARDS.get(dash, {}).get("has_variables", False):
            params["var-asset"] = self.asset
            params["var-timeframe"] = self.timeframe
            params["var-exchange"] = self.exchange

        return f"/d/{dash}?{urlencode(params)}"


class StateManager:
    def __init__(self):
        self._state = KioskState()

    @property
    def state(self) -> KioskState:
        return self._state

    def update(self, **kwargs) -> KioskState:
        data = self._state.model_dump()
        data.update({k: v for k, v in kwargs.items() if v is not None})
        data["updated_at"] = time.time()
        self._state = KioskState(**data)
        return self._state


state_manager = StateManager()
