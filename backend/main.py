from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

app = FastAPI()


class ConnectionManager:
    def __init__(self):
        self.active: dict[WebSocket, str] = {}

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active[ws] = "Гость"

    def disconnect(self, ws: WebSocket):
        self.active.pop(ws, None)

    async def broadcast(self, message: str):
        for ws in list(self.active.keys()):
            try:
                await ws.send_text(message)
            except:
                self.disconnect(ws)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)

    await manager.broadcast(f"{manager.active[ws]} подключился")

    try:
        while True:
            text = await ws.receive_text()

            # смена ника
            if text.startswith("/nick "):
                new_nick = text.replace("/nick ", "", 1).strip()
                if new_nick:
                    old = manager.active[ws]
                    manager.active[ws] = new_nick
                    await manager.broadcast(f"{old} сменил ник на {new_nick}")
                continue

            # обычное сообщение
            await manager.broadcast(f"{manager.active[ws]}: {text}")

    except WebSocketDisconnect:
        username = manager.active.get(ws, "Гость")
        manager.disconnect(ws)
        await manager.broadcast(f"{username} отключился")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
