
from __future__ import annotations

import json, os, signal, uuid
from pathlib import Path
from typing import Any, Mapping
import uvicorn
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from audit import AuditTimer, build_audit_record, configure_azure_monitor_if_available, configure_logging, emit_audit_record

PROTOCOL_VERSION="2025-06-18"; SERVICE_NAME="catalog-mcp"; DEFAULT_PROFILE="manufacturing-field-ops"; SESSION_ID_HEADER="mcp-session-id"
ROOT=Path(__file__).resolve().parents[2]

def load_profile() -> dict[str, Any]:
    name=os.environ.get("DOMAIN_PROFILE") or DEFAULT_PROFILE; path=ROOT/"config"/"profiles"/f"{name}.json"
    if not path.exists(): raise RuntimeError(f"Profile not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))

def load_items(profile: Mapping[str, Any]) -> list[dict[str, Any]]:
    return json.loads((ROOT/profile["seedData"]["items"]).read_text(encoding="utf-8"))

PROFILE=load_profile(); ITEMS=load_items(PROFILE); ITEMS_BY_ID={i["id"].upper():i for i in ITEMS}; LABELS=PROFILE["labels"]
configure_logging(); configure_azure_monitor_if_available(); app=FastAPI(title="Catalog MCP", version="1.0.0")

def availability_status(item: Mapping[str, Any]) -> str:
    q=int(item.get("available_quantity",0)); m=int(item.get("min_quantity",0))
    return "unavailable" if q<=0 else "limited" if q<=m else "available"

def item_summary(item: Mapping[str, Any]) -> dict[str, Any]:
    return {"id":item["id"],"name":item["name"],"category":item.get("category"),"sku":item.get("sku"),"available_quantity":item.get("available_quantity"),"availability_status":availability_status(item),"location":item.get("location"),"supplier":item.get("supplier")}

def find_item(item_id: str) -> dict[str, Any]:
    item=ITEMS_BY_ID.get((item_id or "").upper())
    if item is None: raise ValueError(f"Unknown {LABELS['item']} id: {item_id}")
    return item

def list_items(category: str|None=None) -> dict[str, Any]:
    n=category.strip().lower() if category else None
    matches=[item_summary(i) for i in ITEMS if n is None or i.get("category","").lower()==n]
    return {"count":len(matches),"category":category,LABELS["items"]:matches}

def search_items(query: str) -> dict[str, Any]:
    n=query.strip().lower()
    if not n: raise ValueError("query must not be empty")
    fields=("id","name","description","category","sku","location","supplier")
    matches=[item_summary(i) for i in ITEMS if any(n in str(i.get(f,"")).lower() for f in fields)]
    return {"query":query,"count":len(matches),LABELS["items"]:matches}

def get_item(item_id: str) -> dict[str, Any]:
    item=dict(find_item(item_id)); item["availability_status"]=availability_status(item); return item

def check_availability(item_id: str, quantity: int=1) -> dict[str, Any]:
    item=find_item(item_id); available=int(item.get("available_quantity",0)); requested=max(int(quantity or 1),1)
    return {"id":item["id"],"name":item["name"],"requested_quantity":requested,"available_quantity":available,"availability_status":availability_status(item),"can_fulfill":available>=requested,"location":item.get("location")}

def check_availability_batch(item_ids: list[str], quantity: int=1) -> dict[str, Any]:
    results=[]
    for item_id in item_ids:
        try: results.append(check_availability(item_id, quantity))
        except ValueError as exc: results.append({"id":str(item_id).upper(),"error":str(exc),"can_fulfill":False})
    return {"count":len(results),"results":results}

TOOL_HANDLERS={"list_items":lambda a:list_items(a.get("category")),"search_items":lambda a:search_items(str(a.get("query",""))),"get_item":lambda a:get_item(str(a.get("item_id") or a.get("id") or "")),"check_availability":lambda a:check_availability(str(a.get("item_id") or a.get("id") or ""), int(a.get("quantity",1) or 1)),"check_availability_batch":lambda a:check_availability_batch(list(a.get("item_ids") or a.get("ids") or []), int(a.get("quantity",1) or 1))}

def tool_definitions() -> list[dict[str, Any]]:
    d=PROFILE["catalogTools"]
    return [
      {"name":"list_items","description":d["list_items"],"inputSchema":{"type":"object","properties":{"category":{"type":"string"}}}},
      {"name":"search_items","description":d["search_items"],"inputSchema":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}},
      {"name":"get_item","description":d["get_item"],"inputSchema":{"type":"object","properties":{"item_id":{"type":"string"}},"required":["item_id"]}},
      {"name":"check_availability","description":d["check_availability"],"inputSchema":{"type":"object","properties":{"item_id":{"type":"string"},"quantity":{"type":"integer","minimum":1}},"required":["item_id"]}},
      {"name":"check_availability_batch","description":d["check_availability_batch"],"inputSchema":{"type":"object","properties":{"item_ids":{"type":"array","items":{"type":"string"}},"quantity":{"type":"integer","minimum":1}},"required":["item_ids"]}}]

