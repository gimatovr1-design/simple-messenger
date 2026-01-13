from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import json
import base64

app = FastAPI()

@app.get("/")
async def root():
    return FileResponse("index.html")


class Manager:
    def __init__(self):
        self.users: dict[WebSocket, str] = {}

    async def connect(self, ws: WebSocket):
        await ws.accept()

    def disconnect(self, ws: WebSocket):
        if ws in self.users:
            del self.users[ws]

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.users:
            try:
                await ws.send_text(json.dumps(data))
            except:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def send_users(self):
        await self.broadcast({
            "type": "users",
            "users": list(self.users.values())
        })


manager = Manager()


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await manager.connect(ws)

    try:
        while True:
            data = json.loads(await ws.receive_text())

            # ===== ник =====
            if data["type"] == "nick":
                manager.users[ws] = data["nick"]
                await manager.send_users()

            # ===== текст =====
            if data["type"] == "message":
                await manager.broadcast({
                    "type": "message",
                    "nick": manager.users.get(ws, "anon"),
                    "text": data["text"]
                })

            # ===== файл =====
            if data["type"] == "file":
                await manager.broadcast({
                    "type": "file",
                    "nick": manager.users.get(ws, "anon"),
                    "name": data["name"],
                    "mime": data["mime"],
                    "content": data["content"]
                })

    except WebSocketDisconnect:
        manager.disconnect(ws)
        await manager.send_users()
