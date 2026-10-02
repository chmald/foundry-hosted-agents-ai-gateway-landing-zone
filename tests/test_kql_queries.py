
import re, pytest
from conftest import ROOT
KNOWN_TABLES={"ApiManagementGatewayLogs","ApiManagementGatewayLlmLog","ApiManagementGatewayMCPLog","ContainerAppConsoleLogs_CL","AppTraces","AzureActivity","AADServicePrincipalSignInLogs","AADManagedIdentitySignInLogs","AuditLogs","AzureDiagnostics"}
def test_kql_queries_when_present():
    query_dir=ROOT/"infra"/"monitoring"/"queries"; files=sorted(query_dir.glob("*.kql"))
    if not files: pytest.skip("infra/monitoring/queries KQL files are written by the infra agent")
    assert len(files)>=10
    for path in files:
        text=path.read_text(); assert text.lstrip().startswith("//"), f"{path.name} needs a header comment"
        assert set(re.findall(r"\b[A-Z][A-Za-z0-9_]+\b", text)) & KNOWN_TABLES, f"{path.name} should reference at least one known table"
