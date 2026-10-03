from __future__ import annotations

import asyncio
import filecmp

import httpx
from conftest import ROOT, load_module


def _gateway():
    return load_module("gateway_client_test", ROOT / "src" / "agents" / "maf" / "gateway_auth.py")


def test_traceparent_created_and_gateway_headers_stripped():
    module = _gateway()
    tp = module.make_traceparent()
    assert tp.startswith("00-") and len(tp.split("-")) == 4
    headers = module.strip_gateway_headers({"x-gw-user-oid": "bad", "traceparent": tp, "X-GW-Agent-Oid": "bad", "api-key": "meter"})
    low = {k.lower() for k in headers}
    assert "x-gw-user-oid" not in low and "x-gw-agent-oid" not in low
    assert headers["traceparent"] == tp


def test_agent_gateway_auth_helpers_are_byte_identical():
    assert filecmp.cmp(ROOT / "src" / "agents" / "maf" / "gateway_auth.py", ROOT / "src" / "agents" / "langgraph" / "gateway_auth.py", shallow=False)


def test_gateway_selection_headers(monkeypatch):
    module = _gateway()
    monkeypatch.setenv("HOSTED_DEFAULT_GATEWAY", "aigateway")
    monkeypatch.setenv("AIGW_GATEWAY_URL", "https://example.azure-api.net")
    monkeypatch.setenv("AIGW_KEY_DELIVERY", "env")
    monkeypatch.setenv("AIGW_RUNTIME_KEY", "local-key")
    selected = module.resolve_gateway()
    assert selected.target == "aigateway" and selected.model_base_url == "https://example.azure-api.net/default/models/openai/v1"
    headers = module.gateway_headers(selected, "00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-bbbbbbbbbbbbbbbb-01")
    assert headers["api-key"] == "local-key" and not any(k.lower().startswith("x-gw-") for k in headers)
    monkeypatch.setenv("HOSTED_DEFAULT_GATEWAY", "apimv2")
    monkeypatch.setenv("APIM_GATEWAY_URL", "https://apim.azure-api.net")
    monkeypatch.setenv("LLM_API_PATH", "llm")
    monkeypatch.setenv("GATEWAY_AUDIENCE", "api://demo")
    assert module.resolve_gateway().model_base_url == "https://apim.azure-api.net/llm/openai/v1"


def test_hosted_names_win_and_unprefixed_names_are_local_fallbacks(monkeypatch):
    module = _gateway()
    for name in ("HOSTED_DEFAULT_GATEWAY", "AGENT_DEFAULT_GATEWAY", "HOSTED_PROTOCOL", "AGENT_PROTOCOL"):
        monkeypatch.delenv(name, raising=False)
    assert module.hosted_setting("PROTOCOL", "responses") == "responses"
    monkeypatch.setenv("AGENT_PROTOCOL", "invocations")
    assert module.hosted_setting("PROTOCOL", "responses") == "invocations"
    monkeypatch.setenv("HOSTED_PROTOCOL", "responses")
    assert module.hosted_setting("PROTOCOL", "responses") == "responses"


def test_outbound_requests_get_fresh_credentials_and_traceparent(monkeypatch):
    module = _gateway()
    monkeypatch.setenv("HOSTED_DEFAULT_GATEWAY", "aigateway")
    monkeypatch.setenv("AIGW_GATEWAY_URL", "https://example.azure-api.net")
    monkeypatch.setenv("AIGW_KEY_DELIVERY", "env")
    monkeypatch.setenv("AIGW_RUNTIME_KEY", "local-key")
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={})

    async def run():
        client = module.build_http_client(module.resolve_gateway())
        client._transport = httpx.MockTransport(handler)
        await client.post("https://example.azure-api.net/x", headers={"x-gw-user-oid": "bad", "authorization": f"Bearer {module.PLACEHOLDER_API_KEY}"})
        await client.aclose()

    asyncio.run(run())
    request = seen[0]
    assert request.headers["api-key"] == "local-key" and request.headers["traceparent"].startswith("00-")
    assert "x-gw-user-oid" not in request.headers and "authorization" not in request.headers