from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.core.engine import WorkflowEngine
from app.routes import execution, graphs, websocket
from app.workflows.code_review import register_code_review_workflow

app = FastAPI(title="GraphExec", version="0.1.0")
engine = WorkflowEngine()
register_code_review_workflow(engine)
app.state.engine = engine

app.include_router(graphs.router, prefix="/graph", tags=["graphs"])
app.include_router(execution.router, prefix="/graph", tags=["runs"])
app.include_router(websocket.router, tags=["websocket"])

# Serve static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    """Serve the web interface."""
    index_path = Path(__file__).parent / "static" / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "GraphExec API", "docs": "/docs", "health": "/health"}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "graphs": list(engine.graphs.keys())}

