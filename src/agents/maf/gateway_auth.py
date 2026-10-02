from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Mapping

from azure.identity import DefaultAzureCredential

FORBIDDEN_OUTBOUND_PREFIX = "x-gw-"


def make_traceparent(existing: str | None = None) -> str:
    if existing and len(existing.split("-")) == 4:
        return existing
    return f"00-{uuid.uuid4().hex}-{uuid.uuid4().hex[:16]}-01"


def strip_gateway_headers(headers: Mapping[str, str] | None) -> dict[str, str]:
    return {key: value for key, value in dict(headers or {}).items() if not key.lower().startswith(FORBIDDEN_OUTBOUND_PREFIX)}


def _env(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return default


def _trim(value: str | None) -> str:
    return (value or "").strip().strip("/")


class TokenProvider:
    def __init__(self, audience: str | None = None) -> None:
        self.audience = audience or os.environ.get("GATEWAY_AUDIENCE")
        self._credential: DefaultAzureCredential | None = None

    def _scope(self) -> str:
        if not self.audience:
            raise RuntimeError("GATEWAY_AUDIENCE is required for APIM gateway authentication.")
        return self.audience if self.audience.endswith("/.default") else f"{self.audience}/.default"

    def __call__(self) -> str:
        if self._credential is None:
            self._credential = DefaultAzureCredential()
        return self._credential.get_token(self._scope()).token

    async def async_token(self) -> str:
        return self()


def _read_secret_from_key_vault(vault_uri: str, secret_name: str) -> str:
    from azure.keyvault.secrets import SecretClient

    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=vault_uri, credential=credential)
    secret = client.get_secret(secret_name)
    if not secret.value:
        raise RuntimeError(f"Key Vault secret {secret_name!r} is empty.")
    return secret.value


def get_aigateway_runtime_key() -> str:
    fallback = os.environ.get("AIGW_RUNTIME_KEY")
    vault_uri = os.environ.get("KEY_VAULT_URI")
    secret_name = os.environ.get("AIGW_RUNTIME_KEY_SECRET_NAME")
    if vault_uri and secret_name:
        return _read_secret_from_key_vault(vault_uri, secret_name)
    if fallback:
        return fallback
    raise RuntimeError("AIGW_RUNTIME_KEY or KEY_VAULT_URI + AIGW_RUNTIME_KEY_SECRET_NAME is required for AI Gateway.")


@dataclass(frozen=True)
class GatewaySelection:
    target: str
    model_base_url: str
    model_deployment: str
    catalog_mcp_url: str
    records_mcp_url: str
    default_headers: dict[str, str]
    api_key: str | TokenProvider

    @property
    def model_base_url_with_slash(self) -> str:
        return self.model_base_url.rstrip("/") + "/"


def resolve_gateway(target: str | None = None) -> GatewaySelection:
    selected = (target or os.environ.get("DD_AGENT_DEFAULT_GATEWAY") or os.environ.get("AGENT_DEFAULT_GATEWAY") or "apimv2").lower()
    model_deployment = _env("MODEL_DEPLOYMENT_NAME", "AZURE_AI_MODEL_DEPLOYMENT_NAME", "FOUNDRY_MODEL_NAME", default="chat") or "chat"
    if selected == "aigateway":
        gateway_url = _env("AIGW_GATEWAY_URL")
        if not gateway_url:
            raise RuntimeError("AIGW_GATEWAY_URL is required when DD_AGENT_DEFAULT_GATEWAY=aigateway.")
        key = get_aigateway_runtime_key()
        base = f"{gateway_url.rstrip('/')}/default/models/openai/v1"
        return GatewaySelection(
            target="aigateway",
            model_base_url=base,
            model_deployment=model_deployment,
            catalog_mcp_url=_env("AIGW_MCP_CATALOG_URL", default=f"{gateway_url.rstrip('/')}/default/toolservers/catalog-mcp/mcp") or "",
            records_mcp_url=_env("AIGW_MCP_RECORDS_URL", default=f"{gateway_url.rstrip('/')}/default/toolservers/records/mcp") or "",
            default_headers={"api-key": key},
            api_key="unused",
        )
    if selected != "apimv2":
        raise RuntimeError("DD_AGENT_DEFAULT_GATEWAY must be 'apimv2' or 'aigateway'.")
    apim_url = _env("APIM_GATEWAY_URL")
    if not apim_url:
        return GatewaySelection(
            target="apimv2",
            model_base_url="http://offline.local/openai/v1",
            model_deployment=model_deployment,
            catalog_mcp_url=os.environ.get("MCP_CATALOG_URL", ""),
            records_mcp_url=os.environ.get("MCP_RECORDS_URL", ""),
            default_headers={},
            api_key="offline",
        )
    token_provider = TokenProvider()
    llm_path = _trim(os.environ.get("LLM_API_PATH") or "llm")
    return GatewaySelection(
        target="apimv2",
        model_base_url=f"{apim_url.rstrip('/')}/{llm_path}/openai/v1",
        model_deployment=model_deployment,
        catalog_mcp_url=os.environ.get("MCP_CATALOG_URL", ""),
        records_mcp_url=os.environ.get("MCP_RECORDS_URL", ""),
        default_headers={},
        api_key=token_provider,
    )


def gateway_headers(selection: GatewaySelection, traceparent: str | None = None) -> dict[str, str]:
    headers = strip_gateway_headers(selection.default_headers)
    if selection.target == "apimv2" and isinstance(selection.api_key, TokenProvider) and os.environ.get("APIM_GATEWAY_URL"):
        headers["Authorization"] = f"Bearer {selection.api_key()}"
    if traceparent:
        headers["traceparent"] = traceparent
    return headers
