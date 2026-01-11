from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, ws: WebSocket, username: str):
        await ws.accept()
        self.active_connections[username] = ws
        await self.broadcast_users()

    def disconnect(self, username: str):
        self.active_connections.pop(username, None)

    async def send_private(self, sender: str, recipient: str, message: str):
        if recipient in self.active_connections:
            await self.active_connections[recipient].send_json({
                "from": sender,
                "message": message
            })

    async def broadcast_users(self):
        users = list(self.active_connections.keys())
        for ws in self.active_connections.values():
            await ws.send_json({
                "type": "users",
                "users": users
            })
