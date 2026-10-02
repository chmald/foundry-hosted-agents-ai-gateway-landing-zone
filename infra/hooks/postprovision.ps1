. "$PSScriptRoot\common.ps1"

$root = Get-DemoRoot
$idsPath = Join-Path $root "demo-ids.local.json"
Write-DemoIdsFile -Path $idsPath
Write-Host "Wrote local deployment IDs to $idsPath"

$enableEntraDiagnostics = Get-EnvValue -Name "ENABLE_ENTRA_DIAGNOSTICS" -Default "false"
if ($enableEntraDiagnostics -eq "true") {
    $scriptPath = Join-Path $root "scripts\Enable-EntraDiagnostics.ps1"
    if (Test-Path $scriptPath) {
        $tenantId = Get-EnvValue -Name "AZURE_TENANT_ID"
        $workspaceResourceId = Get-EnvValue -Name "LOG_ANALYTICS_WORKSPACE_ID"
        & $scriptPath -TenantId $tenantId -LogAnalyticsWorkspaceResourceId $workspaceResourceId
        if ($LASTEXITCODE -ne 0) { throw "Enable-EntraDiagnostics.ps1 failed." }
    }
    else {
        Write-Host "ENABLE_ENTRA_DIAGNOSTICS=true but scripts\Enable-EntraDiagnostics.ps1 was not found; skipping tenant-level export setup." -ForegroundColor Yellow
    }
}

$mode = Get-EnvValue -Name "AI_GATEWAY_MODE" -Default "apimv2"
if (Test-AiGatewayTierEnabled -Mode $mode) {
    $aigwName = Get-EnvValue -Name "AIGW_GATEWAY_NAME"
    $resourceGroup = Get-EnvValue -Name "AZURE_RESOURCE_GROUP"
    $subscriptionId = Get-EnvValue -Name "AZURE_SUBSCRIPTION_ID"
    $keyVaultName = Get-EnvValue -Name "KEY_VAULT_NAME"
    $secretName = Get-EnvValue -Name "AIGW_RUNTIME_KEY_SECRET_NAME" -Default "aigw-runtime-key"
    if (-not [string]::IsNullOrWhiteSpace($aigwName) -and -not [string]::IsNullOrWhiteSpace($resourceGroup) -and -not [string]::IsNullOrWhiteSpace($subscriptionId) -and -not [string]::IsNullOrWhiteSpace($keyVaultName)) {
        $apiVersion = "2026-05-01-preview"
        $apiKeyResourceId = "/subscriptions/$subscriptionId/resourceGroups/$resourceGroup/providers/Microsoft.ApiManagement/aigateways/$aigwName/apiKeys/agents"
        $listSecretsUrl = "https://management.azure.com$apiKeyResourceId/listSecrets?api-version=$apiVersion"
        try {
            $secretJson = & az rest --method post --url $listSecretsUrl -o json
            if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($secretJson)) {
                throw "az rest listSecrets returned exit code $LASTEXITCODE."
            }
            $secretResult = $secretJson | ConvertFrom-Json
            $runtimeKey = [string]($secretResult.properties.primaryKey ?? $secretResult.primaryKey ?? $secretResult.value)
            if ([string]::IsNullOrWhiteSpace($runtimeKey)) {
                throw "AI Gateway apiKeys/listSecrets response did not include properties.primaryKey, primaryKey, or value."
            }
            & az keyvault secret set --vault-name $keyVaultName --name $secretName --value $runtimeKey --only-show-errors | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "az keyvault secret set failed with exit code $LASTEXITCODE." }
            Write-Host "Stored AI Gateway runtime access key 'agents' in Key Vault secret '$secretName'."
        }
        catch {
            Write-Host "AI Gateway runtime key could not be stored automatically: $($_.Exception.Message)" -ForegroundColor Yellow
            Write-Host "Portal fallback: open https://ai.gateway.azure.com, select gateway '$aigwName', create/copy runtime key 'agents', then store it in Key Vault '$keyVaultName' as secret '$secretName'." -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "Skipping AI Gateway runtime key capture because one or more required azd outputs are blank: AIGW_GATEWAY_NAME, AZURE_RESOURCE_GROUP, AZURE_SUBSCRIPTION_ID, KEY_VAULT_NAME." -ForegroundColor Yellow
    }
}

if ($mode -eq "apimv2" -or $mode -eq "both") {
    Write-Host "Register the APIM v2 gateway with the Microsoft Foundry project from the Foundry portal: Manage > AI Gateway > Register existing API Management gateway."
}
else {
    Write-Host "AI Gateway tier preview resources were provisioned. If model/tool routes are not visible in Foundry, complete connection registration from the AI Gateway portal or with the documented control-plane API."
}

Write-Host "No sample data was seeded by infra hooks. Runtime seed behavior is controlled by SEED_SAMPLE_DATA and the code scripts."
