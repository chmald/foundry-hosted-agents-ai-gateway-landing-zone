from __future__ import annotations

import logging

LOGGER = logging.getLogger("agent_telemetry")


def configure_telemetry() -> None:
    """Instrument outbound httpx so model and MCP calls carry ``traceparent``.

    The official host owns exporter setup: it reads the platform-injected
    ``APPLICATIONINSIGHTS_CONNECTION_STRING`` itself and disables httpx
    instrumentation, so this is the only telemetry wiring the agent adds.
    """
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
    except Exception as exc:
        LOGGER.warning("HTTPX instrumentation not enabled: %s", exc)
