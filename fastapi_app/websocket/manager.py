"""
WebSocket Connection Manager
Tracks active WebSocket connections and broadcasts messages
"""
from fastapi import WebSocket
from typing import List
import asyncio
import logging


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept and track a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection from tracking"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logging.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients"""
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logging.error(f"Error sending to client: {e}")
                dead_connections.append(connection)

        # Clean up dead connections
        for connection in dead_connections:
            self.disconnect(connection)

    async def broadcast_notification(self, level: str, message: str, details: str = ""):
        """
        Broadcast a notification to all connected clients.

        Args:
            level: Notification level ('info', 'warning', 'error', 'success')
            message: Main notification message
            details: Optional additional details
        """
        notification = {
            'type': 'notification',
            'level': level,
            'message': message,
            'details': details
        }
        await self.broadcast(notification)


# Global connection manager instance
manager = ConnectionManager()
