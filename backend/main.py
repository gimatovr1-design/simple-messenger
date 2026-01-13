from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import uvicorn

app = FastAPI()

# ====== ОТДАЁМ ИМЕННО index.html ======
@app.get("/")
async def root():
    return FileResponse("index.html")


# ====== WS ======
clients = {}

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    nickname = "Гость"
    clients[ws] = nickname

    try:
        while True:
            data = await ws.receive_text()

            if data.startswith("/nick "):
                nickname = data.replace("/nick ", "").strip()
                clients[ws] = nickname
                continue

            for client, nick in clients.items():
                await client.send_text(f"{nickname}: {data}")

    except WebSocketDisconnect:
        clients.pop(ws, None)
