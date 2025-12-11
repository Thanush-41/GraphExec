# GraphExec

A minimal FastAPI-based agent workflow engine. Define graphs of nodes, maintain shared state, and execute them with branching and simple loops. Ships with a sample **Code Review Mini-Agent** workflow and a web interface.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

### Core Engine
- **Node Types**: Tool, Conditional, and Loop nodes with shared state updates
- **State Management**: Dictionary-based state flows between nodes with automatic merging
- **Branching**: Conditional routing based on state values (supports `==`, `!=`, `>`, `>=`, `<`, `<=`)
- **Looping**: Iterate nodes until conditions are met (with max iteration safety cap)
- **Tool Registry**: Plug in sync or async Python functions as workflow tools

### API & Real-time Features
- **REST API**: Full CRUD for graphs and workflow execution
- **WebSocket Streaming**: Real-time execution logs streamed step-by-step
- **Async Execution**: Background task support with `wait_for_completion=false`
- **Web Interface**: Interactive UI to run workflows and view live logs

### Sample Workflow: Code Review Mini-Agent
Implements **Option A** from the assignment:
1. **Extract functions** - Parse Python code to find function definitions
2. **Check complexity** - Calculate cyclomatic complexity metrics
3. **Detect basic issues** - Find long lines, TODO comments, etc.
4. **Suggest improvements** - Generate actionable suggestions
5. **Loop until quality_score >= 0.8** - Refine iteratively

## 📁 Project Structure

```
app/
├── main.py                 # FastAPI app entry point
├── core/
│   └── engine.py           # WorkflowEngine - core execution logic (~200 LOC)
├── models/
│   └── schemas.py          # Pydantic models for API validation
├── routes/
│   ├── graphs.py           # Graph CRUD endpoints
│   ├── execution.py        # Run workflow endpoints
│   └── websocket.py        # WebSocket streaming endpoints
├── tools/
│   └── registry.py         # Tool registration and invocation
├── workflows/
│   └── code_review.py      # Sample code review workflow
└── static/
    └── index.html          # Web interface
```

## 🚀 Quickstart

### Prerequisites
- Python 3.11+

### Installation

```bash
# Clone and enter directory
cd GraphExec

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate
# Or (Unix/macOS)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload
```

### Access Points
- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📡 API Reference

### Graph Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/graph/` | GET | List all registered graphs |
| `/graph/{graph_id}` | GET | Get a specific graph definition |
| `/graph/create` | POST | Register a new graph |

### Workflow Execution

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/graph/run` | POST | Execute a workflow |
| `/graph/state/{run_id}` | GET | Get current run state and logs |

### WebSocket Endpoints

| Endpoint | Description |
|----------|-------------|
| `/ws/run` | Start workflow and stream logs |
| `/ws/run/{run_id}` | Subscribe to existing run logs |

## 💻 Usage Examples

### Run via REST API

```bash
curl -X POST http://localhost:8000/graph/run \
  -H "Content-Type: application/json" \
  -d '{
    "graph_id": "code_review",
    "initial_state": {
      "code": "def add(a, b):\n    # TODO: improve\n    return a + b"
    }
  }'
```

### Run via WebSocket (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/run');

ws.onopen = () => {
  ws.send(JSON.stringify({
    graph_id: 'code_review',
    initial_state: { code: 'def example(): pass' }
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.event, data);
};
```

### Create Custom Graph via API

```bash
curl -X POST http://localhost:8000/graph/create \
  -H "Content-Type: application/json" \
  -d '{
    "graph_id": "my_workflow",
    "start_at": "step1",
    "nodes": [
      {"name": "step1", "type": "tool", "next": "step2", "config": {"tool": "my_tool"}},
      {"name": "step2", "type": "conditional", "config": {
        "key": "score", "op": ">=", "value": 0.8,
        "on_true": null, "on_false": "step1"
      }}
    ]
  }'
```

## 🔧 Engine Architecture

### Node Types

1. **Tool Node**: Executes a registered Python function
   ```python
   NodeDefinition(
       name="analyze",
       type=NodeType.tool,
       next="next_node",
       config={"tool": "analyze_code"}
   )
   ```

2. **Conditional Node**: Branches based on state comparison
   ```python
   NodeDefinition(
       name="check",
       type=NodeType.conditional,
       config={
           "key": "quality_score",
           "op": ">=",
           "value": 0.8,
           "on_true": "done",
           "on_false": "retry"
       }
   )
   ```

3. **Loop Node**: Repeats body until condition fails
   ```python
   NodeDefinition(
       name="iterate",
       type=NodeType.loop,
       config={
           "key": "count",
           "op": "<",
           "value": 10,
           "body": "process",
           "after": "finalize",
           "max_iterations": 25
       }
   )
   ```

### Registering Custom Tools

```python
from app.core.engine import WorkflowEngine

engine = WorkflowEngine()

# Sync function
def my_tool(state: dict) -> dict:
    return {"result": state.get("input", "") + " processed"}

engine.tools.register("my_tool", my_tool)

# Async function
async def async_tool(state: dict) -> dict:
    await asyncio.sleep(1)
    return {"async_result": "done"}

engine.tools.register("async_tool", async_tool)
```

## 📊 Sample Workflow Output

```json
{
  "run_id": "abc123...",
  "status": "completed",
  "state": {
    "code": "def add(a, b): ...",
    "functions": ["add"],
    "avg_complexity": 1.5,
    "issues": [{"type": "todo_comments", "lines": [2]}],
    "issue_count": 1,
    "suggestions": ["Resolve or track TODO comments explicitly."],
    "quality_score": 0.9
  },
  "log": [
    {"node": "extract", "status": "start", ...},
    {"node": "extract", "status": "end", ...},
    ...
  ]
}
```

## 🔮 Improvements With More Time

- **Persistent Storage**: SQLite/PostgreSQL for graphs and run history
- **Parallel Execution**: Run independent branches concurrently
- **Timeouts & Cancellation**: Graceful handling of long-running workflows
- **Authentication**: API key or JWT-based auth
- **Structured Logging**: JSON logs with correlation IDs
- **Graph Visualization**: Interactive node editor in web UI
- **Retry Policies**: Configurable retry on tool failures
- **Metrics & Monitoring**: Prometheus endpoints for observability

## 📝 License

MIT

---

Built as part of an AI Engineering Internship assignment. Focus areas: clean Python, async programming, API design, and state-based workflow execution.
