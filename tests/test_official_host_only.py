from __future__ import annotations

import re

import pytest
from conftest import ROOT

AGENTS = ["maf", "langgraph"]
MAIN_HOST_IMPORT = {
    "maf": "from agent_framework_foundry_hosting import",
    "langgraph": "from langchain_azure_ai.agents.hosting import",
}


def _agent_sources(agent_dir):
    folder = ROOT / "src" / "agents" / agent_dir
    return {p.name: p.read_text(encoding="utf-8") for p in [*folder.glob("*.py"), folder / "requirements.txt", folder / "Dockerfile", folder / "agent.yaml", folder / "agent.manifest.yaml"]}


def test_azure_yaml_has_no_fastapi_fallback_switch():
    text = (ROOT / "azure.yaml").read_text(encoding="utf-8")
    assert "FHAGL_USE_FASTAPI_FALLBACK" not in text and "FASTAPI" not in text.upper()


@pytest.mark.parametrize("agent_dir", AGENTS)
def test_agents_use_only_the_official_host(agent_dir):
    sources = _agent_sources(agent_dir)
    main = sources["main.py"]
    assert MAIN_HOST_IMPORT[agent_dir] in main and "InvocationsHostServer" in main and "ResponsesHostServer" in main
    for name, text in sources.items():
        assert "FHAGL_USE_FASTAPI_FALLBACK" not in text, name
        assert not re.search(r"^\s*(from|import)\s+fastapi", text, re.MULTILINE), name
    assert "fastapi" not in sources["requirements.txt"].lower()


@pytest.mark.parametrize("agent_dir", AGENTS)
def test_protocol_version_and_pins(agent_dir):
    sources = _agent_sources(agent_dir)
    for name in ("agent.yaml", "agent.manifest.yaml"):
        assert re.search(r"protocol: responses\s+version: 2\.0\.0", sources[name]), name
    for line in sources["requirements.txt"].splitlines():
        assert "==" in line, f"unpinned requirement: {line}"


def test_hosted_env_names_replace_dd_names():
    azure = (ROOT / "azure.yaml").read_text(encoding="utf-8")
    for name in ("HOSTED_DEFAULT_GATEWAY", "HOSTED_PROTOCOL", "HOSTED_RUNTIME"):
        assert azure.count(name) >= 2, name
    for agent_dir in AGENTS:
        for name, text in _agent_sources(agent_dir).items():
            assert "DD_" not in text, f"{agent_dir}/{name}"
    assert "DD_" not in azure
    for agent_dir in AGENTS:
        sources = _agent_sources(agent_dir)
        for name in ("agent.yaml", "agent.manifest.yaml"):
            assert "name: HOSTED_DEFAULT_GATEWAY" in sources[name] and "name: AGENT_DEFAULT_GATEWAY" not in sources[name], name


def test_platform_app_insights_connection_string_is_not_passed_to_hosted_agents():
    azure = (ROOT / "azure.yaml").read_text(encoding="utf-8")
    for service in ("agent-maf", "agent-langgraph"):
        block = re.split(r"\n  \S", azure.split(f"  {service}:\n", 1)[1], maxsplit=1)[0]
        assert "APPLICATIONINSIGHTS_CONNECTION_STRING" not in block, service


def test_agent_telemetry_helpers_are_byte_identical():
    import filecmp

    for name in ("gateway_auth.py", "telemetry.py"):
        assert filecmp.cmp(ROOT / "src" / "agents" / "maf" / name, ROOT / "src" / "agents" / "langgraph" / name, shallow=False), name