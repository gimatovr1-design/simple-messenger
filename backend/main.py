from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import FileResponse
import uvicorn, os, json

app = FastAPI()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.get("/")
async def root():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

# ===============================
# ОБЩИЙ ЧАТ (БЕЗ ИЗМЕНЕНИЙ)
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
    phone = ws.query_params.get("phone")
    await manager.connect(ws, phone)

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

            await manager.broadcast({
                "type": "message",
                "nick": manager.clients.get(ws, ""),
                "text": msg
            })

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
# АВТОРИЗАЦИЯ (ФИКС)
# ===============================

USERS_FILE = os.path.join(BASE_DIR, "users.json")

def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({}, f)
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

@app.post("/register")
async def register(request: Request):
    form = await request.form()
    phone = form.get("phone")
    password = form.get("password")

    users = load_users()

    if phone in users:
        return {"ok": False, "error": "exists"}

    users[phone] = {"password": password}
    save_users(users)
    return {"ok": True}

@app.post("/login")
async def login(request: Request):
    form = await request.form()
    phone = form.get("phone")
    password = form.get("password")

    users = load_users()

    if phone not in users or users[phone]["password"] != password:
        return {"ok": False}

    return {"ok": True}

# ===============================
# ЗАПУСК
# ===============================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
