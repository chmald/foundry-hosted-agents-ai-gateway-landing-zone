. "$PSScriptRoot\common.ps1"

$envName = Get-EnvValue -Name "AZURE_ENV_NAME"
$location = Get-EnvValue -Name "AZURE_LOCATION" -Default "eastus2"
$tenantId = Get-EnvValue -Name "AZURE_TENANT_ID"
$subscriptionId = Get-EnvValue -Name "AZURE_SUBSCRIPTION_ID"
$mode = Get-EnvValue -Name "AI_GATEWAY_MODE" -Default "apimv2"
$aiGatewayTierLocation = Get-EnvValue -Name "AI_GATEWAY_TIER_LOCATION" -Default "eastus2"
$sku = Get-EnvValue -Name "APIM_SKU" -Default "StandardV2"
$network = Get-EnvValue -Name "NETWORK_ISOLATION" -Default "false"

Assert-EnvName -EnvironmentName $envName
Assert-AzContextMatches -TenantId $tenantId -SubscriptionId $subscriptionId
Assert-AllowedValue -Name "AI_GATEWAY_MODE" -Value $mode -Allowed @("apimv2", "aigateway", "both")
if (Test-AiGatewayTierEnabled -Mode $mode) {
    Assert-AiGatewayTierLocation -Location $aiGatewayTierLocation
}
Assert-AllowedValue -Name "APIM_SKU" -Value $sku -Allowed @("StandardV2", "PremiumV2")
Assert-AllowedValue -Name "NETWORK_ISOLATION" -Value $network -Allowed @("true", "false")

$gatewayClientId = Ensure-GatewayAppRegistration -EnvironmentName $envName
Write-Host "Gateway application client id: $gatewayClientId"

Invoke-SoftDeletePrompts -EnvironmentName $envName -Location $location

Write-Host "Preprovision checks passed for '$envName'."
