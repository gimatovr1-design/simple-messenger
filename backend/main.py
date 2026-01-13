from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

app = FastAPI()


@app.get("/")
async def root():
    return FileResponse("index.html")


class ConnectionManager:
    def __init__(self):
        self.active = {}

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

            if data.startswith("/nick "):
                nick = data.replace("/nick ", "").strip()
                manager.active[websocket] = nick
                continue

            nick = manager.active.get(websocket)
            if not nick:
                continue

            await manager.broadcast(f"{nick}:{data}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
