from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from conftest import ROOT


CONFIG_DOC = ROOT / "docs" / "12-configuration-reference.md"
AZD_PARAMETERS = ROOT / "infra" / "azd.parameters.json"
AZD_BICEP = ROOT / "infra" / "azd.bicep"
MAIN_BICEP = ROOT / "infra" / "main.bicep"


def config_text() -> str:
    return CONFIG_DOC.read_text(encoding="utf-8")


def azd_parameter_variables() -> set[str]:
    data = json.loads(AZD_PARAMETERS.read_text(encoding="utf-8"))
    variables: set[str] = set()
    for item in data["parameters"].values():
        value = item["value"]
        match = re.fullmatch(r"\$\{([A-Z0-9_]+)(?:=[^}]*)?\}", value)
        assert match, f"azd parameter value is not a single quoted substitution: {value}"
        variables.add(match.group(1))
    return variables


def bicep_outputs(path: Path) -> set[str]:
    return set(re.findall(r"(?m)^output\s+([A-Z0-9_]+)\s+", path.read_text(encoding="utf-8")))


def bicep_params(path: Path) -> set[str]:
    return set(re.findall(r"(?m)^param\s+([A-Za-z][A-Za-z0-9_]*)\s+", path.read_text(encoding="utf-8")))


def azd_main_module_params() -> set[str]:
    text = AZD_BICEP.read_text(encoding="utf-8")
    match = re.search(r"module\s+main\s+'main\.bicep'\s*=\s*\{.*?\n\s*params:\s*\{(?P<body>.*?)\n\s*\}\n\}", text, re.S)
    assert match, "could not find main.bicep module params in infra/azd.bicep"
    return set(re.findall(r"(?m)^\s*([A-Za-z][A-Za-z0-9_]*)\s*:", match.group("body")))


def hook_env_vars() -> set[str]:
    variables: set[str] = set()
    for path in (ROOT / "infra" / "hooks").glob("*.ps1"):
        text = path.read_text(encoding="utf-8")
        variables.update(re.findall(r'Get-EnvValue\s+-Name\s+"([A-Z0-9_]+)"', text))
        variables.update(re.findall(r"\$env:([A-Z0-9_]+)", text))
    return variables


def python_env_vars() -> set[str]:
    variables: set[str] = set()
    for base in [ROOT / "scripts", ROOT / "src"]:
        for path in base.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    is_environ_get = (
                        node.func.attr == "get"
                        and isinstance(node.func.value, ast.Attribute)
                        and node.func.value.attr == "environ"
                    )
                    is_getenv = node.func.attr == "getenv"
                    if (is_environ_get or is_getenv) and node.args and isinstance(node.args[0], ast.Constant):
                        value = node.args[0].value
                        if isinstance(value, str) and re.fullmatch(r"[A-Z0-9_]+", value):
                            variables.add(value)
    return variables


def template_demo_ids_keys() -> set[str]:
    data = json.loads((ROOT / "demo-ids.template.json").read_text(encoding="utf-8"))
    keys = set(data.keys())
    keys.update(data.get("workload", {}).keys())
    return {key for key in keys if not key.startswith("_")}


def python_demo_ids_keys() -> set[str]:
    allowed = template_demo_ids_keys().union({"hostedAgentUrl", "profilePath", "domainProfile"})
    keys: set[str] = set()
    for base in [ROOT / "scripts", ROOT / "src"]:
        for path in base.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get":
                    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                        keys.add(node.args[0].value)
                if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                    keys.add(node.slice.value)
    return keys & allowed


def assert_terms_documented(terms: set[str], label: str) -> None:
    text = config_text()
    missing = sorted(term for term in terms if term not in text)
    assert not missing, f"{label} missing from docs/12-configuration-reference.md: {', '.join(missing)}"


def test_azd_parameter_variables_are_documented():
    assert_terms_documented(azd_parameter_variables(), "azd parameter variables")


def test_azd_outputs_are_documented():
    assert_terms_documented(bicep_outputs(AZD_BICEP), "azd.bicep outputs")


def test_hook_env_vars_are_documented():
    assert_terms_documented(hook_env_vars(), "hook environment variables")


def test_python_env_vars_are_documented():
    assert_terms_documented(python_env_vars(), "Python environment variables")


def test_demo_ids_keys_are_documented():
    assert_terms_documented(template_demo_ids_keys().union(python_demo_ids_keys()), "demo-ids keys")


def test_azd_bicep_passes_every_main_bicep_parameter():
    missing = sorted(bicep_params(MAIN_BICEP) - azd_main_module_params())
    assert not missing, f"infra/azd.bicep does not pass main.bicep params: {', '.join(missing)}"
