from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active: dict[str, WebSocket] = {}

    async def connect(self, ws: WebSocket, username: str):
        await ws.accept()
        self.active[username] = ws
        await self.broadcast_users()

    def disconnect(self, username: str):
        self.active.pop(username, None)

    async def send_private(self, sender, recipient, message):
        if recipient in self.active:
            await self.active[recipient].send_json({
                "type": "message",
                "from": sender,
                "message": message
            })

    async def broadcast_users(self):
        users = list(self.active.keys())
        for ws in self.active.values():
            await ws.send_json({
                "type": "users",
                "users": users
            })