def jsonrpc_result(i: Any, result: Any) -> dict[str, Any]: return {"jsonrpc":"2.0","id":i,"result":result}
def jsonrpc_error(i: Any, code: int, message: str) -> dict[str, Any]: return {"jsonrpc":"2.0","id":i,"error":{"code":code,"message":message}}

@app.get("/healthz")
def healthz(): return {"status":"ok","service":SERVICE_NAME,"domain_profile":PROFILE["profileName"],"items_loaded":len(ITEMS)}

@app.post("/mcp")
async def mcp(request: Request) -> Response:
    headers=dict(request.headers); message={}; tool="unknown"; decision="allowed"; reason="ok"; status_code=200
    with AuditTimer() as timer:
      try: message=await request.json()
      except Exception as exc:
        payload=jsonrpc_error(None,-32700,f"Parse error: {exc}"); tool="parse"; decision="denied"; reason="invalid_json"
      else:
        method=message.get("method") if isinstance(message,dict) else None; request_id=message.get("id") if isinstance(message,dict) else None; tool=method or "unknown"
        if not isinstance(message,dict) or message.get("jsonrpc")!="2.0": payload=jsonrpc_error(request_id,-32602,"Invalid JSON-RPC 2.0 request envelope"); decision="denied"; reason="invalid_envelope"
        elif method=="initialize": payload=jsonrpc_result(request_id,{"protocolVersion":PROTOCOL_VERSION,"capabilities":{"tools":{}},"serverInfo":{"name":SERVICE_NAME,"version":"1.0.0"}})
        elif method=="notifications/initialized": return Response(status_code=status.HTTP_202_ACCEPTED)
        elif method=="tools/list": payload=jsonrpc_result(request_id,{"tools":tool_definitions()})
        elif method=="tools/call":
          params=message.get("params") or {}; name=params.get("name"); args=params.get("arguments") or {}; tool=str(name); handler=TOOL_HANDLERS.get(name)
          if handler is None: payload=jsonrpc_error(request_id,-32602,f"Unknown tool: {name}"); decision="denied"; reason="tool_not_allowlisted"
          else:
            try:
              result=handler(args); payload=jsonrpc_result(request_id,{"content":[{"type":"text","text":json.dumps(result)}],"structuredContent":result,"isError":False})
            except Exception as exc: payload=jsonrpc_error(request_id,-32603,str(exc)); decision="denied"; reason="tool_error"
        else: payload=jsonrpc_error(request_id,-32601,f"Method not found: {method}"); decision="denied"; reason="method_not_found"
    emit_audit_record(build_audit_record(service=SERVICE_NAME, tool=tool, operation=str(message.get("method","unknown")) if isinstance(message,dict) else "unknown", decision=decision, reason=reason, headers=headers, domain_profile=PROFILE["profileName"], latency_ms=timer.elapsed_ms, status_code=status_code))
    response=JSONResponse(payload, status_code=status_code)
    if isinstance(message,dict) and message.get("method")=="initialize": response.headers[SESSION_ID_HEADER]=uuid.uuid4().hex
    return response

if __name__=="__main__":
    port=int(os.environ.get("PORT","8080")); config=uvicorn.Config(app,host="0.0.0.0",port=port,log_level="info"); server=uvicorn.Server(config); signal.signal(signal.SIGTERM, lambda *_: setattr(server,"should_exit",True)); server.run()
