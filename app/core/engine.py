from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.models.schemas import (
    GraphDefinition,
    LogEntry,
    NodeDefinition,
    NodeType,
    RunResponse,
    RunStatus,
)
from app.tools.registry import ToolRegistry


@dataclass
class RunState:
    run_id: str
    graph_id: str
    state: Dict[str, Any]
    current_node: Optional[str]
    status: RunStatus = RunStatus.pending
    log: List[LogEntry] = field(default_factory=list)
    loop_counts: Dict[str, int] = field(default_factory=dict)
    task: Optional[asyncio.Task] = None
    subscribers: List[asyncio.Queue] = field(default_factory=list)


class WorkflowEngine:
    def __init__(self, tools: Optional[ToolRegistry] = None) -> None:
        self.tools = tools or ToolRegistry()
        self.graphs: Dict[str, GraphDefinition] = {}
        self._runs: Dict[str, RunState] = {}
        self._lock = asyncio.Lock()

    def register_graph(self, graph: GraphDefinition) -> None:
        self.graphs[graph.graph_id] = graph

    def get_graph(self, graph_id: str) -> GraphDefinition:
        if graph_id not in self.graphs:
            raise KeyError(f"Unknown graph_id '{graph_id}'")
        return self.graphs[graph_id]

    async def run_graph(
        self, graph_id: str, initial_state: Optional[Dict[str, Any]] = None, wait_for_completion: bool = True
    ) -> str:
        graph = self.get_graph(graph_id)
        run_id = str(uuid.uuid4())
        run_state = RunState(run_id=run_id, graph_id=graph_id, state=dict(initial_state or {}), current_node=graph.start_at)
        async with self._lock:
            self._runs[run_id] = run_state
        task = asyncio.create_task(self._execute(graph, run_state))
        run_state.task = task
        if wait_for_completion:
            await task
        return run_id

    async def wait_for_run(self, run_id: str) -> RunState:
        run_state = self._runs.get(run_id)
        if not run_state:
            raise KeyError(f"Unknown run_id '{run_id}'")
        if run_state.task:
            await asyncio.shield(run_state.task)
        return run_state

    def get_run(self, run_id: str) -> RunResponse:
        run_state = self._runs.get(run_id)
        if not run_state:
            raise KeyError(f"Unknown run_id '{run_id}'")
        return RunResponse(
            run_id=run_state.run_id,
            graph_id=run_state.graph_id,
            status=run_state.status,
            state=run_state.state,
            log=run_state.log,
        )

    async def _execute(self, graph: GraphDefinition, run_state: RunState) -> None:
        run_state.status = RunStatus.running
        await self._notify_subscribers(run_state, {"event": "run_started", "run_id": run_state.run_id})
        node_lookup = {node.name: node for node in graph.nodes}
        current = graph.start_at
        try:
            while current:
                run_state.current_node = current
                log_entry = LogEntry(node=current, status="start", state_snapshot=dict(run_state.state))
                run_state.log.append(log_entry)
                await self._notify_subscribers(run_state, {"event": "node_start", "node": current, "state": run_state.state})
                node = node_lookup[current]
                current = await self._execute_node(node, run_state)
                log_entry = LogEntry(node=node.name, status="end", state_snapshot=dict(run_state.state))
                run_state.log.append(log_entry)
                await self._notify_subscribers(run_state, {"event": "node_end", "node": node.name, "state": run_state.state})
            run_state.current_node = None
            run_state.status = RunStatus.completed
            await self._notify_subscribers(run_state, {"event": "run_completed", "run_id": run_state.run_id, "state": run_state.state})
        except Exception as exc:  # pragma: no cover - surfaced via API
            run_state.status = RunStatus.failed
            run_state.log.append(LogEntry(node=current or "unknown", status="error", detail=str(exc), state_snapshot=dict(run_state.state)))
            run_state.current_node = None
            await self._notify_subscribers(run_state, {"event": "run_failed", "run_id": run_state.run_id, "error": str(exc)})
            raise

    async def _notify_subscribers(self, run_state: RunState, message: Dict[str, Any]) -> None:
        for queue in run_state.subscribers:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                pass

    def subscribe(self, run_id: str) -> asyncio.Queue:
        run_state = self._runs.get(run_id)
        if not run_state:
            raise KeyError(f"Unknown run_id '{run_id}'")
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        run_state.subscribers.append(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue) -> None:
        run_state = self._runs.get(run_id)
        if run_state and queue in run_state.subscribers:
            run_state.subscribers.remove(queue)

    async def _execute_node(self, node: NodeDefinition, run_state: RunState) -> Optional[str]:
        if node.type == NodeType.tool:
            tool_name = node.config.get("tool")
            if not tool_name:
                raise ValueError(f"Tool node '{node.name}' is missing 'tool' in config")
            await self._invoke_tool(tool_name, run_state)
            return node.next
        if node.type == NodeType.conditional:
            return self._evaluate_conditional(node, run_state)
        if node.type == NodeType.loop:
            return self._evaluate_loop(node, run_state)
        raise ValueError(f"Unsupported node type {node.type}")

    async def _invoke_tool(self, tool_name: str, run_state: RunState) -> None:
        tool = self.tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' is not registered")
        result = await self.tools.invoke(tool_name, run_state.state)
        if result:
            run_state.state.update(result)

    def _evaluate_conditional(self, node: NodeDefinition, run_state: RunState) -> Optional[str]:
        key = node.config.get("key")
        op = node.config.get("op", "==")
        target = node.config.get("value")
        on_true = node.config.get("on_true")
        on_false = node.config.get("on_false")
        if key is None:
            raise ValueError(f"Conditional node '{node.name}' is missing 'key'")
        value = run_state.state.get(key)
        passed = self._compare(value, op, target)
        return on_true if passed else on_false or node.next

    def _evaluate_loop(self, node: NodeDefinition, run_state: RunState) -> Optional[str]:
        key = node.config.get("key")
        op = node.config.get("op", "==")
        target = node.config.get("value")
        body = node.config.get("body")
        after = node.config.get("after")
        max_iterations = node.config.get("max_iterations", 25)
        if key is None or body is None:
            raise ValueError(f"Loop node '{node.name}' requires 'key' and 'body'")
        count = run_state.loop_counts.get(node.name, 0)
        value = run_state.state.get(key)
        continue_loop = self._compare(value, op, target)
        if continue_loop and count >= max_iterations:
            return after
        if continue_loop:
            run_state.loop_counts[node.name] = count + 1
            return body
        return after or node.next

    @staticmethod
    def _compare(value: Any, op: str, target: Any) -> bool:
        if op == "==":
            return value == target
        if op == "!=":
            return value != target
        if op == ">":
            return value is not None and target is not None and value > target
        if op == ">=":
            return value is not None and target is not None and value >= target
        if op == "<":
            return value is not None and target is not None and value < target
        if op == "<=":
            return value is not None and target is not None and value <= target
        raise ValueError(f"Unsupported operator '{op}'")


def register_tool(engine: WorkflowEngine, name: str, fn) -> None:
    engine.tools.register(name, fn)

