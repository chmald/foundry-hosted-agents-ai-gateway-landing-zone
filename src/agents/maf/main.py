from __future__ import annotations

import logging
import os

from agent_framework_foundry_hosting import InvocationsHostServer, ResponsesHostServer

from agent import build_agent
from gateway_auth import hosted_setting
from telemetry import configure_telemetry

LOGGER = logging.getLogger("agent_host")


def build_host(protocol: str | None = None) -> ResponsesHostServer | InvocationsHostServer:
    """Return the official Foundry host (itself the ASGI app) for the selected protocol."""
    selected = (protocol or hosted_setting("PROTOCOL", "responses")).lower()
    LOGGER.info("agent_host framework=maf protocol=%s runtime=%s", selected, hosted_setting("RUNTIME", "local"))
    agent = build_agent()
    if selected == "invocations":
        return InvocationsHostServer(agent=agent)
    if selected == "responses":
        return ResponsesHostServer(agent=agent, history_source="agent_server")
    raise RuntimeError("HOSTED_PROTOCOL must be 'responses' or 'invocations'.")


configure_telemetry()
app = build_host()


if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", "8088")))
