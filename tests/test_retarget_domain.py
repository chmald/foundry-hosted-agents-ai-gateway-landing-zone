
import json
from conftest import ROOT

def test_it_service_desk_profile_has_no_manufacturing_terms_in_agent_or_tool_descriptions():
    profile=json.loads((ROOT/"config"/"profiles"/"it-service-desk.json").read_text())
    text=" ".join([profile["agent"]["description"],profile["agent"]["instructions"],*profile["catalogTools"].values(),*profile["recordsTools"].values()]).lower()
    for term in ["manufacturing","field ops","work order","parts catalog","plant","line inspection"]: assert term not in text
