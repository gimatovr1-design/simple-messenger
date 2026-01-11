from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pathlib import Path
from ws_manager import ConnectionManager

app = FastAPI()
manager = ConnectionManager()

# онлайн пользователи
online_users = set()

HTML_FILE = Path(__file__).parent / "index.html"


@app.get("/")
async def root():
    return HTMLResponse(HTML_FILE.read_text(encoding="utf-8"))


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await manager.connect(websocket)

    username = None

    try:
        # первый пакет — ник пользователя
        data = await websocket.receive_json()
        username = data.get("user", "anonymous")
        online_users.add(username)

        # сообщаем всем, что пользователь зашёл
        await manager.broadcast_json({
            "type": "join",
            "user": username,
            "online": list(online_users)
        })

        while True:
            data = await websocket.receive_json()

            await manager.broadcast_json({
                "type": "message",
                "user": username,
                "text": data.get("text", "")
            })

    except WebSocketDisconnect:
        manager.disconnect(websocket)

        if username:
            online_users.discard(username)

            await manager.broadcast_json({
                "type": "leave",
                "user": username,
                "online": list(online_users)
            })
