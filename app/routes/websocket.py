import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.engine import WorkflowEngine

router = APIRouter()


def get_engine_from_app(websocket: WebSocket) -> WorkflowEngine:
    return websocket.app.state.engine


@router.websocket("/ws/run/{run_id}")
async def websocket_run_logs(websocket: WebSocket, run_id: str):
    """Stream execution logs for a running workflow via WebSocket."""
    await websocket.accept()
    engine = get_engine_from_app(websocket)

    try:
        queue = engine.subscribe(run_id)
    except KeyError:
        await websocket.send_json({"error": f"Unknown run_id '{run_id}'"})
        await websocket.close()
        return

    try:
        # Send current state first
        run_response = engine.get_run(run_id)
        await websocket.send_json({
            "event": "connected",
            "run_id": run_id,
            "status": run_response.status.value,
            "current_log_count": len(run_response.log)
        })

        # Stream live updates
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_json(message)
                if message.get("event") in ("run_completed", "run_failed"):
                    break
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"event": "heartbeat"})
                # Check if run is still active
                run_response = engine.get_run(run_id)
                if run_response.status.value in ("completed", "failed"):
                    await websocket.send_json({
                        "event": f"run_{run_response.status.value}",
                        "run_id": run_id,
                        "state": run_response.state
                    })
                    break
    except WebSocketDisconnect:
        pass
    finally:
        engine.unsubscribe(run_id, queue)
        try:
            await websocket.close()
        except Exception:
            pass


@router.websocket("/ws/run")
async def websocket_run_workflow(websocket: WebSocket):
    """Start a workflow and stream logs via WebSocket.
    
    Send JSON: {"graph_id": "...", "initial_state": {...}}
    """
    await websocket.accept()
    engine = get_engine_from_app(websocket)

    try:
        # Receive workflow request
        data = await websocket.receive_json()
        graph_id = data.get("graph_id")
        initial_state = data.get("initial_state", {})

        if not graph_id:
            await websocket.send_json({"error": "graph_id is required"})
            await websocket.close()
            return

        # Start the run (don't wait)
        run_id = await engine.run_graph(graph_id, initial_state=initial_state, wait_for_completion=False)
        
        # Subscribe to updates
        queue = engine.subscribe(run_id)
        
        await websocket.send_json({
            "event": "run_started",
            "run_id": run_id,
            "graph_id": graph_id
        })

        # Stream updates
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_json(message)
                if message.get("event") in ("run_completed", "run_failed"):
                    break
            except asyncio.TimeoutError:
                await websocket.send_json({"event": "heartbeat"})
                run_response = engine.get_run(run_id)
                if run_response.status.value in ("completed", "failed"):
                    break

    except WebSocketDisconnect:
        pass
    except KeyError as e:
        await websocket.send_json({"error": str(e)})
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
