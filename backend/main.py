from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import uvicorn
import json
import os

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MESSAGES_FILE = os.path.join(BASE_DIR, "messages.json")


def load_messages():
    if not os.path.exists(MESSAGES_FILE):
        return []
    with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_message(message: dict):
    messages = load_messages()
    messages.append(message)
    with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


@app.get("/")
async def root():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))


class ConnectionManager:
    def __init__(self):
        self.active: dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active[websocket] = ""

        # история
        for msg in load_messages():
            await websocket.send_json({
                "type": "message",
                "nick": msg["nick"],
                "text": msg["text"]
            })

    def disconnect(self, websocket: WebSocket):
        self.active.pop(websocket, None)

    async def broadcast(self, message: dict):
        save_message(message)
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
            data = await websocket.receive_text()
            data = data.strip()

            if not data:
                continue

            # установка ника
            if data.startswith("/nick "):
                nick = data.replace("/nick ", "").strip()
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
                    "text": "❌ Сначала укажи ник"
                })
                continue

            await manager.broadcast({
                "nick": nick,
                "text": data
            })

    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
