from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

connections = {}  # username -> websocket


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

    username = username.strip().lower()
    connections[username] = ws
    await send_users()

    try:
        while True:
            data = await ws.receive_json()  # 👈 ТОЛЬКО JSON

            if data.get("type") == "message":
                to_user = data.get("to")
                if to_user in connections:
                    await connections[to_user].send_json({
                        "type": "message",
                        "from": username,
                        "text": data.get("text")
                    })

    except WebSocketDisconnect:
        connections.pop(username, None)
        await send_users()

