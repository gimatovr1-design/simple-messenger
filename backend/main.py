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
# WEBSOCKET
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

    def get_online(self):
        return [n for n in self.clients.values() if n]

manager = Manager()

@app.websocket("/ws")
async def websocket(ws: WebSocket):
    await manager.connect(ws)

    # 🔹 загрузка истории
    history = supabase.table("messages").select("*").order("id").execute()
    for m in history.data:
        await ws.send_json({
            "type": "message",
            "nick": m["nick"],
            "text": m["text"]
        })

    try:
        while True:
            msg = await ws.receive_text()

            if msg.startswith("/nick "):
                nick = msg[6:]
                manager.clients[ws] = nick
                await ws.send_json({"type": "system", "text": "✅ Ник установлен"})
                await manager.broadcast({"type": "users", "users": manager.get_online()})
                continue

            # 🔹 сохраняем сообщение
            supabase.table("messages").insert({
                "nick": manager.clients.get(ws, ""),
                "text": msg
            }).execute()

            await manager.broadcast({
                "type": "message",
                "nick": manager.clients.get(ws, ""),
                "text": msg
            })

    except WebSocketDisconnect:
        manager.disconnect(ws)
        await manager.broadcast({"type": "users", "users": manager.get_online()})

# ===============================
# AUTH
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
        "token": token,
        "nickname": phone
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

    response.set_cookie("token", res.data[0]["token"], httponly=True, max_age=31536000)
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

    return {"auth": True, "phone": res.data[0]["phone"]}

# ===============================
# CLEAR CHAT (ТЫ ВИДИШЬ КНОПКУ)
# ===============================

@app.post("/clear")
async def clear():
    supabase.table("messages").delete().neq("id", 0).execute()
    return {"ok": True}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
