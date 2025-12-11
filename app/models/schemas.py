from __future__ import annotations

import enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class NodeType(str, enum.Enum):
    tool = "tool"
    conditional = "conditional"
    loop = "loop"


class NodeDefinition(BaseModel):
    name: str = Field(..., description="Unique node identifier")
    type: NodeType
    next: Optional[str] = Field(None, description="Next node to execute when applicable")
    config: Dict[str, Any] = Field(default_factory=dict, description="Type-specific configuration")

    class Config:
        extra = "forbid"


class GraphDefinition(BaseModel):
    graph_id: str
    start_at: str
    nodes: List[NodeDefinition]

    @model_validator(mode="after")
    def validate_graph(self) -> "GraphDefinition":
        node_names = {n.name for n in self.nodes}
        if self.start_at not in node_names:
            raise ValueError(f"start_at node '{self.start_at}' is not defined")
        for node in self.nodes:
            if node.next and node.next not in node_names:
                raise ValueError(f"Node '{node.name}' references unknown next node '{node.next}'")
            if node.type == NodeType.conditional:
                for key in ("on_true", "on_false"):
                    target = node.config.get(key)
                    if target and target not in node_names:
                        raise ValueError(f"Conditional node '{node.name}' references unknown node '{target}'")
            if node.type == NodeType.loop:
                for key in ("body", "after"):
                    target = node.config.get(key)
                    if target and target not in node_names:
                        raise ValueError(f"Loop node '{node.name}' references unknown node '{target}'")
        return self


class GraphCreateRequest(BaseModel):
    graph_id: str
    start_at: str
    nodes: List[NodeDefinition]


class GraphCreateResponse(BaseModel):
    graph_id: str


class GraphRunRequest(BaseModel):
    graph_id: str
    initial_state: Dict[str, Any] = Field(default_factory=dict)
    wait_for_completion: bool = True


class RunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class LogEntry(BaseModel):
    node: str
    status: Literal["start", "end", "error"]
    detail: Optional[str] = None
    state_snapshot: Optional[Dict[str, Any]] = None


class RunRecord(BaseModel):
    run_id: str
    graph_id: str
    state: Dict[str, Any]
    current_node: Optional[str]
    status: RunStatus = RunStatus.pending
    log: List[LogEntry] = Field(default_factory=list)


class RunResponse(BaseModel):
    run_id: str
    graph_id: str
    status: RunStatus
    state: Dict[str, Any]
    log: List[LogEntry]

