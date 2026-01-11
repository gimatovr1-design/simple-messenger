from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
import pathlib

app = FastAPI()
clients: list[WebSocket] = []

BASE_DIR = pathlib.Path(__file__).parent


@app.get("/", response_class=HTMLResponse)
async def index():
    return (BASE_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/favicon.ico")
async def favicon():
    return FileResponse(BASE_DIR / "favicon.ico")


@app.websocket("/ws")
async def websocket(ws: WebSocket):
    await ws.accept()
    clients.append(ws)
    try:
        while True:
            msg = await ws.receive_text()
            for c in clients:
                await c.send_text(msg)
    except WebSocketDisconnect:
        clients.remove(ws)
