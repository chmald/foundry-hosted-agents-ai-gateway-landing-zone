from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from typing import Iterator

from opentelemetry import trace

LOGGER = logging.getLogger("agent_telemetry")
TRACER = trace.get_tracer("foundry-hosted-agents.gateway")


def configure_telemetry() -> None:
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
    except Exception as exc:
        LOGGER.debug("HTTPX instrumentation not enabled: %s", exc)

    connection_string = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING") or os.environ.get("DD_APPLICATIONINSIGHTS_CONNECTION_STRING")
    if not connection_string:
        return
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor

        configure_azure_monitor(connection_string=connection_string)
    except Exception as exc:
        LOGGER.warning(json.dumps({"event": "telemetry_setup_failed", "reason": str(exc)}))


@contextmanager
def genai_span(name: str, **attributes: object) -> Iterator[None]:
    with TRACER.start_as_current_span(name) as span:
        for key, value in attributes.items():
            if value is not None:
                span.set_attribute(key, str(value))
        yield
