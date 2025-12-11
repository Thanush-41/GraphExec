import asyncio
import inspect
from typing import Any, Callable, Dict, Optional


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Callable[[Dict[str, Any]], Any]] = {}

    def register(self, name: str, fn: Callable[[Dict[str, Any]], Any]) -> None:
        self._tools[name] = fn

    def get(self, name: str) -> Optional[Callable[[Dict[str, Any]], Any]]:
        return self._tools.get(name)

    async def invoke(self, name: str, state: Dict[str, Any]) -> Dict[str, Any]:
        fn = self.get(name)
        if not fn:
            raise ValueError(f"Tool '{name}' is not registered")
        if inspect.iscoroutinefunction(fn):
            result = await fn(state)
        else:
            result = await asyncio.to_thread(fn, state)
        return result or {}

    def list_tools(self) -> Dict[str, str]:
        return {name: fn.__doc__ or "" for name, fn in self._tools.items()}

