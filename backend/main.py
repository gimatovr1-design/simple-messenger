from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pathlib import Path
import json

app = FastAPI()

MESSAGES_FILE = Path("messages.json")


@app.get("/")
async def root():
    return FileResponse("index.html")


class ConnectionManager:
    def __init__(self):
        self.active = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.append(websocket)

        # отправляем сохранённую историю
        if MESSAGES_FILE.exists():
            messages = json.loads(MESSAGES_FILE.read_text(encoding="utf-8"))
            for msg in messages:
                await websocket.send_text(
                    json.dumps(msg, ensure_ascii=False)
                )

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, message: str):
        for ws in list(self.active):
            try:
                await ws.send_text(message)
            except:
                self.disconnect(ws)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    nickname = "Гость"

    try:
        while True:
            data = json.loads(await websocket.receive_text())

            # смена ника
            if data["type"] == "nick":
                nickname = data["nick"]
                continue

            # сообщение
            if data["type"] == "message":
                msg = {
                    "nick": nickname,
                    "text": data["text"]
                }

                # сохраняем
                messages = json.loads(
                    MESSAGES_FILE.read_text(encoding="utf-8")
                )
                messages.append(msg)

                MESSAGES_FILE.write_text(
                    json.dumps(messages, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )

                await manager.broadcast(
                    json.dumps(msg, ensure_ascii=False)
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
