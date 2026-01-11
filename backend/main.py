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


def save_message(message: str):
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

        # 🔥 отправляем историю при подключении
        for msg in load_messages():
            await websocket.send_text(msg)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active:
            del self.active[websocket]

    async def broadcast(self, message: str):
        save_message(message)  # 💾 сохраняем сообщение
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
            data = data.strip()

            if not data:
                continue

            if data.startswith("/nick "):
                nick = data.replace("/nick ", "").strip()
                if not nick:
                    await websocket.send_text("❌ Ник не может быть пустым")
                    continue

                manager.active[websocket] = nick
                await websocket.send_text(f"✅ Ник установлен: {nick}")
                continue

            nick = manager.active.get(websocket, "")
            if not nick:
                await websocket.send_text("❌ Сначала укажи ник")
                continue

            message = f"{nick}: {data}"
            await manager.broadcast(message)

    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
