
import filecmp, json
from conftest import ROOT, load_module

def test_audit_modules_identical_and_schema_has_no_token_leak():
    catalog=ROOT/"src"/"catalog-mcp"/"audit.py"; records=ROOT/"src"/"records-api"/"audit.py"; assert filecmp.cmp(catalog,records,shallow=False)
    module=load_module("audit_test", catalog); record=module.build_audit_record(service="svc",tool="tool",operation="op",decision="allowed",reason="ok",headers={"traceparent":"00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-bbbbbbbbbbbbbbbb-01","authorization":"Bearer secret","x-gw-agent-appid":"app","x-gw-agent-oid":"oid","x-gw-user-oid":"user","x-gw-request-id":"req"},domain_profile="manufacturing-field-ops",latency_ms=12.345,status_code=200)
    for key in ["timestamp","trace_id","span_id","traceparent","service","tool","operation","decision","reason","human_principal","agent_principal","gateway_request_id","gateway","caller","domain_profile","latency_ms","status_code"]: assert key in record
    assert "secret" not in json.dumps(record).lower(); assert record["human_principal"]["oid"]=="user"; assert record["agent_principal"]["appid"]=="app"; assert record["gateway"]=="apimv2"; assert record["caller"] is None
    aigw=module.build_audit_record(service="svc",tool="tool",operation="op",decision="allowed",reason="ok",headers={"traceparent":"00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-bbbbbbbbbbbbbbbb-01","x-gw-caller":"aigw-runtime-key:agents"},domain_profile="manufacturing-field-ops",latency_ms=1,status_code=200)
    assert aigw["gateway"]=="aigateway"; assert aigw["caller"]=="aigw-runtime-key:agents"
