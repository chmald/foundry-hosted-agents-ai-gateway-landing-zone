"""Gateway selection and request authentication shared by both hosted agents.

Nothing here performs network I/O at import or while resolving a selection.
Tokens and Key Vault secrets are acquired lazily, cached, and refreshed on the
first outbound request, so the host's ``/readiness`` probe never depends on a
backend. This file is kept byte-identical in ``maf`` and ``langgraph``.
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Generator, Mapping

import httpx

FORBIDDEN_OUTBOUND_PREFIX = "x-gw-"
PLACEHOLDER_API_KEY = "gateway-managed"
TOKEN_REFRESH_SKEW_SECONDS = 300
SECRET_REFRESH_SECONDS = 900


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


def hosted_setting(name: str, default: str) -> str:
    """Read ``HOSTED_<name>``; the unprefixed ``AGENT_<name>`` is only a local-run fallback.

    Foundry reserves ``AGENT_*`` in the deployed container environment, so the
    deployed configuration always uses the ``HOSTED_*`` names.
    """
    return _env(f"HOSTED_{name}", f"AGENT_{name}", default=default) or default


def _azure_credential() -> Any:
    from azure.identity import DefaultAzureCredential, ManagedIdentityCredential

    if os.environ.get("FOUNDRY_HOSTING_ENVIRONMENT"):
        return ManagedIdentityCredential(client_id=os.environ.get("FOUNDRY_AGENT_INSTANCE_CLIENT_ID"))
    return DefaultAzureCredential()


class TokenProvider:
    """Cached bearer-token source for the APIM gateway audience."""

    def __init__(self, audience: str | None = None) -> None:
        self.audience = audience or os.environ.get("GATEWAY_AUDIENCE")
        self._credential: Any = None
        self._token: str | None = None
        self._expires_on = 0.0
        self._lock = threading.Lock()

    def _scope(self) -> str:
        if not self.audience:
            raise RuntimeError("GATEWAY_AUDIENCE is required for APIM gateway authentication.")
        return self.audience if self.audience.endswith("/.default") else f"{self.audience}/.default"

    def __call__(self) -> str:
        with self._lock:
            if self._token and self._expires_on - time.time() > TOKEN_REFRESH_SKEW_SECONDS:
                return self._token
            if self._credential is None:
                self._credential = _azure_credential()
            access = self._credential.get_token(self._scope())
            self._token, self._expires_on = access.token, float(access.expires_on)
            return self._token


def _read_secret_from_key_vault(vault_uri: str, secret_name: str) -> str:
    from azure.keyvault.secrets import SecretClient

    client = SecretClient(vault_url=vault_uri, credential=_azure_credential())
    secret = client.get_secret(secret_name)
    if not secret.value:
        raise RuntimeError(f"Key Vault secret {secret_name!r} is empty.")
    return secret.value


KEY_DELIVERY_KEYVAULT = "keyvault"
KEY_DELIVERY_ENV = "env"


def key_delivery_mode() -> str:
    """``keyvault`` (default) reads the runtime key from Key Vault; ``env`` is the explicit demo-only opt-in to ``AIGW_RUNTIME_KEY``."""
    mode = (os.environ.get("AIGW_KEY_DELIVERY") or KEY_DELIVERY_KEYVAULT).strip().lower()
    if mode not in (KEY_DELIVERY_KEYVAULT, KEY_DELIVERY_ENV):
        raise RuntimeError(f"AIGW_KEY_DELIVERY must be '{KEY_DELIVERY_KEYVAULT}' or '{KEY_DELIVERY_ENV}', got {mode!r}.")
    return mode


def get_aigateway_runtime_key() -> str:
    """Resolve the AI Gateway runtime key. The key value is never logged."""
    log = logging.getLogger("agent_host")
    env_key = os.environ.get("AIGW_RUNTIME_KEY") or None
    if key_delivery_mode() == KEY_DELIVERY_ENV:
        if not env_key:
            raise RuntimeError("AIGW_KEY_DELIVERY=env requires AIGW_RUNTIME_KEY to be set.")
        log.warning("aigw_runtime_key_source source=env reason=explicit_opt_in delivery=env")
        return env_key
    vault_uri = os.environ.get("KEY_VAULT_URI")
    secret_name = os.environ.get("AIGW_RUNTIME_KEY_SECRET_NAME")
    if not (vault_uri and secret_name):
        raise RuntimeError("KEY_VAULT_URI and AIGW_RUNTIME_KEY_SECRET_NAME are required when AIGW_KEY_DELIVERY=keyvault (set AIGW_KEY_DELIVERY=env plus AIGW_RUNTIME_KEY for local runs).")
    try:
        return _read_secret_from_key_vault(vault_uri, secret_name)
    except Exception as exc:
        # Governance policy can force Key Vault public access off, which hosted agents (outside the VNet) cannot cross.
        if not env_key:
            raise
        log.warning(
            "aigw_runtime_key_source source=env reason=key_vault_read_failed delivery=keyvault secret=%s error=%s",
            secret_name,
            type(exc).__name__,
        )
        return env_key


class NoCredentials:
    def headers(self) -> dict[str, str]:
        return {}


class BearerCredentials:
    def __init__(self, provider: TokenProvider | None = None) -> None:
        self.provider = provider or TokenProvider()

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.provider()}"}


class ApiKeyCredentials:
    """AI Gateway runtime key, read from Key Vault on first use (``AIGW_RUNTIME_KEY`` only under ``AIGW_KEY_DELIVERY=env`` or when the read fails)."""

    def __init__(self) -> None:
        self._key: str | None = None
        self._loaded_at = 0.0
        self._lock = threading.Lock()

    def headers(self) -> dict[str, str]:
        with self._lock:
            if self._key is None or time.time() - self._loaded_at > SECRET_REFRESH_SECONDS:
                self._key, self._loaded_at = get_aigateway_runtime_key(), time.time()
            return {"api-key": self._key}


@dataclass(frozen=True)
class GatewaySelection:
    target: str
    model_base_url: str
    model_deployment: str
    catalog_mcp_url: str
    records_mcp_url: str
    credentials: NoCredentials | BearerCredentials | ApiKeyCredentials

    @property
    def model_base_url_with_slash(self) -> str:
        return self.model_base_url.rstrip("/") + "/"


def resolve_gateway(target: str | None = None) -> GatewaySelection:
    selected = (target or hosted_setting("DEFAULT_GATEWAY", "apimv2")).lower()
    model_deployment = _env("MODEL_DEPLOYMENT_NAME", "AZURE_AI_MODEL_DEPLOYMENT_NAME", "FOUNDRY_MODEL_NAME", default="chat") or "chat"
    if selected == "aigateway":
        gateway_url = _env("AIGW_GATEWAY_URL")
        if not gateway_url:
            raise RuntimeError("AIGW_GATEWAY_URL is required when HOSTED_DEFAULT_GATEWAY=aigateway.")
        root = gateway_url.rstrip("/")
        return GatewaySelection(
            target="aigateway",
            model_base_url=f"{root}/default/models/openai/v1",
            model_deployment=model_deployment,
            catalog_mcp_url=_env("AIGW_MCP_CATALOG_URL", default=f"{root}/default/toolservers/catalog-mcp/mcp") or "",
            records_mcp_url=_env("AIGW_MCP_RECORDS_URL", default=f"{root}/default/toolservers/records/mcp") or "",
            credentials=ApiKeyCredentials(),
        )
    if selected != "apimv2":
        raise RuntimeError("HOSTED_DEFAULT_GATEWAY must be 'apimv2' or 'aigateway'.")
    apim_url = _env("APIM_GATEWAY_URL")
    catalog = os.environ.get("MCP_CATALOG_URL", "")
    records = os.environ.get("MCP_RECORDS_URL", "")
    if not apim_url:
        return GatewaySelection("apimv2", "http://offline.local/openai/v1", model_deployment, catalog, records, NoCredentials())
    llm_path = _trim(os.environ.get("LLM_API_PATH") or "llm")
    return GatewaySelection("apimv2", f"{apim_url.rstrip('/')}/{llm_path}/openai/v1", model_deployment, catalog, records, BearerCredentials())


def gateway_headers(selection: GatewaySelection, traceparent: str | None = None) -> dict[str, str]:
    """Blocking helper that returns the auth headers for one outbound call."""
    headers = strip_gateway_headers(selection.credentials.headers())
    if traceparent:
        headers["traceparent"] = traceparent
    return headers


def _outbound_traceparent() -> str:
    from opentelemetry.propagate import inject

    carrier: dict[str, str] = {}
    inject(carrier)
    return carrier.get("traceparent") or make_traceparent()


class GatewayAuth(httpx.Auth):
    """Per-request auth for every outbound gateway call (model and MCP).

    Credentials are resolved when a request is sent, never when the client is
    built. ``traceparent`` follows the active span and falls back to a fresh one.
    """

    def __init__(self, selection: GatewaySelection) -> None:
        self.selection = selection

    def _apply(self, request: httpx.Request, auth_headers: Mapping[str, str]) -> None:
        for key in [key for key in request.headers if key.lower().startswith(FORBIDDEN_OUTBOUND_PREFIX)]:
            del request.headers[key]
        if "Authorization" not in auth_headers and request.headers.get("authorization") == f"Bearer {PLACEHOLDER_API_KEY}":
            del request.headers["authorization"]
        request.headers.update(auth_headers)
        request.headers["traceparent"] = _outbound_traceparent()

    def sync_auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        self._apply(request, strip_gateway_headers(self.selection.credentials.headers()))
        yield request

    async def async_auth_flow(self, request: httpx.Request):
        self._apply(request, strip_gateway_headers(await asyncio.to_thread(self.selection.credentials.headers)))
        yield request


def build_http_client(selection: GatewaySelection) -> httpx.AsyncClient:
    return httpx.AsyncClient(auth=GatewayAuth(selection), timeout=httpx.Timeout(60.0, connect=10.0))
