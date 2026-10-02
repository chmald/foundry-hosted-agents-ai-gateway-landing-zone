from __future__ import annotations

import argparse
import json
import uuid

import httpx
from azure.identity import DeviceCodeCredential, InteractiveBrowserCredential


def traceparent() -> str:
    return f"00-{uuid.uuid4().hex}-{uuid.uuid4().hex[:16]}-01"


def endpoint_from_project(project_endpoint: str, agent: str) -> str:
    agent_name = "agent-maf" if agent == "maf" else "agent-langgraph"
    return f"{project_endpoint.rstrip('/')}/agents/{agent_name}/endpoint/protocols/openai/responses?api-version=v1"


def main() -> int:
    parser = argparse.ArgumentParser(description="Invoke a Foundry hosted agent as a signed-in user.")
    parser.add_argument("--endpoint")
    parser.add_argument("--project-endpoint")
    parser.add_argument("--agent", choices=["maf", "langgraph"], default="maf")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--prompt", default="Check governed tool readiness.")
    parser.add_argument("--device-code", action="store_true")
    args = parser.parse_args()

    endpoint = args.endpoint or (endpoint_from_project(args.project_endpoint, args.agent) if args.project_endpoint else None)
    if not endpoint:
        raise SystemExit("Provide --endpoint or --project-endpoint.")

    credential = DeviceCodeCredential(tenant_id=args.tenant_id, client_id=args.client_id) if args.device_code else InteractiveBrowserCredential(tenant_id=args.tenant_id, client_id=args.client_id)
    token = credential.get_token(args.scope).token
    tp = traceparent()
    response = httpx.post(endpoint, headers={"Authorization": f"Bearer {token}", "traceparent": tp}, json={"input": args.prompt, "stream": False}, timeout=60)
    response.raise_for_status()
    print(
        json.dumps(
            {
                "agent": args.agent,
                "endpoint": endpoint,
                "traceparent": tp,
                "trace_id": tp.split("-")[1],
                "response": response.json(),
                "verified": "request shape and trace id printed",
                "to_verify": "audit row contains human_principal and agent_principal after deployment",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
