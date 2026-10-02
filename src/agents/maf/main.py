from __future__ import annotations

import os
import signal
import uuid
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

from agent import HostedGatewayAgent, build_framework_agent
from gateway_auth import make_traceparent
from telemetry import configure_telemetry

configure_telemetry()

app = FastAPI(title="Foundry Hosted Agent - Microsoft Agent Framework", version="1.1.0")
app.state.agent = HostedGatewayAgent()


class ResponsesRequest(BaseModel):
    model: str | None = None
    input: str | list[Any] = Field(default="")
    metadata: dict[str, Any] = Field(default_factory=dict)


def input_to_text(value: str | list[Any]) -> str:
    if isinstance(value, str):
        return value
    parts: list[str] = []
    for item in value:
        if isinstance(item, dict):
            content = item.get("content", "")
            if isinstance(content, list):
                parts.extend(str(part.get("text", part)) if isinstance(part, dict) else str(part) for part in content)
            else:
                parts.append(str(content))
        else:
            parts.append(str(item))
    return "\n".join(part for part in parts if part)


@app.get("/readiness")
def readiness() -> dict[str, str]:
    return {"status": "ok", "agent": app.state.agent.name, "framework": "maf", "runtime": os.environ.get("DD_AGENT_RUNTIME") or os.environ.get("AGENT_RUNTIME", "local")}


@app.post("/responses")
async def responses(payload: ResponsesRequest, request: Request) -> dict[str, Any]:
    result = await app.state.agent.invoke(input_to_text(payload.input), traceparent=make_traceparent(request.headers.get("traceparent")))
    return {
        "id": f"resp_{uuid.uuid4().hex}",
        "object": "response",
        "created_at": 0,
        "model": payload.model or os.environ.get("MODEL_DEPLOYMENT_NAME") or os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME") or "chat",
        "output_text": result.text,
        "output": [{"id": f"msg_{uuid.uuid4().hex}", "type": "message", "role": "assistant", "content": [{"type": "output_text", "text": result.text}]}],
        "metadata": {"traceparent": result.traceparent, "tool_calls": result.tool_calls},
    }


@app.post("/invocations")
async def invocations(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    prompt = str(payload.get("input") or payload.get("prompt") or payload.get("message") or "")
    result = await app.state.agent.invoke(prompt, traceparent=make_traceparent(request.headers.get("traceparent")))
    return {"response": result.text, "traceparent": result.traceparent, "tool_calls": result.tool_calls}


def run_offline_host() -> None:
    port = int(os.environ.get("PORT", "8088"))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    signal.signal(signal.SIGTERM, lambda *_: setattr(server, "should_exit", True))
    server.run()


def main() -> None:
    if os.environ.get("FHAGL_USE_FASTAPI_FALLBACK") == "1":
        run_offline_host()
        return
    protocol = (os.environ.get("DD_AGENT_PROTOCOL") or os.environ.get("AGENT_PROTOCOL", "responses")).lower()
    try:
        from agent_framework_foundry_hosting import InvocationsHostServer, ResponsesHostServer
    except ImportError:
        run_offline_host()
        return

    agent = build_framework_agent()
    port = int(os.environ.get("PORT", "8088"))
    if protocol == "invocations":
        InvocationsHostServer(agent=agent).run(port=port)
    else:
        ResponsesHostServer(agent=agent, history_source="agent_server").run(port=port)


if __name__ == "__main__":
    main()
