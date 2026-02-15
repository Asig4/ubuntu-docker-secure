import logging
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from config import settings, ASSETS, TIMEFRAMES, EXCHANGES, DASHBOARDS
from state import state_manager
from ws_manager import ws_manager
from cycle import start_cycle, stop_cycle, is_cycling

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("kiosk")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Kiosk Controller started on port {settings.port}")
    yield
    stop_cycle()
    logger.info("Kiosk Controller stopped")


app = FastAPI(title="Bloomberg Kiosk Controller", lifespan=lifespan)
templates = Jinja2Templates(directory="templates")


# --- Health ---

@app.get("/kiosk/health")
async def health():
    return {
        "status": "healthy",
        "displays": ws_manager.count,
        "cycling": is_cycling(),
    }


# --- HTML Pages ---

@app.get("/kiosk/display", response_class=HTMLResponse)
async def display_page(request: Request):
    state = state_manager.state
    return templates.TemplateResponse("display.html", {
        "request": request,
        "grafana_url": state.grafana_url,
    })


@app.get("/kiosk/control", response_class=HTMLResponse)
async def control_page(request: Request):
    state = state_manager.state
    return templates.TemplateResponse("control.html", {
        "request": request,
        "state": state.model_dump(),
        "assets": ASSETS,
        "timeframes": TIMEFRAMES,
        "exchanges": EXCHANGES,
        "dashboards": DASHBOARDS,
    })


# --- REST API ---

@app.get("/kiosk/api/state")
async def get_state():
    state = state_manager.state
    return {
        **state.model_dump(),
        "grafana_url": state.grafana_url,
        "displays": ws_manager.count,
        "cycling": is_cycling(),
    }


class StateUpdate(BaseModel):
    dashboard: Optional[str] = None
    asset: Optional[str] = None
    timeframe: Optional[str] = None
    exchange: Optional[str] = None


@app.put("/kiosk/api/state")
async def update_state(update: StateUpdate):
    new_state = state_manager.update(**update.model_dump(exclude_none=True))
    msg = {
        "type": "state_update",
        "state": new_state.model_dump(),
        "grafana_url": new_state.grafana_url,
    }
    await ws_manager.broadcast(msg)
    return {**new_state.model_dump(), "grafana_url": new_state.grafana_url}


class CycleUpdate(BaseModel):
    mode: str = "off"  # off, assets, dashboards, both
    interval: Optional[int] = None


@app.post("/kiosk/api/cycle")
async def toggle_cycle(update: CycleUpdate):
    if update.interval is not None:
        interval = max(settings.cycle_interval_min, min(update.interval, settings.cycle_interval_max))
        state_manager.update(cycle_interval=interval)

    state_manager.update(cycle_mode=update.mode)

    if update.mode == "off":
        stop_cycle()
    else:
        start_cycle()

    state = state_manager.state
    await ws_manager.broadcast({
        "type": "cycle_update",
        "state": state.model_dump(),
        "grafana_url": state.grafana_url,
    })
    return {"cycling": is_cycling(), "mode": update.mode, "interval": state.cycle_interval}


class PipUpdate(BaseModel):
    enabled: Optional[bool] = None
    url: Optional[str] = None
    position: Optional[str] = None  # top-left, top-right, bottom-left, bottom-right
    size: Optional[int] = None  # 10-50 (% of screen width)
    opacity: Optional[int] = None  # 50-100


@app.put("/kiosk/api/pip")
async def update_pip(update: PipUpdate):
    pip_data = state_manager.state.pip.model_dump()
    pip_data.update({k: v for k, v in update.model_dump().items() if v is not None})
    if pip_data.get("size") is not None:
        pip_data["size"] = max(10, min(50, pip_data["size"]))
    if pip_data.get("opacity") is not None:
        pip_data["opacity"] = max(50, min(100, pip_data["opacity"]))
    state_manager.update(pip=pip_data)
    state = state_manager.state
    await ws_manager.broadcast({
        "type": "pip_update",
        "pip": state.pip.model_dump(),
    })
    return state.pip.model_dump()


@app.get("/kiosk/api/options")
async def get_options():
    return {
        "assets": ASSETS,
        "timeframes": TIMEFRAMES,
        "exchanges": EXCHANGES,
        "dashboards": {k: v["label"] for k, v in DASHBOARDS.items()},
    }


# --- WebSocket ---

@app.websocket("/kiosk/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    # Send current state on connect
    state = state_manager.state
    try:
        await ws.send_text(__import__("json").dumps({
            "type": "init",
            "state": state.model_dump(),
            "grafana_url": state.grafana_url,
            "pip": state.pip.model_dump(),
        }))
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
    except Exception:
        ws_manager.disconnect(ws)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port, log_level="warning")
