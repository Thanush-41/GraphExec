from fastapi import APIRouter, HTTPException, Request

from app.core.engine import WorkflowEngine
from app.models.schemas import GraphRunRequest, RunResponse

router = APIRouter()


def get_engine(request: Request) -> WorkflowEngine:
    engine = getattr(request.app.state, "engine", None)
    if not engine:
        raise HTTPException(status_code=500, detail="Engine not configured")
    return engine


@router.post("/run", response_model=RunResponse)
async def run_graph(payload: GraphRunRequest, request: Request) -> RunResponse:
    engine = get_engine(request)
    try:
        run_id = await engine.run_graph(
            payload.graph_id, initial_state=payload.initial_state, wait_for_completion=payload.wait_for_completion
        )
        if payload.wait_for_completion:
            await engine.wait_for_run(run_id)
        return engine.get_run(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Graph not found")
    except Exception as exc:  # pragma: no cover - surfaced via API
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/state/{run_id}", response_model=RunResponse)
async def get_run_state(run_id: str, request: Request) -> RunResponse:
    engine = get_engine(request)
    try:
        return engine.get_run(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found")

