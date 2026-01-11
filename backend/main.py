from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import uvicorn

app = FastAPI()

@app.get("/")
async def root():
    return FileResponse("index.html")


class ConnectionManager:
    def __init__(self):
        self.active: dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active[websocket] = ""

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active:
            del self.active[websocket]

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

            # команда смены ника
            if data.startswith("/nick "):
                nick = data.replace("/nick ", "").strip()
                manager.active[websocket] = nick
                await websocket.send_text(f"🔧 Ник установлен: {nick}")
                continue

            nick = manager.active.get(websocket, "")
            if not nick:
                await websocket.send_text("❌ Сначала укажи ник")
                continue

            await manager.broadcast(f"{nick}: {data}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
