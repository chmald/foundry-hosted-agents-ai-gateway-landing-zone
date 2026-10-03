from __future__ import annotations

import logging
import os

from langchain_azure_ai.agents.hosting import InvocationsHostServer, ResponsesHostServer

from agent import build_agent
from gateway_auth import hosted_setting
from telemetry import configure_telemetry

LOGGER = logging.getLogger("agent_host")


def build_host(protocol: str | None = None) -> ResponsesHostServer | InvocationsHostServer:
    """Return the official LangGraph host for the selected protocol; ``host.app`` is the ASGI app."""
    selected = (protocol or hosted_setting("PROTOCOL", "responses")).lower()
    LOGGER.info("agent_host framework=langgraph protocol=%s runtime=%s", selected, hosted_setting("RUNTIME", "local"))
    graph = build_agent()
    if selected == "invocations":
        return InvocationsHostServer(graph)
    if selected == "responses":
        return ResponsesHostServer(graph)
    raise RuntimeError("HOSTED_PROTOCOL must be 'responses' or 'invocations'.")


configure_telemetry()
host = build_host()
app = host.app


if __name__ == "__main__":
    host.run(port=int(os.environ.get("PORT", "8088")))
