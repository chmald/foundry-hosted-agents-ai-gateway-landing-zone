from __future__ import annotations

import json
import logging
import shutil
import subprocess

import os
import re

import pytest
from conftest import ROOT, load_module

HOOKS = ROOT / "infra" / "hooks"
AGENTS = ("agent-maf", "agent-langgraph")
SECRET = "super-secret-runtime-key"
PWSH = shutil.which("pwsh")


def _gateway(agent_dir: str = "maf"):
    return load_module(f"gateway_auth_{agent_dir}", ROOT / "src" / "agents" / agent_dir / "gateway_auth.py")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ("AIGW_KEY_DELIVERY", "AIGW_RUNTIME_KEY", "KEY_VAULT_URI", "AIGW_RUNTIME_KEY_SECRET_NAME"):
        monkeypatch.delenv(name, raising=False)


def _vault_env(monkeypatch):
    monkeypatch.setenv("KEY_VAULT_URI", "https://kv.vault.azure.net/")
    monkeypatch.setenv("AIGW_RUNTIME_KEY_SECRET_NAME", "aigw-runtime-key")


@pytest.mark.parametrize("agent_dir", ["maf", "langgraph"])
def test_default_mode_reads_key_vault_and_ignores_env_key(monkeypatch, caplog, agent_dir):
    module = _gateway(agent_dir)
    _vault_env(monkeypatch)
    monkeypatch.setenv("AIGW_RUNTIME_KEY", "env-key")
    monkeypatch.setattr(module, "_read_secret_from_key_vault", lambda uri, name: "vault-key")
    assert module.key_delivery_mode() == "keyvault"
    assert module.get_aigateway_runtime_key() == "vault-key"
    assert "aigw_runtime_key_source" not in caplog.text


@pytest.mark.parametrize("agent_dir", ["maf", "langgraph"])
def test_env_mode_uses_env_key_and_warns_without_leaking_it(monkeypatch, caplog, agent_dir):
    module = _gateway(agent_dir)
    monkeypatch.setenv("AIGW_KEY_DELIVERY", "env")
    monkeypatch.setenv("AIGW_RUNTIME_KEY", SECRET)
    monkeypatch.setattr(module, "_read_secret_from_key_vault", lambda *a: pytest.fail("Key Vault must not be read in env mode"))
    with caplog.at_level(logging.WARNING, logger="agent_host"):
        assert module.get_aigateway_runtime_key() == SECRET
    records = [r for r in caplog.records if "aigw_runtime_key_source" in r.getMessage()]
    assert records and records[0].levelno == logging.WARNING and "reason=explicit_opt_in" in records[0].getMessage()
    assert SECRET not in caplog.text


def test_env_mode_without_env_key_fails(monkeypatch):
    module = _gateway()
    monkeypatch.setenv("AIGW_KEY_DELIVERY", "env")
    with pytest.raises(RuntimeError, match="AIGW_RUNTIME_KEY"):
        module.get_aigateway_runtime_key()


def test_key_vault_failure_falls_back_to_env_key_with_warning(monkeypatch, caplog):
    module = _gateway()
    _vault_env(monkeypatch)
    monkeypatch.setenv("AIGW_RUNTIME_KEY", SECRET)

    def boom(uri, name):
        raise PermissionError("ForbiddenByConnection")

    monkeypatch.setattr(module, "_read_secret_from_key_vault", boom)
    with caplog.at_level(logging.WARNING, logger="agent_host"):
        assert module.get_aigateway_runtime_key() == SECRET
    messages = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any("reason=key_vault_read_failed" in m and "PermissionError" in m for m in messages)
    assert SECRET not in caplog.text


def test_key_vault_failure_without_env_key_raises(monkeypatch):
    module = _gateway()
    _vault_env(monkeypatch)

    def boom(uri, name):
        raise PermissionError("ForbiddenByConnection")

    monkeypatch.setattr(module, "_read_secret_from_key_vault", boom)
    with pytest.raises(PermissionError):
        module.get_aigateway_runtime_key()


def test_keyvault_mode_requires_vault_settings_and_invalid_mode_rejected(monkeypatch):
    module = _gateway()
    with pytest.raises(RuntimeError, match="KEY_VAULT_URI"):
        module.get_aigateway_runtime_key()
    monkeypatch.setenv("AIGW_KEY_DELIVERY", "plaintext")
    with pytest.raises(RuntimeError, match="AIGW_KEY_DELIVERY"):
        module.key_delivery_mode()


def test_gateway_auth_helper_is_byte_identical():
    assert (ROOT / "src/agents/maf/gateway_auth.py").read_bytes() == (ROOT / "src/agents/langgraph/gateway_auth.py").read_bytes()


def _service_block(service: str) -> str:
    text = (ROOT / "azure.yaml").read_text(encoding="utf-8")
    match = re.search(rf"(?ms)^  {re.escape(service)}:\n(.*?)(?=^  \S|\Z)", text)
    assert match, f"service {service} not found in azure.yaml"
    return match.group(1)


@pytest.mark.parametrize("service", AGENTS)
def test_azure_yaml_has_service_postdeploy_hook_and_key_delivery_env(service):
    block = _service_block(service)
    hook = re.search(r"(?ms)^    hooks:\n      postdeploy:\n(.*?)(?=^    \S|\Z)", block)
    assert hook, "service-level postdeploy hook missing"
    body = hook.group(1)
    assert "shell: pwsh" in body and "continueOnError: false" in body
    assert "postdeploy-agents.ps1" in body and f"-AgentName {service}" in body
    assert "AIGW_KEY_DELIVERY: ${AIGW_KEY_DELIVERY}" in block
    assert "AIGW_RUNTIME_KEY: ${AIGW_RUNTIME_KEY}" in block
    assert (ROOT / "infra" / "hooks" / "postdeploy-agents.ps1").is_file()

@pytest.mark.skipif(PWSH is None, reason="pwsh not installed")
def test_all_hook_scripts_parse():
    script = (
        "$failed = $false; foreach ($f in Get-ChildItem -LiteralPath $env:HOOKS_DIR -Filter *.ps1) { "
        "$e = $null; [void][System.Management.Automation.Language.Parser]::ParseFile($f.FullName, [ref]$null, [ref]$e); "
        "if ($e) { $failed = $true; $e | ForEach-Object { \"$($f.Name): $($_.Message)\" } } }; if ($failed) { exit 1 }"
    )
    result = subprocess.run([PWSH, "-NoProfile", "-Command", script], capture_output=True, text=True, env={**os.environ, "HOOKS_DIR": str(HOOKS)})
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.skipif(PWSH is None, reason="pwsh not installed")
def test_agent_show_json_parsing_helpers():
    payload = {"name": "agent-maf", "instance_identity": {"principal_id": "11111111-1111-1111-1111-111111111111", "client_id": "c"}, "blueprint": {"principal_id": "22222222-2222-2222-2222-222222222222"}}
    noisy = "WARNING: update available\n" + json.dumps(payload) + "\ntrailing banner"
    script = (
        ". (Join-Path $env:HOOKS_DIR 'common.ps1'); "
        "$obj = ConvertFrom-MixedJsonOutput -Text $env:NOISY_JSON; "
        "Get-InstancePrincipalIdFromAgentJson -Agent $obj"
    )
    result = subprocess.run([PWSH, "-NoProfile", "-Command", script], capture_output=True, text=True, env={**os.environ, "HOOKS_DIR": str(HOOKS), "NOISY_JSON": noisy})
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip().splitlines()[-1] == "11111111-1111-1111-1111-111111111111"
