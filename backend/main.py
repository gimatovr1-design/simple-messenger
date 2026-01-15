from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, Response
from fastapi.responses import FileResponse
import uvicorn
import os
import json
import uuid
import hashlib

app = FastAPI()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.get("/")
async def root():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

# ===============================
# ЧАТ
# ===============================

class Manager:
    def __init__(self):
        self.clients = {}

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

    def get_online_list(self):
        return [nick for nick in self.clients.values() if nick]

manager = Manager()

@app.websocket("/ws")
async def websocket(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            msg = await ws.receive_text()

            if msg.startswith("/nick "):
                nick = msg[6:]
                manager.clients[ws] = nick

                await ws.send_json({
                    "type": "system",
                    "text": "✅ Ник установлен"
                })

                await manager.broadcast({
                    "type": "status",
                    "nick": nick,
                    "online": True
                })

                await manager.broadcast({
                    "type": "users",
                    "users": manager.get_online_list()   # 🔥 ВАЖНО
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

            await manager.broadcast({
                "type": "users",
                "users": manager.get_online_list()   # 🔥 ВАЖНО
            })

        manager.disconnect(ws)

# ===============================
# АВТОРИЗАЦИЯ
# ===============================

USERS_FILE = os.path.join(BASE_DIR, "users.json")

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def hash_password(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()

@app.post("/register")
async def register(data: dict = Body(...)):
    phone = data.get("phone")
    password = data.get("password")

    if not phone or not password:
        return {"status": "error"}

    users = load_users()
    if phone in users:
        return {"status": "error"}

    users[phone] = {
        "password": hash_password(password),
        "token": str(uuid.uuid4())
    }

    save_users(users)
    return {"status": "ok"}

@app.post("/login")
async def login(data: dict = Body(...), response: Response = None):
    phone = data.get("phone")
    password = data.get("password")

    if not phone or not password:
        return {"status": "error"}

    users = load_users()
    if phone not in users:
        return {"status": "error"}

    if users[phone]["password"] != hash_password(password):
        return {"status": "error"}

    response.set_cookie(
        key="token",
        value=users[phone]["token"],
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 365
    )

    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
