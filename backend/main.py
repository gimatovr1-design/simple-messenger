from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
import pathlib

app = FastAPI()
clients: list[tuple[WebSocket, str]] = []

BASE = pathlib.Path(__file__).parent


@app.get("/", response_class=HTMLResponse)
async def index():
    return (BASE / "index.html").read_text(encoding="utf-8")


@app.get("/favicon.ico")
async def favicon():
    return FileResponse(BASE / "favicon.ico")


@app.websocket("/ws")
async def websocket(ws: WebSocket):
    await ws.accept()
    nickname = await ws.receive_text()  # первый пакет — ник
    clients.append((ws, nickname))

    try:
        while True:
            msg = await ws.receive_text()
            for c, name in clients:
                await c.send_text(f"{nickname}: {msg}")
    except WebSocketDisconnect:
        clients.remove((ws, nickname))
