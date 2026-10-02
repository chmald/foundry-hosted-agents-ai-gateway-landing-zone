[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string]$TenantId,
    [Parameter(Mandatory = $true)][string]$LogAnalyticsWorkspaceResourceId,
    [string]$DiagnosticSettingName = "agent-identity-audit-export"
)
$ErrorActionPreference = "Stop"
$active = az account show --query "{tenant:tenantId}" -o json | ConvertFrom-Json
if ($active.tenant -ne $TenantId) { throw "Active az tenant $($active.tenant) does not match $TenantId. Run: az login --tenant $TenantId" }
$body = @{ properties = @{ workspaceId = $LogAnalyticsWorkspaceResourceId; logs = @(
@{ category = "SignInLogs"; enabled = $true }, @{ category = "NonInteractiveUserSignInLogs"; enabled = $true }, @{ category = "ServicePrincipalSignInLogs"; enabled = $true }, @{ category = "ManagedIdentitySignInLogs"; enabled = $true }, @{ category = "AuditLogs"; enabled = $true }) } } | ConvertTo-Json -Depth 8
$uri = "https://management.azure.com/providers/microsoft.aadiam/diagnosticSettings/$DiagnosticSettingName?api-version=2017-04-01-preview"
if ($PSCmdlet.ShouldProcess($uri, "Create Entra diagnostic setting (requires Security Administrator)")) { az rest --method put --uri $uri --body $body --headers "Content-Type=application/json" | Out-Host }
