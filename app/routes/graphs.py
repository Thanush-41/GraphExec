from fastapi import APIRouter, HTTPException, Request

from app.core.engine import WorkflowEngine
from app.models.schemas import GraphCreateRequest, GraphCreateResponse, GraphDefinition

router = APIRouter()


def get_engine(request: Request) -> WorkflowEngine:
    engine = getattr(request.app.state, "engine", None)
    if not engine:
        raise HTTPException(status_code=500, detail="Engine not configured")
    return engine


@router.post("/create", response_model=GraphCreateResponse)
async def create_graph(payload: GraphCreateRequest, request: Request) -> GraphCreateResponse:
    engine = get_engine(request)
    try:
        graph = GraphDefinition(**payload.dict())
        engine.register_graph(graph)
    except Exception as exc:  # pragma: no cover - validation error surfaces
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return GraphCreateResponse(graph_id=graph.graph_id)


@router.get("/{graph_id}", response_model=GraphDefinition)
async def get_graph(graph_id: str, request: Request) -> GraphDefinition:
    engine = get_engine(request)
    try:
        return engine.get_graph(graph_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Graph not found")


@router.get("/", response_model=list[GraphDefinition])
async def list_graphs(request: Request) -> list[GraphDefinition]:
    engine = get_engine(request)
    return list(engine.graphs.values())

