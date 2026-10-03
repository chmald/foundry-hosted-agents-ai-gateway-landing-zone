from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI

from gateway_auth import PLACEHOLDER_API_KEY, GatewayAuth, GatewaySelection, build_http_client, resolve_gateway

DEFAULT_PROFILE = "manufacturing-field-ops"
LOGGER = logging.getLogger("agent_host")


def _candidate_roots() -> list[Path]:
    here = Path(__file__).resolve()
    roots = [here.parent, Path.cwd()]
    roots.extend(here.parents)
    return list(dict.fromkeys(roots))


def load_profile() -> dict[str, Any]:
    profile_name = os.environ.get("DOMAIN_PROFILE") or DEFAULT_PROFILE
    candidates: list[Path] = []
    for root in _candidate_roots():
        candidates.append(root / "config" / "profiles" / f"{profile_name}.json")
        candidates.append(root / "profiles" / f"{profile_name}.json")
    for path in candidates:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    raise RuntimeError(f"Profile not found for DOMAIN_PROFILE={profile_name!r}. Checked: {', '.join(str(p) for p in candidates)}")


class LazyMcpToolsMiddleware(AgentMiddleware):
    """Load the gateway MCP tools on the first model call instead of at import.

    ``MultiServerMCPClient.get_tools()`` is network I/O, so it must not run while the
    host starts (``/readiness`` has to pass even when a backend is slow). A server that
    cannot be reached is skipped for that request and retried on the next one.
    """

    def __init__(self, servers: dict[str, dict[str, Any]], timeout_seconds: float = 30.0) -> None:
        super().__init__()
        self._servers = servers
        self._timeout = timeout_seconds
        self._tools: dict[str, list[BaseTool]] = {}
        self._lock = asyncio.Lock()

    async def _load_server(self, name: str, connection: dict[str, Any]) -> None:
        try:
            client = MultiServerMCPClient({name: connection})
            self._tools[name] = await asyncio.wait_for(client.get_tools(), timeout=self._timeout)
            LOGGER.info("mcp_tools_loaded server=%s count=%d", name, len(self._tools[name]))
        except Exception as exc:  # noqa: BLE001 - degrade to no tools and retry on the next request
            LOGGER.warning("mcp_tools_unavailable server=%s error=%s", name, exc)

    async def _tools_for_request(self) -> list[BaseTool]:
        async with self._lock:
            pending = [(name, conn) for name, conn in self._servers.items() if name not in self._tools]
            await asyncio.gather(*(self._load_server(name, conn) for name, conn in pending))
            return [tool for tools in self._tools.values() for tool in tools]

    async def awrap_model_call(self, request: Any, handler: Callable[[Any], Awaitable[Any]]) -> Any:
        tools = await self._tools_for_request()
        return await handler(request.override(tools=[*request.tools, *tools]))

    async def awrap_tool_call(self, request: Any, handler: Callable[[Any], Awaitable[Any]]) -> Any:
        if request.tool is None:
            known = {tool.name: tool for tools in self._tools.values() for tool in tools}
            tool = known.get(request.tool_call["name"])
            if tool is not None:
                request = request.override(tool=tool)
        return await handler(request)


def build_agent(selection: GatewaySelection | None = None) -> Any:
    """Build the LangChain agent graph without any network I/O."""
    profile = load_profile()
    selection = selection or resolve_gateway()
    model = ChatOpenAI(
        model=selection.model_deployment,
        base_url=selection.model_base_url_with_slash,
        api_key=PLACEHOLDER_API_KEY,
        http_async_client=build_http_client(selection),
        use_responses_api=True,
        output_version="responses/v1",
        store=False,
    )
    servers = {
        name: {"transport": "streamable_http", "url": url, "auth": GatewayAuth(selection), "timeout": 30}
        for name, url in (("catalog", selection.catalog_mcp_url), ("records", selection.records_mcp_url))
        if url
    }
    return create_agent(
        model,
        tools=[],
        system_prompt=profile["agent"]["instructions"],
        name=profile["agent"]["name"],
        middleware=[LazyMcpToolsMiddleware(servers)] if servers else [],
    )
