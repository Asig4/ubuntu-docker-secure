import asyncio
import logging

from config import ASSETS, DASHBOARDS
from state import state_manager
from ws_manager import ws_manager

logger = logging.getLogger("kiosk.cycle")

_cycle_task: asyncio.Task | None = None


def _get_cycle_items(mode: str) -> list[dict]:
    if mode == "assets":
        return [{"asset": a} for a in ASSETS]
    elif mode == "dashboards":
        return [{"dashboard": d} for d in DASHBOARDS]
    elif mode == "both":
        items = []
        for d in DASHBOARDS:
            for a in ASSETS:
                items.append({"dashboard": d, "asset": a})
        return items
    return []


async def _cycle_loop(stop_event: asyncio.Event):
    logger.info("Auto-cycle started")
    try:
        while not stop_event.is_set():
            state = state_manager.state
            items = _get_cycle_items(state.cycle_mode)
            if not items:
                await asyncio.sleep(1)
                continue

            for item in items:
                if stop_event.is_set():
                    break
                state_manager.update(**item)
                new_state = state_manager.state
                await ws_manager.broadcast({
                    "type": "state_update",
                    "state": new_state.model_dump(),
                    "grafana_url": new_state.grafana_url,
                })
                try:
                    await asyncio.wait_for(
                        stop_event.wait(),
                        timeout=state_manager.state.cycle_interval,
                    )
                    break  # stop_event was set
                except asyncio.TimeoutError:
                    pass  # interval elapsed, continue cycling
    except asyncio.CancelledError:
        pass
    logger.info("Auto-cycle stopped")


def start_cycle():
    global _cycle_task
    stop_cycle()
    event = asyncio.Event()
    _cycle_task = asyncio.create_task(_cycle_loop(event))
    _cycle_task._stop_event = event  # type: ignore[attr-defined]


def stop_cycle():
    global _cycle_task
    if _cycle_task and not _cycle_task.done():
        _cycle_task._stop_event.set()  # type: ignore[attr-defined]
        _cycle_task = None


def is_cycling() -> bool:
    return _cycle_task is not None and not _cycle_task.done()
