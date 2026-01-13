from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import os

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@app.get("/")
async def root():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))


class ConnectionManager:
    def __init__(self):
        self.active = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active[websocket] = ""

    def disconnect(self, websocket: WebSocket):
        self.active.pop(websocket, None)

    async def broadcast(self, message: str):
        for ws in list(self.active):
            try:
                await ws.send_text(message)
            except:
                self.disconnect(ws)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            data = data.strip()

            if not data:
                continue

            if data.startswith("/nick "):
                nick = data.replace("/nick ", "").strip()
                if not nick:
                    await websocket.send_text("❌ Ник пустой")
                    continue
                manager.active[websocket] = nick
                await websocket.send_text(f"Ник установлен: {nick}")
                continue

            nick = manager.active.get(websocket)
            if not nick:
                await websocket.send_text("❌ Сначала укажи ник")
                continue

            await manager.broadcast(f"{nick}: {data}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)

