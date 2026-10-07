from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

import httpx
from azure.identity import DefaultAzureCredential

ROOT = Path(__file__).resolve().parents[1]


def traceparent() -> str:
    return f"00-{uuid.uuid4().hex}-{uuid.uuid4().hex[:16]}-01"


def mcp_request(method: str, params: dict[str, Any] | None = None, request_id: int = 1) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}


def load_ids(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def key_from_key_vault(vault_uri: str, secret_name: str) -> str:
    from azure.keyvault.secrets import SecretClient

    client = SecretClient(vault_url=vault_uri, credential=DefaultAzureCredential())
    secret = client.get_secret(secret_name)
    if not secret.value:
        raise RuntimeError(f"Secret {secret_name!r} in {vault_uri} is empty.")
    return secret.value


def cli_token(scope: str) -> str:
    resource = scope[: -len("/.default")] if scope.endswith("/.default") else scope
    tenant = os.environ.get("AZURE_TENANT_ID")
    result = subprocess.run(
        ["az", "account", "get-access-token", *(["--tenant", tenant] if tenant else []), "--resource", resource, "--query", "accessToken", "-o", "tsv"],
        check=True,
        capture_output=True,
        text=True,
    )
    token = result.stdout.strip()
    if not token:
        raise RuntimeError(f"az returned an empty access token for {resource}")
    return token


def resolve_target(args: argparse.Namespace, ids: dict[str, Any]) -> tuple[str, str, dict[str, str]]:
    tp = traceparent()
    if args.target == "aigateway":
        gateway_url = args.gateway_url or ids.get("aigwGatewayUrl")
        catalog_url = args.catalog_mcp_url or ids.get("aigwMcpCatalogUrl") or (f"{gateway_url.rstrip('/')}/default/toolservers/catalog-mcp/mcp" if gateway_url else "")
        records_url = args.records_mcp_url or ids.get("aigwMcpRecordsUrl") or (f"{gateway_url.rstrip('/')}/default/toolservers/records/mcp" if gateway_url else "")
        llm_url = args.llm_url or (f"{gateway_url.rstrip('/')}/default/models/openai/v1/responses" if gateway_url else "")
        key = args.aigw_key or (os.environ.get(args.aigw_key_env) if args.aigw_key_env else None)
        if not key and ids.get("keyVaultUri"):
            key = key_from_key_vault(ids["keyVaultUri"], args.aigw_secret_name or ids.get("aigwRuntimeKeySecretName") or "aigw-runtime-key")
        if not key:
            raise SystemExit("--aigw-key, --aigw-key-env, or ids.keyVaultUri + secret name is required for --target aigateway")
        return llm_url, json.dumps({"catalog": catalog_url, "records": records_url}), {"api-key": key, "traceparent": tp, "Content-Type": "application/json"}

    gateway_url = args.gateway_url or ids.get("apimGatewayUrl")
    llm_path = (args.llm_api_path or ids.get("llmApiPath") or "llm").strip("/")
    llm_url = args.llm_url or (f"{gateway_url.rstrip('/')}/{llm_path}/openai/v1/responses" if gateway_url else "")
    catalog_url = args.catalog_mcp_url or ids.get("mcpCatalogUrl")
    records_url = args.records_mcp_url or ids.get("mcpRecordsUrl")
    scope = args.scope or "https://cognitiveservices.azure.com/.default"
    if not llm_url or not catalog_url or not records_url or not scope:
        raise SystemExit("--llm-url, --catalog-mcp-url, --records-mcp-url, and --scope are required unless --ids provides APIM values")
    try:
        token = DefaultAzureCredential().get_token(scope).token
    except Exception:
        token = cli_token(scope)
    headers = {"Authorization": f"Bearer {token}", "traceparent": tp, "Content-Type": "application/json"}
    if args.subscription_key:
        headers["api-key"] = args.subscription_key
    return llm_url, json.dumps({"catalog": catalog_url, "records": records_url}), headers


def check_mcp(name: str, url: str, headers: dict[str, str], call_tool: str) -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    init = httpx.post(url, json=mcp_request("initialize"), headers=headers, timeout=45)
    checks.append((f"{name} MCP initialize", 200 <= init.status_code < 300, str(init.status_code)))
    mcp_headers = dict(headers)
    if init.headers.get("mcp-session-id"):
        mcp_headers["mcp-session-id"] = init.headers["mcp-session-id"]
    tools = httpx.post(url, json=mcp_request("tools/list", request_id=2), headers=mcp_headers, timeout=45)
    checks.append((f"{name} MCP tools/list", 200 <= tools.status_code < 300, str(tools.status_code)))
    call = httpx.post(url, json=mcp_request("tools/call", {"name": call_tool, "arguments": {}}, 3), headers=mcp_headers, timeout=45)
    checks.append((f"{name} MCP tools/call", 200 <= call.status_code < 300, str(call.status_code)))
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=["apimv2", "aigateway"], default="apimv2")
    parser.add_argument("--ids", default=str(ROOT / "demo-ids.local.json"))
    parser.add_argument("--gateway-url")
    parser.add_argument("--llm-url")
    parser.add_argument("--llm-api-path")
    parser.add_argument("--catalog-mcp-url")
    parser.add_argument("--records-mcp-url")
    parser.add_argument("--scope")
    parser.add_argument("--subscription-key")
    parser.add_argument("--aigw-key")
    parser.add_argument("--aigw-key-env", default="AIGW_RUNTIME_KEY")
    parser.add_argument("--aigw-secret-name")
    parser.add_argument("--catalog-tool")
    parser.add_argument("--records-tool")
    parser.add_argument("--assert-401", action="store_true")
    parser.add_argument("--probe-429", action="store_true")
    parser.add_argument("--max-429-attempts", type=int, default=240)
    args = parser.parse_args()
    # The AI Gateway tier prefixes each tool with its tool-server name; APIM exposes the backend names.
    default_catalog, default_records = ("catalog_list_items", "records_list_records") if args.target == "aigateway" else ("list_items", "list_records")
    args.catalog_tool = args.catalog_tool or default_catalog
    args.records_tool = args.records_tool or default_records

    ids = load_ids(Path(args.ids))
    llm_url, mcp_json, headers = resolve_target(args, ids)
    mcp_urls = json.loads(mcp_json)
    checks: list[tuple[str, bool, str]] = []

    if args.assert_401:
        unauth = httpx.post(mcp_urls["catalog"], json=mcp_request("initialize"), headers={"traceparent": headers["traceparent"]}, timeout=30)
        checks.append(("401 without credential", unauth.status_code == 401, str(unauth.status_code)))

    llm = httpx.post(llm_url, json={"model": ids.get("modelDeploymentName", "chat"), "input": "Return a readiness check.", "stream": False}, headers=headers, timeout=60)
    checks.append(("LLM responses call", 200 <= llm.status_code < 300, str(llm.status_code)))
    checks.extend(check_mcp("catalog", mcp_urls["catalog"], headers, args.catalog_tool))
    checks.extend(check_mcp("records", mcp_urls["records"], headers, args.records_tool))

    if args.probe_429:
        # Burst concurrently: sequential LLM calls are too slow to exceed a per-minute request limit.
        from concurrent.futures import ThreadPoolExecutor

        def one_probe(_: int) -> int:
            try:
                return httpx.post(llm_url, json={"model": ids.get("modelDeploymentName", "chat"), "input": "ok", "max_output_tokens": 16, "stream": False}, headers=headers, timeout=60).status_code
            except httpx.HTTPError:
                return 0

        with ThreadPoolExecutor(max_workers=24) as pool:
            codes = list(pool.map(one_probe, range(args.max_429_attempts)))
        status = "observed" if 429 in codes else "not_observed"
        checks.append(("429 probe", status == "observed", f"{status} (requests={len(codes)}, 429s={codes.count(429)}, 2xx={sum(1 for c in codes if 200 <= c < 300)})"))

    print(json.dumps({"target": args.target, "traceparent": headers["traceparent"], "trace_id": headers["traceparent"].split("-")[1], "checks": [{"name": n, "passed": p, "detail": d} for n, p, d in checks]}, indent=2))
    return 0 if all(passed for _, passed, _ in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
