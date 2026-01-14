from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, Response, Request
from fastapi.responses import FileResponse, RedirectResponse
import uvicorn, os, json, uuid, hashlib

app = FastAPI()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ===============================
# СТРАНИЦЫ
# ===============================

@app.get("/")
async def root(request: Request):
    if not request.cookies.get("token"):
        return RedirectResponse("/login")
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

@app.get("/login")
async def login_page():
    return FileResponse(os.path.join(BASE_DIR, "login.html"))

@app.get("/register")
async def register_page():
    return FileResponse(os.path.join(BASE_DIR, "register.html"))

# ===============================
# ОБЩИЙ ЧАТ (НЕ ТРОНУТ)
# ===============================

class Manager:
    def __init__(self):
        self.clients: dict[WebSocket, str] = {}

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.clients[ws] = ""

    def disconnect(self, ws: WebSocket):
        self.clients.pop(ws, None)

    async def broadcast(self, data):
        for c in list(self.clients):
            try:
                await c.send_json(data)
            except:
                self.disconnect(c)

manager = Manager()

@app.websocket("/ws")
async def ws(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            msg = await ws.receive_text()

            if msg.startswith("/nick "):
                nick = msg[6:]
                manager.clients[ws] = nick
                await ws.send_json({"type": "system", "text": "✅ Ник установлен"})
                await manager.broadcast({"type": "status", "nick": nick, "online": True})
                continue

            await manager.broadcast({
                "type": "message",
                "nick": manager.clients.get(ws, ""),
                "text": msg
            })

    except WebSocketDisconnect:
        nick = manager.clients.get(ws)
        if nick:
            await manager.broadcast({"type": "status", "nick": nick, "online": False})
        manager.disconnect(ws)

# ===============================
# АВТОРИЗАЦИЯ (РАБОЧАЯ)
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

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

@app.post("/register")
async def register(data: dict = Body(...)):
    phone = data.get("phone")
    password = data.get("password")

    if not phone or not password:
        return {"ok": False, "error": "empty"}

    users = load_users()

    if phone in users:
        return {"ok": False, "error": "exists"}

    users[phone] = {
        "password": hash_password(password),
        "token": str(uuid.uuid4())
    }

    save_users(users)
    return {"ok": True}

@app.post("/login")
async def login(data: dict = Body(...), response: Response = Response()):
    phone = data.get("phone")
    password = data.get("password")

    users = load_users()

    if phone not in users:
        return {"ok": False}

    if users[phone]["password"] != hash_password(password):
        return {"ok": False}

    response.set_cookie(
        key="token",
        value=users[phone]["token"],
        httponly=True,
        max_age=60 * 60 * 24 * 365
    )

    return {"ok": True}

# ===============================
# ЗАПУСК
# ===============================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

