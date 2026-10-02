
import filecmp
from conftest import ROOT, load_module

def test_traceparent_created_and_gateway_headers_stripped():
    module=load_module("gateway_client_test", ROOT/"src"/"agents"/"maf"/"gateway_auth.py"); tp=module.make_traceparent(); assert tp.startswith("00-"); assert len(tp.split("-"))==4
    headers=module.strip_gateway_headers({"x-gw-user-oid":"bad","traceparent":tp,"X-GW-Agent-Oid":"bad","api-key":"meter"}); low={k.lower() for k in headers}
    assert "x-gw-user-oid" not in low and "x-gw-agent-oid" not in low; assert headers["traceparent"]==tp

def test_agent_gateway_auth_helpers_are_byte_identical():
    assert filecmp.cmp(ROOT/"src"/"agents"/"maf"/"gateway_auth.py", ROOT/"src"/"agents"/"langgraph"/"gateway_auth.py", shallow=False)

def test_gateway_selection_headers(monkeypatch):
    module=load_module("gateway_selection_test", ROOT/"src"/"agents"/"maf"/"gateway_auth.py")
    monkeypatch.setenv("AGENT_DEFAULT_GATEWAY","aigateway"); monkeypatch.setenv("AIGW_GATEWAY_URL","https://example.azure-api.net"); monkeypatch.setenv("AIGW_RUNTIME_KEY","local-key")
    selected=module.resolve_gateway(); assert selected.target=="aigateway"; assert selected.model_base_url=="https://example.azure-api.net/default/models/openai/v1"
    headers=module.gateway_headers(selected,"00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-bbbbbbbbbbbbbbbb-01"); assert headers["api-key"]=="local-key"; assert not any(k.lower().startswith("x-gw-") for k in headers)
    monkeypatch.setenv("AGENT_DEFAULT_GATEWAY","apimv2"); monkeypatch.setenv("APIM_GATEWAY_URL","https://apim.azure-api.net"); monkeypatch.setenv("LLM_API_PATH","llm"); monkeypatch.setenv("GATEWAY_AUDIENCE","api://demo")
    selected=module.resolve_gateway(); assert selected.model_base_url=="https://apim.azure-api.net/llm/openai/v1"
