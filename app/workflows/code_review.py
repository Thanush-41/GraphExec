from __future__ import annotations

import re
from statistics import mean
from typing import Any, Dict, List

from app.core.engine import WorkflowEngine
from app.models.schemas import GraphDefinition, NodeDefinition, NodeType


def extract_functions(state: Dict[str, Any]) -> Dict[str, Any]:
    code = state.get("code", "")
    functions = re.findall(r"^def\s+([a-zA-Z_][a-zA-Z0-9_]*)", code, flags=re.MULTILINE)
    return {"functions": functions}


def check_complexity(state: Dict[str, Any]) -> Dict[str, Any]:
    code = state.get("code", "")
    lines = [line.strip() for line in code.splitlines() if line.strip()]
    branch_keywords = ("if ", "for ", "while ", "try:", "except ", "with ")
    complexities: List[int] = []
    current = 1
    for line in lines:
        if any(kw in line for kw in branch_keywords):
            current += 1
        if line.startswith("def "):
            complexities.append(current)
            current = 1
    complexities.append(current)
    avg_complexity = mean(complexities) if complexities else 1
    return {"avg_complexity": round(avg_complexity, 2)}


def detect_basic_issues(state: Dict[str, Any]) -> Dict[str, Any]:
    code = state.get("code", "")
    long_lines = [idx + 1 for idx, line in enumerate(code.splitlines()) if len(line) > 100]
    todo_comments = [idx + 1 for idx, line in enumerate(code.splitlines()) if "TODO" in line]
    issues = []
    if long_lines:
        issues.append({"type": "long_lines", "lines": long_lines})
    if todo_comments:
        issues.append({"type": "todo_comments", "lines": todo_comments})
    return {"issues": issues, "issue_count": len(issues)}


def suggest_improvements(state: Dict[str, Any]) -> Dict[str, Any]:
    issues = state.get("issues", [])
    suggestions: List[str] = []
    if state.get("avg_complexity", 1) > 5:
        suggestions.append("Reduce branching or split functions to lower complexity.")
    if any(issue.get("type") == "long_lines" for issue in issues):
        suggestions.append("Wrap or refactor long lines to improve readability.")
    if any(issue.get("type") == "todo_comments" for issue in issues):
        suggestions.append("Resolve or track TODO comments explicitly.")
    quality_score = max(0.1, 1.0 - 0.1 * len(suggestions))
    return {"suggestions": suggestions, "quality_score": round(quality_score, 2)}


def refine_suggestions(state: Dict[str, Any]) -> Dict[str, Any]:
    previous = state.get("suggestions", [])
    refined = previous + ["Apply one suggestion and re-evaluate quality."]
    new_score = min(1.0, (state.get("quality_score", 0.5) or 0.5) + 0.1)
    return {"suggestions": refined, "quality_score": round(new_score, 2)}


def register_code_review_workflow(engine: WorkflowEngine) -> None:
    engine.tools.register("extract_functions", extract_functions)
    engine.tools.register("check_complexity", check_complexity)
    engine.tools.register("detect_basic_issues", detect_basic_issues)
    engine.tools.register("suggest_improvements", suggest_improvements)
    engine.tools.register("refine_suggestions", refine_suggestions)

    nodes = [
        NodeDefinition(name="extract", type=NodeType.tool, next="complexity", config={"tool": "extract_functions"}),
        NodeDefinition(name="complexity", type=NodeType.tool, next="detect", config={"tool": "check_complexity"}),
        NodeDefinition(name="detect", type=NodeType.tool, next="suggest", config={"tool": "detect_basic_issues"}),
        NodeDefinition(name="suggest", type=NodeType.tool, next="quality_gate", config={"tool": "suggest_improvements"}),
        NodeDefinition(
            name="quality_gate",
            type=NodeType.conditional,
            config={"key": "quality_score", "op": ">=", "value": 0.8, "on_true": None, "on_false": "refine"},
        ),
        NodeDefinition(name="refine", type=NodeType.tool, next="quality_gate", config={"tool": "refine_suggestions"}),
    ]

    graph = GraphDefinition(graph_id="code_review", start_at="extract", nodes=nodes)
    engine.register_graph(graph)

