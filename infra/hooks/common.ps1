Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-DemoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

function Get-EnvValue {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [string]$Default = ""
    )
    $value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrWhiteSpace($value)) { return $Default }
    return $value
}

function Assert-EnvName {
    param([Parameter(Mandatory = $true)][string]$EnvironmentName)
    if ($EnvironmentName -notmatch '^[a-z0-9][a-z0-9-]{0,19}$' -or $EnvironmentName.EndsWith("-")) {
        throw "AZURE_ENV_NAME must be lowercase alphanumeric plus hyphen, start with alphanumeric, not end with hyphen, and be <= 20 characters. Current value: '$EnvironmentName'."
    }
}

function Assert-AllowedValue {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Value,
        [Parameter(Mandatory = $true)][string[]]$Allowed
    )
    if ($Allowed -notcontains $Value) {
        throw "$Name must be one of: $($Allowed -join ', '). Current value: '$Value'."
    }
}

function Test-AiGatewayTierEnabled {
    param([Parameter(Mandatory = $true)][string]$Mode)
    return @("aigateway", "both") -contains $Mode
}

function Assert-AiGatewayTierLocation {
    param([Parameter(Mandatory = $true)][string]$Location)
    $allowed = @("eastus2", "swedencentral")
    if ($allowed -notcontains $Location) {
        throw "AI_GATEWAY_TIER_LOCATION must be one of: eastus2, swedencentral. Current value: '$Location'. The AI Gateway tier public preview is only available in East US 2 and Sweden Central. See https://learn.microsoft.com/azure/api-management/ai-gateway-overview"
    }
}

function Assert-AzContextMatches {
    param(
        [Parameter(Mandatory = $true)][string]$TenantId,
        [Parameter(Mandatory = $true)][string]$SubscriptionId
    )
    if ([string]::IsNullOrWhiteSpace($TenantId) -or [string]::IsNullOrWhiteSpace($SubscriptionId)) {
        throw "AZURE_TENANT_ID and AZURE_SUBSCRIPTION_ID must be set before provisioning."
    }

    $raw = & az account show --query "{tenant:tenantId,subscription:id,user:user.name}" -o json 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($raw)) {
        throw "Azure CLI is not authenticated. Sign in explicitly with: az login --tenant $TenantId ; az account set --subscription $SubscriptionId"
    }

    $active = $raw | ConvertFrom-Json
    if ($active.tenant -ne $TenantId -or $active.subscription -ne $SubscriptionId) {
        Write-Host "Active Azure CLI context does not match this azd environment." -ForegroundColor Yellow
        Write-Host "  Active tenant/subscription:   $($active.tenant) / $($active.subscription)"
        Write-Host "  Expected tenant/subscription: $TenantId / $SubscriptionId"
        Write-Host "Fix with:"
        Write-Host "  az login --tenant $TenantId"
        Write-Host "  az account set --subscription $SubscriptionId"
        throw "Refusing to continue with the wrong Azure CLI tenant/subscription."
    }
}

function Set-AzdEnvironmentValue {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Value
    )
    & azd env set $Name $Value | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "azd env set failed for $Name."
    }
    [Environment]::SetEnvironmentVariable($Name, $Value, "Process")
}

function Ensure-GatewayAppRegistration {
    param(
        [Parameter(Mandatory = $true)][string]$EnvironmentName
    )
    $existingClientId = Get-EnvValue -Name "GATEWAY_APP_CLIENT_ID"
    if (-not [string]::IsNullOrWhiteSpace($existingClientId)) {
        return $existingClientId
    }

    $displayName = "gw-$EnvironmentName"
    Write-Host "GATEWAY_APP_CLIENT_ID is blank; creating Entra application registration '$displayName'."
    $appJson = & az ad app create --display-name $displayName -o json
    if ($LASTEXITCODE -ne 0) { throw "Failed to create Entra application registration '$displayName'." }
    $app = $appJson | ConvertFrom-Json
    $appId = [string]$app.appId

    & az ad app update --id $appId --identifier-uris "api://$appId" | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Failed to set identifier URI api://$appId." }

    $appObjectId = (& az ad app show --id $appId --query id -o tsv)
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($appObjectId)) {
        throw "Failed to resolve app object id for $appId."
    }

    $roleId = [guid]::NewGuid().ToString()
    $body = @{
        appRoles = @(
            @{
                allowedMemberTypes = @("Application", "User")
                description = "Invoke the hosted-agent AI gateway."
                displayName = "Gateway.Invoke"
                id = $roleId
                isEnabled = $true
                value = "Gateway.Invoke"
            }
        )
    } | ConvertTo-Json -Depth 6

    $patchPath = Join-Path ([System.IO.Path]::GetTempPath()) "gateway-app-role-$EnvironmentName.json"
    Set-Content -Path $patchPath -Value $body -Encoding utf8
    try {
        & az rest --method PATCH --url "https://graph.microsoft.com/v1.0/applications/$appObjectId" --headers "Content-Type=application/json" --body "@$patchPath" | Out-Host
        if ($LASTEXITCODE -ne 0) { throw "Failed to add Gateway.Invoke app role." }
    }
    finally {
        Remove-Item -Path $patchPath -Force -ErrorAction SilentlyContinue
    }

    Set-AzdEnvironmentValue -Name "GATEWAY_APP_CLIENT_ID" -Value $appId
    return $appId
}

