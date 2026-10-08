param(
    # Service/agent names to process. Defaults to the service azd is deploying (AZD_SERVICE_NAME), else both hosted agents.
    [string[]]$AgentName = @()
)

. "$PSScriptRoot\common.ps1"

# A hosted agent runs as its Instance Identity Principal, which only exists after the agent is deployed, so Bicep cannot
# grant it Key Vault access. This hook grants "Key Vault Secrets User" on the vault to each deployed agent's instance principal.
$hostedAgents = @("agent-maf", "agent-langgraph")
if ($AgentName.Count -eq 0) {
    $serviceName = Get-EnvValue -Name "AZD_SERVICE_NAME"
    $AgentName = if ($hostedAgents -contains $serviceName) { @($serviceName) } else { $hostedAgents }
}

$tenantId = Get-EnvValue -Name "AZURE_TENANT_ID"
$subscriptionId = Get-EnvValue -Name "AZURE_SUBSCRIPTION_ID"
Assert-AzContextMatches -TenantId $tenantId -SubscriptionId $subscriptionId

$delivery = Get-AiGatewayKeyDelivery
$mode = Get-EnvValue -Name "AI_GATEWAY_MODE" -Default "apimv2"
if ($delivery -eq "env") {
    Write-Host "AIGW_KEY_DELIVERY=env: hosted agents use the plaintext AIGW_RUNTIME_KEY env var (demo-only compromise); no Key Vault role assignment is needed. Skipping." -ForegroundColor Yellow
    return
}
if (-not (Test-AiGatewayTierEnabled -Mode $mode)) {
    Write-Host "AI_GATEWAY_MODE=$mode does not use the AI Gateway runtime key; agents authenticate to APIM v2 with their Entra token (no Azure RBAC is required for that audience). Skipping Key Vault grant."
    return
}

$resourceGroup = Get-EnvValue -Name "AZURE_RESOURCE_GROUP"
$keyVaultName = Get-EnvValue -Name "KEY_VAULT_NAME"
if ([string]::IsNullOrWhiteSpace($resourceGroup) -or [string]::IsNullOrWhiteSpace($keyVaultName)) {
    Write-Host "Skipping Key Vault grant: AZURE_RESOURCE_GROUP and KEY_VAULT_NAME must be set (run 'azd provision' first)." -ForegroundColor Yellow
    return
}
$scope = "/subscriptions/$subscriptionId/resourceGroups/$resourceGroup/providers/Microsoft.KeyVault/vaults/$keyVaultName"

Push-Location (Get-DemoRoot)
$results = @()
try {
    foreach ($name in $AgentName) {
        $principalId = ""
        $status = ""
        $detail = ""
        try {
            for ($attempt = 1; $attempt -le 3 -and -not $principalId; $attempt++) {
                $principalId = Get-AgentInstancePrincipalId -AgentName $name
                if (-not $principalId -and $attempt -lt 3) { Start-Sleep -Seconds 10 }
            }
            if (-not $principalId) {
                $status = "NOT FOUND"
                $detail = "no instance identity yet; check 'azd ai agent show $name --output json' (instance_identity.principal_id)"
            }
            else {
                $status = Grant-KeyVaultSecretsUser -PrincipalId $principalId -Scope $scope
            }
        }
        catch {
            $status = "FAILED"
            $detail = $_.Exception.Message
        }
        if ($status -in @("NOT FOUND", "FAILED")) {
            Write-Host "WARNING: could not grant Key Vault access for '$name': $detail" -ForegroundColor Yellow
            if ($principalId) {
                Write-Host "  Grant manually: az role assignment create --assignee-object-id $principalId --assignee-principal-type ServicePrincipal --role `"Key Vault Secrets User`" --scope $scope" -ForegroundColor Yellow
            }
        }
        $results += [pscustomobject]@{ Agent = $name; InstancePrincipalId = $(if ($principalId) { $principalId } else { "-" }); KeyVaultSecretsUser = $status }
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "Hosted-agent Key Vault access (AIGW_KEY_DELIVERY=keyvault) on '$keyVaultName':"
$results | Format-Table -AutoSize | Out-String | Write-Host
$failed = @($results | Where-Object { $_.KeyVaultSecretsUser -in @("NOT FOUND", "FAILED") })
if ($failed.Count -gt 0) {
    Write-Host "Not every agent was granted. Without the role (or with Key Vault public access disabled by policy) the AI Gateway runtime key read returns 403; see docs for AIGW_KEY_DELIVERY=env and isolated mode." -ForegroundColor Yellow
}
else {
    Write-Host "Role assignments can take a few minutes to propagate; the agent retries the Key Vault read on its next request."
}
Write-Host "If the agent still gets 403 ForbiddenByConnection, Key Vault public access is disabled (e.g. by an organization policy): use NETWORK_ISOLATION=true (private endpoint + agent subnet injection), or as a demo-only compromise set AIGW_KEY_DELIVERY=env and re-run 'azd provision' then 'azd deploy'." -ForegroundColor Cyan
