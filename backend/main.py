from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import uvicorn
import json
import os

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MESSAGES_FILE = os.path.join(BASE_DIR, "messages.json")


# ====== история ======
def load_messages():
    if not os.path.exists(MESSAGES_FILE):
        return []
    try:
        with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_message(msg: dict):
    messages = load_messages()
    messages.append(msg)
    with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


@app.get("/")
async def root():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))


# ====== WS MANAGER ======
class ConnectionManager:
    def __init__(self):
        self.active: dict[WebSocket, str] = {}

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active[ws] = ""

        # отправляем историю
        for msg in load_messages():
            await ws.send_json({
                "type": "message",
                "nick": msg["nick"],
                "text": msg["text"]
            })

    async def disconnect(self, ws: WebSocket):
        nick = self.active.get(ws)
        self.active.pop(ws, None)

        if nick:
            await self.broadcast_system(f"{nick} вышел")

    async def broadcast_message(self, nick: str, text: str):
        save_message({"nick": nick, "text": text})
        for ws in list(self.active):
            try:
                await ws.send_json({
                    "type": "message",
                    "nick": nick,
                    "text": text
                })
            except:
                self.active.pop(ws, None)

    async def broadcast_system(self, text: str):
        for ws in list(self.active):
            try:
                await ws.send_json({
                    "type": "system",
                    "text": text
                })
            except:
                self.active.pop(ws, None)


manager = ConnectionManager()


# ====== WEBSOCKET ======
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)

    try:
        while True:
            text = (await ws.receive_text()).strip()
            if not text:
                continue

            # установка ника
            if text.startswith("/nick "):
                nick = text.replace("/nick ", "").strip()
                if not nick:
                    await ws.send_json({
                        "type": "system",
                        "text": "❌ Ник не может быть пустым"
                    })
                    continue

                manager.active[ws] = nick
                await ws.send_json({
                    "type": "system",
                    "text": f"Ник установлен: {nick}"
                })
                await manager.broadcast_system(f"{nick} вошёл")
                continue

            nick = manager.active.get(ws)
            if not nick:
                await ws.send_json({
                    "type": "system",
                    "text": "❌ Сначала укажи ник"
                })
                continue

            await manager.broadcast_message(nick, text)

    except WebSocketDisconnect:
        await manager.disconnect(ws)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
