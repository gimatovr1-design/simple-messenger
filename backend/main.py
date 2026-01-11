from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from ws_manager import ConnectionManager

app = FastAPI()
manager = ConnectionManager()

# Статика (index.html + favicon.ico)
app.mount("/static", StaticFiles(directory="."), name="static")


@app.get("/")
async def get_index():
    return FileResponse("index.html")


@app.get("/favicon.ico")
async def favicon():
    return FileResponse("favicon.ico")


@app.websocket("/ws/{username}")
async def websocket_endpoint(ws: WebSocket, username: str):
    await manager.connect(ws, username)
    try:
        while True:
            data = await ws.receive_json()
            await manager.send_private(
                sender=username,
                recipient=data["to"],
                message=data["message"]
            )
    except WebSocketDisconnect:
        manager.disconnect(username)
