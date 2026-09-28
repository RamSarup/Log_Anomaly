import asyncio
import contextlib
from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.event_generator import LogGenerator, event_stream
from backend.websocket_manager import ConnectionManager

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

manager = ConnectionManager()


async def run_event_pipeline() -> None:
    """Read events from the source and broadcast each one to all dashboards."""
    async for event in event_stream():
        await manager.broadcast(event)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log_path = Path(os.getenv("LOG_PATH", str(FRONTEND_DIR.parent / "logs" / "application.log")))
    generator = LogGenerator(path=log_path, rate=float(os.getenv("LOG_RATE", "2")))
    generator.start()
    task = asyncio.create_task(run_event_pipeline())
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
    generator.stop()


app = FastAPI(title="Real-Time Log Anomaly Detector", lifespan=lifespan)

# Serves style.css and app.js at /static/...
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
async def health() -> dict:
    return {"status": "ok", "connected_clients": len(manager.active_connections)}


@app.get("/dashboard")
async def dashboard() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        # Keep the connection open. We don't need messages from the browser,
        # but awaiting receive lets us notice when the client disconnects.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)