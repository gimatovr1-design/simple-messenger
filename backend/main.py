from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import json
from pathlib import Path

app = FastAPI()

ADMIN_NICK = "руслан"
MESSAGES_FILE = Path("messages.json")


@app.get("/")
async def root():
    return FileResponse("index.html")


class ConnectionManager:
    def __init__(self):
        self.active = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()

    def disconnect(self, websocket: WebSocket):
        self.active.pop(websocket, None)

    async def broadcast(self, message: str):
        for ws in list(self.active.keys()):
            try:
                await ws.send_text(message)
            except:
                self.disconnect(ws)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    nickname = "Гость"

    try:
        while True:
            text = await websocket.receive_text()
            data = json.loads(text)

            # смена ника
            if data["type"] == "nick":
                nickname = data["nick"]
                manager.active[websocket] = nickname
                continue

            # очистка чата (ТОЛЬКО руслан)
            if data["type"] == "clear_chat":
                if nickname == ADMIN_NICK:
                    MESSAGES_FILE.write_text("[]", encoding="utf-8")
                    await manager.broadcast(json.dumps({
                        "type": "system",
                        "message": "🧹 Чат очищен администратором"
                    }, ensure_ascii=False))
                continue

            # обычное сообщение
            if data["type"] == "message":
                msg = {
                    "type": "message",
                    "nick": nickname,
                    "text": data["text"]
                }

                messages = json.loads(MESSAGES_FILE.read_text(encoding="utf-8"))
                messages.append(msg)
                MESSAGES_FILE.write_text(
                    json.dumps(messages, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )

                await manager.broadcast(json.dumps(msg, ensure_ascii=False))

    except WebSocketDisconnect:
        manager.disconnect(websocket)
