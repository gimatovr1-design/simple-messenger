from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import json
import os
from uuid import uuid4

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MESSAGES_FILE = os.path.join(BASE_DIR, "messages.json")

# ===== ПАПКА ДЛЯ ФОТО / ВИДЕО =====
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


# ===================== CHAT STORAGE =====================
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


# ===================== UPLOAD =====================
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1]
    name = f"{uuid4()}{ext}"
    path = os.path.join(UPLOAD_DIR, name)

    with open(path, "wb") as f:
        f.write(await file.read())

    return {"url": f"/uploads/{name}"}


# ===================== CHAT =====================
class ConnectionManager:
    def __init__(self):
        self.active: dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active[websocket] = ""

        # отправляем историю
        for msg in load_messages():
            await websocket.send_json({
                "type": "message",
                "nick": msg.get("nick", ""),
                "text": msg.get("text", "")
            })

    def disconnect(self, websocket: WebSocket):
        self.active.pop(websocket, None)

    async def broadcast(self, message: dict):
        save_message(message)
        for ws in list(self.active):
            try:
                await ws.send_json(message)
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

            # /nick
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
                    "text": "❌ Сначала укажи ник"
                })
                continue

            await manager.broadcast({
                "type": "message",
                "nick": nick,
                "text": text
            })

    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ===================== WEBRTC SIGNALING =====================
video_rooms: dict[str, set[WebSocket]] = {}

@app.websocket("/webrtc")
async def webrtc_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            data = json.loads(await websocket.receive_text())
            msg_type = data.get("type")
            room = data.get("room")

            if not room:
                continue

            # join room
            if msg_type == "video_join":
                video_rooms.setdefault(room, set()).add(websocket)
                continue

            # relay signaling
            if msg_type in ("video_offer", "video_answer", "video_ice"):
                for ws in video_rooms.get(room, set()):
                    if ws != websocket:
                        try:
                            await ws.send_text(json.dumps(data))
                        except:
                            pass

    except WebSocketDisconnect:
        # очистка
        for room in video_rooms.values():
            room.discard(websocket)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
