from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import uvicorn

app = FastAPI()

# ===== HTTP =====
@app.get("/")
async def root():
    return FileResponse("index.html")


# ===== Connection Manager =====
class ConnectionManager:
    def __init__(self):
        self.active: dict[WebSocket, str] = {}  # ws -> username

    async def connect(self, ws: WebSocket):
        await ws.accept()

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            del self.active[ws]

    async def broadcast_users(self):
        users = list(self.active.values())
        for ws in self.active:
            await ws.send_json({
                "type": "users",
                "users": users
            })

    async def broadcast_public(self, sender: str, text: str):
        for ws in self.active:
            await ws.send_json({
                "type": "public",
                "from": sender,
                "text": text
            })


manager = ConnectionManager()


# ===== WebSocket =====
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)

    try:
        while True:
            data = await ws.receive_json()

            # ===== LOGIN =====
            if data["type"] == "login":
                username = data["username"]
                manager.active[ws] = username
                await manager.broadcast_users()
                continue

            sender = manager.active.get(ws)
            if not sender:
                continue

            # ===== MESSAGE =====
            if data["type"] == "message":

                # PUBLIC CHAT
                if data["mode"] == "public":
                    await manager.broadcast_public(sender, data["text"])

                # PRIVATE CHAT
                elif data["mode"] == "private":
                    target = data["to"]

                    for w, nick in manager.active.items():
                        if nick == target:
                            await w.send_json({
                                "type": "private",
                                "from": sender,
                                "text": data["text"]
                            })

                    # копия себе
                    await ws.send_json({
                        "type": "private",
                        "from": f"Вы → {target}",
                        "text": data["text"]
                    })

    except WebSocketDisconnect:
        manager.disconnect(ws)
        await manager.broadcast_users()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
