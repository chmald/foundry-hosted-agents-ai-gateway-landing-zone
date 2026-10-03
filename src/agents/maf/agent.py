from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from agent_framework import Agent, MCPStreamableHTTPTool
from agent_framework.openai import OpenAIChatClient
from openai import AsyncOpenAI

from gateway_auth import PLACEHOLDER_API_KEY, GatewaySelection, build_http_client, resolve_gateway

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


def build_agent(selection: GatewaySelection | None = None) -> Agent:
    """Build the Microsoft Agent Framework agent without any network I/O.

    The shared httpx client authenticates every model and MCP request through the
    selected gateway. The official host enters the agent (and so connects the MCP
    tools) on the first request, so ``/readiness`` never waits on a backend.
    """
    profile = load_profile()
    selection = selection or resolve_gateway()
    http_client = build_http_client(selection)
    model = OpenAIChatClient(
        model=selection.model_deployment,
        async_client=AsyncOpenAI(base_url=selection.model_base_url_with_slash, api_key=PLACEHOLDER_API_KEY, http_client=http_client),
    )
    tools = [
        MCPStreamableHTTPTool(name=name, url=url, http_client=http_client, load_prompts=False, description=description, request_timeout=30)
        for name, url, description in (
            ("catalog", selection.catalog_mcp_url, "Catalog MCP tools"),
            ("records", selection.records_mcp_url, "Records MCP tools"),
        )
        if url
    ]
    return Agent(
        client=model,
        instructions=profile["agent"]["instructions"],
        name=profile["agent"]["name"],
        description=profile["agent"]["description"],
        tools=tools,
        default_options={"store": False},
    )
