from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

connections = {}  # username -> websocket


@app.get("/")
async def index():
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


async def send_users():
    users = list(connections.keys())
    for ws in connections.values():
        await ws.send_json({
            "type": "users",
            "users": users
        })


@app.websocket("/ws/{username}")
async def websocket_endpoint(ws: WebSocket, username: str):
    await ws.accept()
    connections[username] = ws
    await send_users()

    try:
        while True:
            data = await ws.receive_json()

            if data.get("type") == "message":
                to = data.get("to")
                if to in connections:
                    await connections[to].send_json({
                        "type": "message",
                        "from": username,
                        "text": data.get("text")
                    })

    except WebSocketDisconnect:
        connections.pop(username, None)
        await send_users()
