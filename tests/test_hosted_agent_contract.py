from __future__ import annotations

import pytest
from conftest import ROOT, load_module

HOST_PACKAGES = {"maf": "agent_framework_foundry_hosting", "langgraph": "langchain_azure_ai.agents.hosting"}
EXPECTED_HOSTS = {
    "responses": "ResponsesHostServer",
    "invocations": "InvocationsHostServer",
}


def _asgi(host):
    from starlette.applications import Starlette

    return host if isinstance(host, Starlette) else host.app


@pytest.fixture
def offline_env(monkeypatch):
    monkeypatch.setenv("DOMAIN_PROFILE", "manufacturing-field-ops")
    monkeypatch.setenv("HOSTED_DEFAULT_GATEWAY", "aigateway")
    monkeypatch.setenv("AIGW_GATEWAY_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("AIGW_KEY_DELIVERY", "env")
    monkeypatch.setenv("AIGW_RUNTIME_KEY", "local-key")
    monkeypatch.delenv("HOSTED_PROTOCOL", raising=False)
    monkeypatch.delenv("AGENT_PROTOCOL", raising=False)


def _load(agent_dir):
    pytest.importorskip(HOST_PACKAGES[agent_dir])
    return load_module(f"{agent_dir}_main_test", ROOT / "src" / "agents" / agent_dir / "main.py")


@pytest.mark.parametrize("agent_dir", ["maf", "langgraph"])
def test_official_responses_host_contract(offline_env, agent_dir):
    from starlette.testclient import TestClient

    module = _load(agent_dir)
    assert type(module.build_host("responses")).__name__ == EXPECTED_HOSTS["responses"]
    client = TestClient(_asgi(module.build_host("responses")))
    readiness = client.get("/readiness")
    assert readiness.status_code == 200 and readiness.json()["status"] == "healthy"
    response = client.post("/responses", json={"input": "hello", "stream": False})
    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "response" and body["status"] in {"completed", "failed"}
    if body["status"] == "failed":
        assert body["error"]["code"] and body["error"]["message"]


@pytest.mark.parametrize("agent_dir", ["maf", "langgraph"])
def test_official_invocations_host_contract(offline_env, monkeypatch, agent_dir):
    from starlette.testclient import TestClient

    monkeypatch.setenv("HOSTED_PROTOCOL", "invocations")
    module = _load(agent_dir)
    host = module.build_host()
    assert type(host).__name__ == EXPECTED_HOSTS["invocations"]
    client = TestClient(_asgi(host), raise_server_exceptions=False)
    assert client.get("/readiness").status_code == 200
    payload = {"message": "hello", "stream": False} if agent_dir == "langgraph" else {"input": "hello"}
    response = client.post("/invocations", json=payload)
    assert response.status_code in {200, 400, 500} and response.json()


@pytest.mark.parametrize("agent_dir", ["maf", "langgraph"])
def test_host_construction_does_no_network_io(offline_env, monkeypatch, agent_dir):
    import socket

    def refuse(*args, **kwargs):
        raise AssertionError("agent construction attempted network I/O")

    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)
    module = _load(agent_dir)
    assert module.build_host("responses") is not None


@pytest.mark.parametrize("agent_dir", ["maf", "langgraph"])
def test_invalid_protocol_is_rejected(offline_env, agent_dir):
    module = _load(agent_dir)
    with pytest.raises(RuntimeError, match="HOSTED_PROTOCOL"):
        module.build_host("grpc")