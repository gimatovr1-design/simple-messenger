from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from ws_manager import ConnectionManager

app = FastAPI()
manager = ConnectionManager()

app.mount("/static", StaticFiles(directory="."), name="static")


@app.get("/")
async def index():
    return FileResponse("index.html")


@app.get("/favicon.ico")
async def favicon():
    return FileResponse("favicon.ico")


@app.websocket("/ws/{username}")
async def websocket(ws: WebSocket, username: str):
    await manager.connect(ws, username)
    try:
        while True:
            data = await ws.receive_json()
            await manager.send_private(username, data["to"], data["message"])
    except WebSocketDisconnect:
        manager.disconnect(username)
        await manager.broadcast_users()
