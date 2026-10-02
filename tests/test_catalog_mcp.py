
from fastapi.testclient import TestClient
from conftest import ROOT, load_module

def test_catalog_mcp_handshake_and_tool_call(monkeypatch):
    monkeypatch.setenv("DOMAIN_PROFILE","manufacturing-field-ops"); module=load_module("catalog_server_test", ROOT/"src"/"catalog-mcp"/"server.py"); client=TestClient(module.app)
    assert client.get("/healthz").json()["status"]=="ok"
    init=client.post("/mcp",json={"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}); assert init.status_code==200; assert init.headers.get("mcp-session-id")
    tools=client.post("/mcp",json={"jsonrpc":"2.0","id":2,"method":"tools/list"}).json()["result"]["tools"]
    assert {t["name"] for t in tools}=={"list_items","search_items","get_item","check_availability","check_availability_batch"}
    call=client.post("/mcp",headers={"traceparent":"00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-bbbbbbbbbbbbbbbb-01","x-gw-agent-appid":"agent-app"},json={"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"check_availability","arguments":{"item_id":"PRT-100","quantity":1}}}).json()
    assert call["result"]["structuredContent"]["can_fulfill"] is True
