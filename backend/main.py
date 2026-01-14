from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import uvicorn, os, json

app = FastAPI()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.get("/")
async def root():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

# ===============================
# ОБЩИЙ ЧАТ (БЕЗ ЛОМКИ)
# ===============================

class Manager:
    def __init__(self):
        self.clients: dict[WebSocket, str] = {}

    async def connect(self, ws: WebSocket, phone: str | None = None):
        await ws.accept()
        self.clients[ws] = phone or ""

    def disconnect(self, ws: WebSocket):
        self.clients.pop(ws, None)

    async def send(self, ws, data):
        await ws.send_json(data)

    async def broadcast(self, data, skip=None):
        for c in list(self.clients):
            if c != skip:
                try:
                    await c.send_json(data)
                except:
                    self.disconnect(c)

manager = Manager()

@app.websocket("/ws")
async def ws(ws: WebSocket):
    phone = ws.query_params.get("phone")  # 🔹 ДОБАВЛЕНО
    await manager.connect(ws, phone)      # 🔹 ИЗМЕНЕНО

    try:
        while True:
            msg = await ws.receive_text()

            if msg.startswith("/nick "):
                nick = msg[6:]
                manager.clients[ws] = nick

                await manager.send(ws, {
                    "type": "system",
                    "text": "✅ Ник установлен"
                })

                await manager.broadcast({
                    "type": "status",
                    "nick": nick,
                    "online": True
                })
                continue

            try:
                data = json.loads(msg)
            except:
                await manager.broadcast({
                    "type": "message",
                    "nick": manager.clients.get(ws, ""),
                    "text": msg
                })
                continue

            data["from"] = manager.clients.get(ws, "")
            if "to" in data:
                for c, n in manager.clients.items():
                    if n == data["to"]:
                        await manager.send(c, data)
            else:
                await manager.broadcast(data, skip=ws)

    except WebSocketDisconnect:
        nick = manager.clients.get(ws)
        if nick:
            await manager.broadcast({
                "type": "status",
                "nick": nick,
                "online": False
            })
        manager.disconnect(ws)

# ===============================
# АВТОРИЗАЦИЯ ПО НОМЕРУ (РАБОЧАЯ)
# ===============================

USERS_FILE = os.path.join(BASE_DIR, "users.json")

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

@app.post("/register")
async def register(data: dict):
    phone = data.get("phone")
    password = data.get("password")

    users = load_users()

    if phone in users:
        return {"ok": False, "error": "Пользователь уже существует"}

    users[phone] = {"password": password}
    save_users(users)
    return {"ok": True}

@app.post("/login")
async def login(data: dict):
    phone = data.get("phone")
    password = data.get("password")

    users = load_users()

    if phone not in users or users[phone]["password"] != password:
        return {"ok": False}

    return {"ok": True}

# ===============================
# ПРИВАТНЫЕ ЧАТЫ 1-на-1 (БЕЗ ИЗМЕНЕНИЙ)
# ===============================

class PrivateManager:
    def __init__(self):
        self.clients: dict[WebSocket, str] = {}

    async def connect(self, ws: WebSocket, phone: str):
        await ws.accept()
        self.clients[ws] = phone

    def disconnect(self, ws: WebSocket):
        self.clients.pop(ws, None)

    async def send_to(self, from_phone, to_phone, text):
        for ws, phone in self.clients.items():
            if phone == to_phone:
                await ws.send_json({
                    "from": from_phone,
                    "text": text
                })

private_manager = PrivateManager()

@app.websocket("/ws-private/{phone}")
async def ws_private(ws: WebSocket, phone: str):
    await private_manager.connect(ws, phone)
    try:
        while True:
            data = await ws.receive_json()
            await private_manager.send_to(
                phone,
                data["to"],
                data["text"]
            )
    except WebSocketDisconnect:
        private_manager.disconnect(ws)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
