from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pathlib import Path

app = FastAPI()
HTML_FILE = Path(__file__).parent / "index.html"

connections = {}  # username -> websocket

@app.get("/")
async def get():
    return HTMLResponse(HTML_FILE.read_text(encoding="utf-8"))

@app.websocket("/ws/chat")
async def websocket(ws: WebSocket):
    await ws.accept()
    username = None

    try:
        while True:
            data = await ws.receive_text()

            # регистрация пользователя
            if data.startswith("__join__"):
                username = data.replace("__join__", "")
                connections[username] = ws
                await broadcast_users()
                continue

            # приватное сообщение
            if data.startswith("__to__"):
                target, msg = data.replace("__to__", "").split("|", 1)

                if target in connections:
                    await connections[target].send_text(
                        f"{username}: {msg}"
                    )
                    await ws.send_text(
                        f"Вы → {target}: {msg}"
                    )

    except WebSocketDisconnect:
        if username in connections:
            del connections[username]
            await broadcast_users()

async def broadcast_users():
    users = ",".join(connections.keys())
    for ws in connections.values():
        await ws.send_text("__users__" + users)
