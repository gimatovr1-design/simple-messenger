from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from pathlib import Path

app = FastAPI()

@app.get("/")
async def root():
    html = Path("index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)

clients: list[WebSocket] = []

@app.websocket("/ws/chat")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    clients.append(ws)

    try:
        while True:
            data = await ws.receive_text()
            for client in clients:
                if client != ws:
                    await client.send_text(data)
    except:
        clients.remove(ws)
