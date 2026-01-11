from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pathlib import Path

app = FastAPI()

HTML_FILE = Path(__file__).parent / "index.html"

online_users = set()
connections = []

@app.get("/")
async def get():
    return HTMLResponse(HTML_FILE.read_text(encoding="utf-8"))

@app.websocket("/ws/chat")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connections.append(ws)
    username = None

    try:
        while True:
            data = await ws.receive_text()

            # первое сообщение — ник
            if data.startswith("__join__"):
                username = data.replace("__join__", "")
                online_users.add(username)
                await broadcast_users()
                await broadcast(f"🟢 {username} вошёл в чат")
                continue

            await broadcast(data)

    except WebSocketDisconnect:
        connections.remove(ws)
        if username:
            online_users.discard(username)
            await broadcast_users()
            await broadcast(f"🔴 {username} вышел из чата")

async def broadcast(message: str):
    for ws in connections:
        await ws.send_text(message)

async def broadcast_users():
    users = ", ".join(sorted(online_users))
    for ws in connections:
        await ws.send_text(f"__users__{users}")