function Invoke-SoftDeletePrompts {
    param(
        [Parameter(Mandatory = $true)][string]$EnvironmentName,
        [Parameter(Mandatory = $true)][string]$Location
    )
    $apimNamePattern = "apim-$EnvironmentName"
    $deletedApim = & az apim deletedservice list --query "[?contains(name, '$apimNamePattern')].{name:name,location:location}" -o json 2>$null
    if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($deletedApim) -and $deletedApim -ne "[]") {
        Write-Host "Soft-deleted APIM services may block reuse:" -ForegroundColor Yellow
        Write-Host $deletedApim
        $answer = Read-Host "Purge matching APIM soft-delete records now? Type PURGE to continue"
        if ($answer -eq "PURGE") {
            ($deletedApim | ConvertFrom-Json) | ForEach-Object {
                & az apim deletedservice purge --service-name $_.name --location $_.location | Out-Host
            }
        }
    }

    $deletedCog = & az cognitiveservices account list-deleted --location $Location --query "[?contains(name, 'fdry-$EnvironmentName')].{name:name,location:location}" -o json 2>$null
    if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($deletedCog) -and $deletedCog -ne "[]") {
        Write-Host "Soft-deleted Cognitive Services accounts may block reuse:" -ForegroundColor Yellow
        Write-Host $deletedCog
        $answer = Read-Host "Purge matching Cognitive Services soft-delete records now? Type PURGE to continue"
        if ($answer -eq "PURGE") {
            ($deletedCog | ConvertFrom-Json) | ForEach-Object {
                & az cognitiveservices account purge --name $_.name --location $_.location --resource-group (Get-EnvValue -Name "AZURE_RESOURCE_GROUP" -Default "rg-$EnvironmentName") | Out-Host
            }
        }
    }
}

function Write-DemoIdsFile {
    param([Parameter(Mandatory = $true)][string]$Path)
    $ids = [ordered]@{
        resourceGroup = Get-EnvValue -Name "AZURE_RESOURCE_GROUP"
        foundryAccountName = Get-EnvValue -Name "FOUNDRY_ACCOUNT_NAME"
        foundryProjectName = Get-EnvValue -Name "FOUNDRY_PROJECT_NAME"
        foundryProjectEndpoint = Get-EnvValue -Name "FOUNDRY_PROJECT_ENDPOINT"
        modelDeploymentName = Get-EnvValue -Name "MODEL_DEPLOYMENT_NAME"
        containerRegistryEndpoint = Get-EnvValue -Name "AZURE_CONTAINER_REGISTRY_ENDPOINT"
        containerAppsEnvironmentName = Get-EnvValue -Name "CONTAINER_APPS_ENVIRONMENT_NAME"
        apimName = Get-EnvValue -Name "APIM_NAME"
        apimGatewayUrl = Get-EnvValue -Name "APIM_GATEWAY_URL"
        aiGatewayMode = Get-EnvValue -Name "AI_GATEWAY_MODE"
        llmApiPath = Get-EnvValue -Name "LLM_API_PATH" -Default "llm"
        mcpCatalogUrl = Get-EnvValue -Name "MCP_CATALOG_URL"
        mcpRecordsUrl = Get-EnvValue -Name "MCP_RECORDS_URL"
        recordsApiUrl = Get-EnvValue -Name "RECORDS_API_URL"
        gatewayAppClientId = Get-EnvValue -Name "GATEWAY_APP_CLIENT_ID"
        logAnalyticsWorkspaceId = Get-EnvValue -Name "LOG_ANALYTICS_WORKSPACE_ID"
        logAnalyticsCustomerId = Get-EnvValue -Name "LOG_ANALYTICS_CUSTOMER_ID"
        applicationInsightsName = Get-EnvValue -Name "APPLICATIONINSIGHTS_NAME"
        workbookId = Get-EnvValue -Name "WORKBOOK_ID"
        queryPackId = Get-EnvValue -Name "QUERY_PACK_ID"
        keyVaultName = Get-EnvValue -Name "KEY_VAULT_NAME"
        keyVaultUri = Get-EnvValue -Name "KEY_VAULT_URI"
        aigwGatewayName = Get-EnvValue -Name "AIGW_GATEWAY_NAME"
        aigwGatewayUrl = Get-EnvValue -Name "AIGW_GATEWAY_URL"
        aigwLocation = Get-EnvValue -Name "AIGW_LOCATION"
        aigwMcpCatalogUrl = Get-EnvValue -Name "AIGW_MCP_CATALOG_URL"
        aigwMcpRecordsUrl = Get-EnvValue -Name "AIGW_MCP_RECORDS_URL"
        vnetId = Get-EnvValue -Name "VNET_ID"
        workload = [ordered]@{
            domainProfile = Get-EnvValue -Name "DOMAIN_PROFILE" -Default "manufacturing-field-ops"
            profilePath = "config/profiles/$((Get-EnvValue -Name "DOMAIN_PROFILE" -Default "manufacturing-field-ops")).json"
        }
    }
    $json = $ids | ConvertTo-Json -Depth 8
    Set-Content -Path $Path -Value $json -Encoding utf8
}
