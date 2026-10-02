
import pytest
from fastapi.testclient import TestClient
from conftest import ROOT, load_module

@pytest.mark.parametrize("agent_dir,framework", [("maf","maf"),("langgraph","langgraph")])
def test_hosted_agent_contract(monkeypatch, agent_dir, framework):
    monkeypatch.setenv("DOMAIN_PROFILE","manufacturing-field-ops"); monkeypatch.delenv("APIM_GATEWAY_URL", raising=False); monkeypatch.setenv("AGENT_DEFAULT_GATEWAY","apimv2")
    module=load_module(f"{agent_dir}_main_test", ROOT/"src"/"agents"/agent_dir/"main.py"); client=TestClient(module.app)
    readiness=client.get("/readiness"); assert readiness.status_code==200; assert readiness.json()["status"]=="ok"
    assert readiness.json()["framework"]==framework
    responses=client.post("/responses",headers={"traceparent":"00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-bbbbbbbbbbbbbbbb-01"},json={"input":"Hello"}); assert responses.status_code==200
    body=responses.json(); assert body["object"]=="response"; assert body["output"][0]["type"]=="message"
    invocations=client.post("/invocations",json={"prompt":"Hello"}); assert invocations.status_code==200; assert "traceparent" in invocations.json()
