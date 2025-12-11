import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

print("=" * 60)
print("GraphExec Verification")
print("=" * 60)

# Health check
health_resp = client.get("/health")
print(f"\n✓ Health check: {health_resp.status_code}")
print(f"  {json.dumps(health_resp.json(), indent=2)}")

# List graphs
graphs_resp = client.get("/graph/")
print(f"\n✓ List graphs: {graphs_resp.status_code}")
print(f"  Registered graphs: {[g['graph_id'] for g in graphs_resp.json()]}")

# Run code review workflow
payload = {
    "graph_id": "code_review",
    "initial_state": {
        "code": "def add(a, b):\n    # TODO: improve\n    return a + b"
    }
}
print(f"\n✓ Running code_review workflow...")
run_resp = client.post("/graph/run", json=payload)
result = run_resp.json()

print(f"  Status: {run_resp.status_code}")
print(f"  Run ID: {result['run_id']}")
print(f"  Workflow Status: {result['status']}")
print(f"  Quality Score: {result['state'].get('quality_score')}")
print(f"  Issues Found: {len(result['state'].get('issues', []))}")
print(f"  Suggestions: {len(result['state'].get('suggestions', []))}")
print(f"  Execution Log Entries: {len(result['log'])}")

# Show execution flow
print(f"\n✓ Execution flow:")
for entry in result['log']:
    if entry['status'] == 'start':
        print(f"  → {entry['node']}")

print("\n" + "=" * 60)
print("All checks passed ✓")
print("=" * 60)
