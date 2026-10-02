from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from gateway_auth import GatewaySelection, gateway_headers, make_traceparent, resolve_gateway
from telemetry import genai_span

DEFAULT_PROFILE = "manufacturing-field-ops"


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


@dataclass
class AgentResult:
    text: str
    traceparent: str
    tool_calls: list[dict[str, Any]]


class GatewayJsonRpcToolClient:
    def __init__(self, endpoint: str, selection: GatewaySelection, client: httpx.AsyncClient | None = None) -> None:
        self.endpoint = endpoint
        self.selection = selection
        self.client = client or httpx.AsyncClient(timeout=45)
        self.session_id: str | None = None

    async def call_tool(self, name: str, arguments: dict[str, Any], traceparent: str) -> dict[str, Any]:
        if not self.endpoint:
            return {"tool": name, "arguments": arguments, "offline": True}
        headers = gateway_headers(self.selection, traceparent)
        headers.update({"Accept": "application/json, text/event-stream", "Content-Type": "application/json"})
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        payload = {"jsonrpc": "2.0", "id": "1", "method": "tools/call", "params": {"name": name, "arguments": arguments}}
        response = await self.client.post(self.endpoint, headers=headers, json=payload)
        response.raise_for_status()
        if response.headers.get("mcp-session-id"):
            self.session_id = response.headers["mcp-session-id"]
        body = response.json()
        if "error" in body:
            raise RuntimeError(body["error"].get("message", "MCP tool call failed"))
        result = body.get("result") or {}
        if result.get("structuredContent"):
            return result["structuredContent"]
        content = result.get("content") or []
        if content and isinstance(content[0], dict):
            try:
                return json.loads(content[0].get("text", "{}"))
            except json.JSONDecodeError:
                return {"text": content[0].get("text")}
        return result


class OfflineModelClient:
    async def respond(self, prompt: str, traceparent: str) -> str:
        return f"Offline demo response: {prompt}"


class HostedGatewayAgent:
    def __init__(self, *, model_client: Any | None = None, catalog_client: GatewayJsonRpcToolClient | None = None, records_client: GatewayJsonRpcToolClient | None = None, selection: GatewaySelection | None = None) -> None:
        self.profile = load_profile()
        self.selection = selection or resolve_gateway()
        self.model_client = model_client or OfflineModelClient()
        self.catalog_client = catalog_client or GatewayJsonRpcToolClient(self.selection.catalog_mcp_url, self.selection)
        self.records_client = records_client or GatewayJsonRpcToolClient(self.selection.records_mcp_url, self.selection)
        self.name = self.profile["agent"]["name"]

    async def invoke(self, prompt: str, traceparent: str | None = None) -> AgentResult:
        traceparent = make_traceparent(traceparent)
        lower = prompt.lower()
        calls: list[dict[str, Any]] = []
        with genai_span("invoke_agent", **{"gen_ai.agent.name": self.name, "agent.runtime": os.environ.get("DD_AGENT_RUNTIME") or os.environ.get("AGENT_RUNTIME", "local")}):
            if any(term in lower for term in ("stock", "availability", "available", "ready", "part", "device")):
                tool = "search_items"
                args: dict[str, Any] = {"query": prompt[:120]}
                token = next((word.strip(".,;:?!") for word in prompt.split() if "-" in word), "")
                if token:
                    tool = "check_availability"
                    args = {"item_id": token.upper(), "quantity": 1}
                with genai_span("execute_tool", **{"gen_ai.tool.name": tool}):
                    result = await self.catalog_client.call_tool(tool, args, traceparent)
                calls.append({"service": "catalog-mcp", "tool": tool, "arguments": args, "result": result})
                return AgentResult(f"{self.profile['labels']['items'].title()} result: {json.dumps(result, default=str)}", traceparent, calls)
            if any(term in lower for term in ("work order", "ticket", "record", "create")):
                tool = "list_records"
                args = {}
                with genai_span("execute_tool", **{"gen_ai.tool.name": tool}):
                    result = await self.records_client.call_tool(tool, args, traceparent)
                calls.append({"service": "records-api", "tool": tool, "arguments": args, "result": result})
                return AgentResult(f"{self.profile['labels']['records'].title()} result: {json.dumps(result, default=str)}", traceparent, calls)
            with genai_span("chat", **{"gen_ai.request.model": self.selection.model_deployment}):
                text = await self.model_client.respond(f"{self.profile['agent']['instructions']}\n\nUser: {prompt}", traceparent)
            return AgentResult(text, traceparent, calls)


async def build_langgraph_agent() -> Any:
    from langchain.agents import create_agent
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_openai import ChatOpenAI

    profile = load_profile()
    selection = resolve_gateway()
    model = ChatOpenAI(
        model=selection.model_deployment,
        base_url=selection.model_base_url_with_slash,
        api_key=selection.api_key,
        default_headers=selection.default_headers,
        use_responses_api=True,
        output_version="responses/v1",
    )
    client = MultiServerMCPClient(
        {
            "catalog": {"transport": "streamable_http", "url": selection.catalog_mcp_url, "headers": gateway_headers(selection)},
            "records": {"transport": "streamable_http", "url": selection.records_mcp_url, "headers": gateway_headers(selection)},
        }
    )
    tools = await client.get_tools()
    return create_agent(model=model, tools=tools, system_prompt=profile["agent"]["instructions"])
