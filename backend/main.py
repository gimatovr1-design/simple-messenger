from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import uvicorn
import os

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@app.get("/")
async def root():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))


class ConnectionManager:
    def __init__(self):
        self.active: dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active[websocket] = ""

    def disconnect(self, websocket: WebSocket):
        self.active.pop(websocket, None)

    async def broadcast(self, message: dict):
        for ws in list(self.active):
            try:
                await ws.send_json({
                    "type": "message",
                    "nick": message["nick"],
                    "text": message["text"]
                })
            except:
                self.disconnect(ws)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            text = (await websocket.receive_text()).strip()
            if not text:
                continue

            # установка ника
            if text.startswith("/nick "):
                nick = text.replace("/nick ", "").strip()
                if not nick:
                    await websocket.send_json({
                        "type": "system",
                        "text": "❌ Ник не может быть пустым"
                    })
                    continue

                manager.active[websocket] = nick
                await websocket.send_json({
                    "type": "system",
                    "text": f"✅ Ник установлен: {nick}"
                })
                continue

            nick = manager.active.get(websocket)
            if not nick:
                await websocket.send_json({
                    "type": "system",
                    "text": "❌ Сначала укажи ник через /nick"
                })
                continue

            await manager.broadcast({
                "nick": nick,
                "text": text
            })

    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

