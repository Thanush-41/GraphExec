$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "GraphExec Live Server Verification" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Wait for server startup
Start-Sleep -Seconds 2

# Test 1: Health check
Write-Host "[1/4] Testing health endpoint..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri http://127.0.0.1:8000/health -Method Get
    Write-Host "  ✓ Status: OK" -ForegroundColor Green
    Write-Host "  ✓ Registered graphs: $($health.graphs -join ', ')" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Health check failed: $_" -ForegroundColor Red
    exit 1
}

# Test 2: List graphs
Write-Host "`n[2/4] Testing list graphs endpoint..." -ForegroundColor Yellow
try {
    $graphs = Invoke-RestMethod -Uri http://127.0.0.1:8000/graph/ -Method Get
    Write-Host "  ✓ Found $($graphs.Count) graph(s)" -ForegroundColor Green
    foreach ($g in $graphs) {
        Write-Host "    - $($g.graph_id) with $($g.nodes.Count) nodes" -ForegroundColor Gray
    }
} catch {
    Write-Host "  ✗ List graphs failed: $_" -ForegroundColor Red
    exit 1
}

# Test 3: Get specific graph
Write-Host "`n[3/4] Testing get graph endpoint..." -ForegroundColor Yellow
try {
    $graph = Invoke-RestMethod -Uri http://127.0.0.1:8000/graph/code_review -Method Get
    Write-Host "  ✓ Retrieved graph: $($graph.graph_id)" -ForegroundColor Green
    Write-Host "  ✓ Start node: $($graph.start_at)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Get graph failed: $_" -ForegroundColor Red
    exit 1
}

# Test 4: Run workflow
Write-Host "`n[4/4] Testing workflow execution..." -ForegroundColor Yellow
try {
    $payload = @{
        graph_id = "code_review"
        initial_state = @{
            code = @"
def calculate(x, y, z):
    # TODO: add validation
    result = x + y * z
    if result > 100:
        return result
    else:
        return 0
"@
        }
        wait_for_completion = $true
    } | ConvertTo-Json -Depth 10

    $run = Invoke-RestMethod -Uri http://127.0.0.1:8000/graph/run -Method Post -Body $payload -ContentType "application/json"
    
    Write-Host "  ✓ Run completed with status: $($run.status)" -ForegroundColor Green
    Write-Host "  ✓ Run ID: $($run.run_id)" -ForegroundColor Green
    Write-Host "  ✓ Quality score: $($run.state.quality_score)" -ForegroundColor Green
    Write-Host "  ✓ Functions found: $($run.state.functions.Count)" -ForegroundColor Green
    Write-Host "  ✓ Average complexity: $($run.state.avg_complexity)" -ForegroundColor Green
    Write-Host "  ✓ Issues detected: $($run.state.issue_count)" -ForegroundColor Green
    Write-Host "  ✓ Execution log entries: $($run.log.Count)" -ForegroundColor Green
    
    # Test 5: Get run state
    Write-Host "`n[5/5] Testing get run state endpoint..." -ForegroundColor Yellow
    $runState = Invoke-RestMethod -Uri "http://127.0.0.1:8000/graph/state/$($run.run_id)" -Method Get
    Write-Host "  ✓ Retrieved run state: $($runState.status)" -ForegroundColor Green
    
} catch {
    Write-Host "  ✗ Workflow execution failed: $_" -ForegroundColor Red
    Write-Host "  Error details: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "All tests passed! ✓" -ForegroundColor Green
Write-Host "Server is running at http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "API docs available at http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
