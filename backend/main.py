from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, Response, Request
from fastapi.responses import FileResponse
import uvicorn
import os
import uuid
import hashlib
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.get("/")
async def root():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

# ===============================
# MANAGER
# ===============================

class Manager:
    def __init__(self):
        self.clients = {}  # ws -> nick

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

    def users(self):
        return [n for n in self.clients.values() if n]

manager = Manager()

# ===============================
# WEBSOCKET
# ===============================

@app.websocket("/ws")
async def websocket(ws: WebSocket):
    await manager.connect(ws)

    try:
        while True:
            msg = await ws.receive_text()

            # установка ника
            if msg.startswith("/nick "):
                nick = msg[6:].strip()
                manager.clients[ws] = nick

                await manager.broadcast({
                    "type": "system",
                    "text": f"🟢 {nick} зашёл"
                })

                await manager.broadcast({
                    "type": "users",
                    "users": manager.users()
                })
                continue

            # обычное сообщение
            nick = manager.clients.get(ws, "")
            if not nick:
                continue

            await manager.broadcast({
                "type": "message",
                "nick": nick,
                "text": msg
            })

    except WebSocketDisconnect:
        nick = manager.clients.get(ws, "")
        manager.disconnect(ws)

        if nick:
            await manager.broadcast({
                "type": "system",
                "text": f"🔴 {nick} вышел"
            })

        await manager.broadcast({
            "type": "users",
            "users": manager.users()
        })

# ===============================
# AUTH (SUPABASE)
# ===============================

def hash_password(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()

@app.post("/register")
async def register(data: dict = Body(...)):
    phone = data.get("phone")
    password = data.get("password")
    if not phone or not password:
        return {"ok": False}

    if supabase.table("users").select("id").eq("phone", phone).execute().data:
        return {"ok": False}

    token = str(uuid.uuid4())

    supabase.table("users").insert({
        "phone": phone,
        "password_hash": hash_password(password),
        "token": token
    }).execute()

    return {"ok": True}

@app.post("/login")
async def login(response: Response, data: dict = Body(...)):
    phone = data.get("phone")
    password = data.get("password")

    res = supabase.table("users").select("*").eq("phone", phone).execute()
    if not res.data:
        return {"ok": False}

    if res.data[0]["password_hash"] != hash_password(password):
        return {"ok": False}

    response.set_cookie(
        key="token",
        value=res.data[0]["token"],
        httponly=True,
        max_age=60 * 60 * 24 * 365
    )
    return {"ok": True}

@app.post("/logout")
async def logout(response: Response):
    response.delete_cookie("token")
    return {"ok": True}

@app.get("/me")
async def me(request: Request):
    token = request.cookies.get("token")
    if not token:
        return {"auth": False}

    res = supabase.table("users").select("phone").eq("token", token).execute()
    if not res.data:
        return {"auth": False}

    return {"auth": True}

# ===============================
# RUN
# ===============================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
