"""WebSocket job stream (Brief 18). Replays buffered events then streams live ones."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.jobs import manager

ws_router = APIRouter()


@ws_router.websocket("/ws/jobs/{job_id}")
async def ws_jobs(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()
    job = manager.get(job_id)
    if job is None:
        await websocket.send_json({"event": "error", "message": "unknown job"})
        await websocket.close()
        return

    queue: asyncio.Queue = asyncio.Queue()
    job.subscribers.add(queue)
    last = -1
    try:
        for event in list(job.events):            # backlog
            if event["_seq"] > last:
                await websocket.send_json(event)
                last = event["_seq"]
        while True:                               # live
            if job.status in ("done", "error") and queue.empty():
                break
            try:
                event = await asyncio.wait_for(queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            if event is None:
                break
            if event["_seq"] > last:
                await websocket.send_json(event)
                last = event["_seq"]
        await websocket.send_json({"event": "__closed__"})
    except WebSocketDisconnect:
        pass
    finally:
        job.subscribers.discard(queue)
