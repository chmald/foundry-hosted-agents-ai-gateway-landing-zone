// Microsoft Foundry account/project, model deployment, ACR, App Insights connection, and project pull permissions.
// When networkIsolation is true the account is created with agent-subnet network injection and public access disabled;
// BYO connections + capability host are added by foundry-agent-byo.bicep once private endpoints exist.
param location string
param tags object = {}
param aiServicesName string
param aiProjectName string
param modelName string
param modelVersion string
param modelDeploymentName string
param modelSku string
param modelCapacity int
param principalId string = ''
param principalType string = 'User'
param appInsightsId string
@secure()
param appInsightsConnectionString string
param containerRegistryName string
param networkIsolation bool = false
@description('Delegated agent subnet resource id (Microsoft.App/environments). Required when networkIsolation is true; hosted agents need network injection set when the account is first created.')
param agentSubnetId string = ''

resource aiServices 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: aiServicesName
  location: location
  tags: tags
  sku: {
    name: 'S0'
  }
  kind: 'AIServices'
  identity: {
    type: 'SystemAssigned'
  }
  properties: union({
    allowProjectManagement: true
    customSubDomainName: toLower(aiServicesName)
    disableLocalAuth: true
    publicNetworkAccess: networkIsolation ? 'Disabled' : 'Enabled'
  }, networkIsolation ? {
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
      ipRules: []
      virtualNetworkRules: []
    }
    networkInjections: [
      {
        scenario: 'agent'
        subnetArmId: agentSubnetId
        useMicrosoftManagedNetwork: false
      }
    ]
  } : {})
}

resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: aiServices
  name: aiProjectName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: aiProjectName
    description: 'Generic hosted-agent project for the gateway landing-zone demo.'
  }
  dependsOn: [
    modelDeployment
  ]
}

resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: aiServices
  name: modelDeploymentName
  sku: {
    name: modelSku
    capacity: modelCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      version: modelVersion
    }
  }
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: containerRegistryName
  location: location
  tags: tags
  sku: {
    // Private endpoints require Premium; Standard is enough (and cheaper) when the registry stays public.
    name: networkIsolation ? 'Premium' : 'Standard'
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: networkIsolation ? 'Disabled' : 'Enabled'
    networkRuleBypassOptions: 'AzureServices'
    zoneRedundancy: 'Disabled'
  }
}

resource appInsightsConnection 'Microsoft.CognitiveServices/accounts/connections@2025-06-01' = if (!empty(appInsightsId)) {
  parent: aiServices
  name: 'appinsights'
  properties: {
    category: 'AppInsights'
    authType: 'ApiKey'
    isSharedToAll: false
    target: appInsightsId
    credentials: {
      key: appInsightsConnectionString
    }
    metadata: {
      ApiType: 'Azure'
      ResourceId: appInsightsId
    }
  }
  dependsOn: [
    aiProject
  ]
}

resource projectAcrConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = {
  parent: aiProject
  name: '${acr.name}-conn'
  properties: {
    category: 'ContainerRegistry'
    target: acr.properties.loginServer
    authType: 'ManagedIdentity'
    credentials: {
      clientId: aiProject.identity.principalId
      resourceId: acr.id
    }
    isSharedToAll: true
    metadata: {
      ResourceId: acr.id
    }
  }
  dependsOn: [
    acrPullAssignmentProject
  ]
}

var acrPullRoleDefinitionId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
var cognitiveServicesUserRoleDefinitionId = 'a97b65f3-24c7-4388-baec-2e87135dc908'
var cognitiveServicesContributorRoleDefinitionId = '25fbc0a9-bd7c-42a3-aa1a-3b75d497ee68'
var cognitiveServicesOpenAIUserRoleDefinitionId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

resource acrPullAssignmentProject 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: acr
  name: guid(acr.id, aiProject.id, acrPullRoleDefinitionId)
  properties: {
    principalId: aiProject.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleDefinitionId)
  }
}

resource operatorAiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  scope: aiServices
  name: guid(aiServices.id, principalId, cognitiveServicesUserRoleDefinitionId)
  properties: {
    principalId: principalId
    principalType: principalType
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesUserRoleDefinitionId)
  }
}

resource operatorAiOpenAIUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  scope: aiServices
  name: guid(aiServices.id, principalId, cognitiveServicesOpenAIUserRoleDefinitionId)
  properties: {
    principalId: principalId
    principalType: principalType
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUserRoleDefinitionId)
  }
}

resource projectAiContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: aiServices
  name: guid(aiServices.id, aiProject.id, cognitiveServicesContributorRoleDefinitionId)
  properties: {
    principalId: aiProject.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesContributorRoleDefinitionId)
  }
}

output aiServicesName string = aiServices.name
output aiServicesId string = aiServices.id
output aiServicesEndpoint string = aiServices.properties.endpoint
output openAiEndpoint string = aiServices.properties.endpoints['OpenAI Language Model Instance API']
output aiProjectName string = aiProject.name
output aiProjectResourceId string = aiProject.id
output aiProjectPrincipalId string = aiProject.identity.principalId
output projectEndpoint string = 'https://${aiServices.name}.services.ai.azure.com/api/projects/${aiProject.name}'
output modelDeploymentId string = modelDeployment.id
output containerRegistryName string = acr.name
output containerRegistryEndpoint string = acr.properties.loginServer
output containerRegistryId string = acr.id
