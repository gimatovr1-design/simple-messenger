from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from pathlib import Path

app = FastAPI()

HTML_FILE = Path(__file__).parent / "index.html"

@app.get("/")
async def root():
    return HTMLResponse(HTML_FILE.read_text(encoding="utf-8"))

@app.websocket("/ws/chat")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    while True:
        data = await ws.receive_text()
        await ws.send_text(f"echo: {data}")
