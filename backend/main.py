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
    try:
        with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


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

        # отправляем историю
        for msg in load_messages():
            if isinstance(msg, dict):
                await websocket.send_text(
                    json.dumps({
                        "type": "message",
                        "nick": msg.get("nick", ""),
                        "text": msg.get("text", "")
                    }, ensure_ascii=False)   # ✅ ВАЖНО
                )

    def disconnect(self, websocket: WebSocket):
        self.active.pop(websocket, None)

    async def broadcast(self, message: dict):
        save_message(message)
        payload = json.dumps({
            "type": "message",
            "nick": message["nick"],
            "text": message["text"]
        }, ensure_ascii=False)               # ✅ ВАЖНО

        for ws in list(self.active):
            try:
                await ws.send_text(payload)
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
                    await websocket.send_text(
                        json.dumps({
                            "type": "system",
                            "text": "❌ Ник не может быть пустым"
                        }, ensure_ascii=False)
                    )
                    continue

                manager.active[websocket] = nick
                await websocket.send_text(
                    json.dumps({
                        "type": "system",
                        "text": f"✅ Ник установлен: {nick}"
                    }, ensure_ascii=False)
                )
                continue

            nick = manager.active.get(websocket)
            if not nick:
                await websocket.send_text(
                    json.dumps({
                        "type": "system",
                        "text": "❌ Сначала укажи ник"
                    }, ensure_ascii=False)
                )
                continue

            await manager.broadcast({
                "nick": nick,
                "text": text
            })

    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
