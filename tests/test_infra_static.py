
import json, pytest
from conftest import ROOT

def test_azd_parameters_are_quoted_when_infra_present():
    params=ROOT/"infra"/"azd.parameters.json"; azd_bicep=ROOT/"infra"/"azd.bicep"
    if not params.exists() or not azd_bicep.exists(): pytest.skip("infra azd files are written by the infra agent")
    data=json.loads(params.read_text())
    for name,value in data.get("parameters",{}).items(): assert isinstance(value.get("value"), str), f"{name} value must be a quoted azd substitution"
    assert "targetScope = 'subscription'" in azd_bicep.read_text()
