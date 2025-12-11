import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Import after path setup
import httpx

BASE_URL = "http://127.0.0.1:8000"


async def run_tests():
    print("=" * 60)
    print("GraphExec Live Server Verification")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: Health check
        print("\n[1/5] Testing health endpoint...")
        resp = await client.get(f"{BASE_URL}/health")
        health = resp.json()
        print(f"  ✓ Status: {resp.status_code}")
        print(f"  ✓ Registered graphs: {health['graphs']}")
        
        # Test 2: List graphs
        print("\n[2/5] Testing list graphs endpoint...")
        resp = await client.get(f"{BASE_URL}/graph/")
        graphs = resp.json()
        print(f"  ✓ Found {len(graphs)} graph(s)")
        for g in graphs:
            print(f"    - {g['graph_id']} with {len(g['nodes'])} nodes")
        
        # Test 3: Get specific graph
        print("\n[3/5] Testing get graph endpoint...")
        resp = await client.get(f"{BASE_URL}/graph/code_review")
        graph = resp.json()
        print(f"  ✓ Retrieved graph: {graph['graph_id']}")
        print(f"  ✓ Start node: {graph['start_at']}")
        
        # Test 4: Run workflow
        print("\n[4/5] Testing workflow execution...")
        payload = {
            "graph_id": "code_review",
            "initial_state": {
                "code": """def calculate(x, y, z):
    # TODO: add validation
    result = x + y * z
    if result > 100:
        return result
    else:
        return 0
"""
            },
            "wait_for_completion": True
        }
        resp = await client.post(f"{BASE_URL}/graph/run", json=payload)
        run = resp.json()
        print(f"  ✓ Run completed with status: {run['status']}")
        print(f"  ✓ Run ID: {run['run_id']}")
        print(f"  ✓ Quality score: {run['state'].get('quality_score')}")
        print(f"  ✓ Functions found: {len(run['state'].get('functions', []))}")
        print(f"  ✓ Average complexity: {run['state'].get('avg_complexity')}")
        print(f"  ✓ Issues detected: {run['state'].get('issue_count')}")
        print(f"  ✓ Execution log entries: {len(run['log'])}")
        
        # Test 5: Get run state
        print("\n[5/5] Testing get run state endpoint...")
        resp = await client.get(f"{BASE_URL}/graph/state/{run['run_id']}")
        run_state = resp.json()
        print(f"  ✓ Retrieved run state: {run_state['status']}")
        print(f"  ✓ State matches: {run_state['run_id'] == run['run_id']}")
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print(f"Server is running at {BASE_URL}")
    print(f"API docs available at {BASE_URL}/docs")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_tests())
