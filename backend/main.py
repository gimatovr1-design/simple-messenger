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

    async def set_nick(self, websocket: WebSocket, nick: str):
        self.active[websocket] = nick
        await self.broadcast({
            "type": "online",
            "nick": nick
        })

    async def disconnect(self, websocket: WebSocket):
        nick = self.active.pop(websocket, None)
        if nick:
            await self.broadcast({
                "type": "offline",
                "nick": nick
            })

    async def broadcast(self, message: dict):
        for ws in list(self.active.keys()):
            try:
                await ws.send_json(message)
            except:
                await self.disconnect(ws)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_text()

            # установка ника
            if data.startswith("/nick "):
                nick = data.replace("/nick ", "").strip()
                await manager.set_nick(websocket, nick)
                continue

            # обычное сообщение
            nick = manager.active.get(websocket)
            if nick:
                await manager.broadcast({
                    "type": "message",
                    "nick": nick,
                    "text": data
                })

    except WebSocketDisconnect:
        await manager.disconnect(websocket)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
