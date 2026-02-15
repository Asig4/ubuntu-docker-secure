import json
import logging

from fastapi import WebSocket

logger = logging.getLogger("kiosk.ws")


class ConnectionManager:
    def __init__(self):
        self._connections: list[WebSocket] = []

    @property
    def count(self) -> int:
        return len(self._connections)

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.append(ws)
        logger.info(f"Display connected ({self.count} total)")

    def disconnect(self, ws: WebSocket):
        if ws in self._connections:
            self._connections.remove(ws)
            logger.info(f"Display disconnected ({self.count} total)")

    async def broadcast(self, message: dict):
        dead = []
        data = json.dumps(message)
        for ws in self._connections:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


ws_manager = ConnectionManager()
