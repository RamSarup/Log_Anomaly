from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
	"""Keep track of dashboard sockets and broadcast events to all of them."""

	def __init__(self) -> None:
		self.active_connections: set[WebSocket] = set()

	async def connect(self, websocket: WebSocket) -> None:
		"""Accept a new dashboard connection and remember it."""
		await websocket.accept()
		self.active_connections.add(websocket)

	def disconnect(self, websocket: WebSocket) -> None:
		"""Forget a disconnected dashboard. discard() is safe if already removed."""
		self.active_connections.discard(websocket)

	async def broadcast(self, event: dict) -> None:
		"""Send one event to every connected dashboard."""
		disconnected: list[WebSocket] = []

		# Use a snapshot because a failed send may remove a connection.
		for websocket in list(self.active_connections):
			try:
				await websocket.send_json(event)
			except (WebSocketDisconnect, RuntimeError, OSError):
				disconnected.append(websocket)

		for websocket in disconnected:
			self.disconnect(websocket)
