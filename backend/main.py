from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import uvicorn, os, json

app = FastAPI()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.get("/")
async def root():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

class Manager:
    def __init__(self):
        self.clients: dict[WebSocket, str] = {}

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.clients[ws] = ""

    def disconnect(self, ws: WebSocket):
        self.clients.pop(ws, None)

    async def send(self, ws, data):
        await ws.send_json(data)

    async def broadcast(self, data, skip=None):
        for c in list(self.clients):
            if c != skip:
                try: await c.send_json(data)
                except: self.disconnect(c)

manager = Manager()

@app.websocket("/ws")
async def ws(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            msg = await ws.receive_text()

            if msg.startswith("/nick "):
                manager.clients[ws] = msg[6:]
                await manager.send(ws, {"type":"system","text":"✅ Ник установлен"})
                continue

            try:
                data = json.loads(msg)
            except:
                await manager.broadcast({
                    "type":"message",
                    "nick": manager.clients.get(ws,""),
                    "text": msg
                })
                continue

            data["from"] = manager.clients.get(ws,"")
            if "to" in data:
                for c,n in manager.clients.items():
                    if n == data["to"]:
                        await manager.send(c, data)
            else:
                await manager.broadcast(data, skip=ws)

    except WebSocketDisconnect:
        manager.disconnect(ws)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
