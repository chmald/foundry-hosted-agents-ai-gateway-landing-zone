// AI Gateway tier preview sidecar. Uses the documented 2026-05-01-preview control-plane shape where public Bicep types are not yet indexed.
param location string
param tags object = {}
param gatewayName string
param foundryEndpoint string
param foundryAccountResourceId string
param modelDeploymentResourceId string
param modelDeploymentName string
param tokenLimitTpmPerAgent int
param requestLimitRpm int = 120
param enableContentSafety bool
param catalogMcpBackendUrl string
param recordsApiBackendUrl string
param appInsightsId string
@secure()
param appInsightsConnectionString string
param keyVaultName string
param runtimeKeySecretName string = 'aigw-runtime-key'

var apiVersion = '2026-05-01-preview'
var workspaceName = 'default'
var foundryUserRoleDefinitionId = '53ca6127-db72-4b80-b1b0-d745d6d5456d'
var toolCallerHeaderValue = 'aigw-runtime-key:agents'
var recordsOpenApiSpec = loadJsonContent('../../src/records-api/openapi.json')
var foundryAccountName = last(split(foundryAccountResourceId, '/'))
var commonRequestRatePolicy = {
  type: 'requestRateLimit'
  displayName: 'Hosted agent request rate limit'
  enabled: true
  scope: 'callerIdentity'
  limit: requestLimitRpm
  period: 'minute'
}
var contentSafetyPolicy = {
  type: 'contentSafety'
  displayName: 'Baseline content safety'
  enabled: enableContentSafety
  mode: 'block'
  categories: [
    {
      name: 'Hate'
      threshold: 4
    }
    {
      name: 'Sexual'
      threshold: 4
    }
    {
      name: 'SelfHarm'
      threshold: 4
    }
    {
      name: 'Violence'
      threshold: 4
    }
  ]
  promptShields: {
    enabled: true
  }
}
var tokenLimitPolicy = {
  type: 'tokenLimit'
  displayName: 'Hosted agent token rate limit'
  enabled: true
  scope: 'callerIdentity'
  limit: tokenLimitTpmPerAgent
  period: 'minute'
}

resource aiGateway 'Microsoft.ApiManagement/aigateways@2026-05-01-preview' = {
  name: gatewayName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'AIGateway'
    capacity: 1
  }
  properties: {}
}

resource foundryAccount 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryAccountName
}

resource foundryUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: foundryAccount
  name: guid(foundryAccountResourceId, aiGateway.id, foundryUserRoleDefinitionId)
  properties: {
    principalId: aiGateway.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', foundryUserRoleDefinitionId)
  }
}

resource workspace 'Microsoft.ApiManagement/aigateways/workspaces@2026-05-01-preview' existing = {
  parent: aiGateway
  name: workspaceName
}

resource telemetryExporter 'Microsoft.ApiManagement/aigateways/workspaces/telemetryExporters@2026-05-01-preview' = {
  parent: workspace
  name: 'appinsights'
  properties: {
    kind: 'applicationInsights'
    payloadCapture: false
    applicationInsights: {
      resourceId: appInsightsId
      connectionString: appInsightsConnectionString
    }
  }
}

resource foundryProvider 'Microsoft.ApiManagement/aigateways/workspaces/modelProviders@2026-05-01-preview' = {
  parent: workspace
  name: 'foundry'
  properties: {
    kind: 'Foundry'
    displayName: 'Microsoft Foundry'
    description: 'Managed identity connection to the Microsoft Foundry account backing the demo model deployment.'
    foundry: {
      endpoint: endsWith(foundryEndpoint, '/') ? foundryEndpoint : '${foundryEndpoint}/'
      resourceIds: [
        foundryAccountResourceId
      ]
      authentication: {
        kind: 'ManagedIdentity'
        managedIdentity: {
          resource: 'https://cognitiveservices.azure.com/'
        }
      }
    }
  }
  dependsOn: [
    foundryUserAssignment
  ]
}

resource providerModel 'Microsoft.ApiManagement/aigateways/workspaces/modelProviders/models@2026-05-01-preview' = {
  parent: foundryProvider
  name: modelDeploymentName
  properties: {
    displayName: modelDeploymentName
    description: 'Imported Foundry deployment exposed through the AI Gateway tier.'
    deployment: {
      resourceId: modelDeploymentResourceId
      name: modelDeploymentName
    }
    supportedEndpoints: [
      'OpenAIChatCompletions'
      'OpenAIResponses'
    ]
  }
}

resource callableModel 'Microsoft.ApiManagement/aigateways/workspaces/models@2026-05-01-preview' = {
  parent: workspace
  name: modelDeploymentName
  properties: {
    displayName: modelDeploymentName
    description: 'OpenAI-compatible callable model for hosted agents.'
    backendModels: [
      {
        resourceId: providerModel.id
      }
    ]
    supportedEndpoints: [
      'OpenAIChatCompletions'
      'OpenAIResponses'
    ]
    policies: enableContentSafety ? [
      tokenLimitPolicy
      commonRequestRatePolicy
      contentSafetyPolicy
    ] : [
      tokenLimitPolicy
      commonRequestRatePolicy
    ]
  }
}

resource catalogToolServer 'Microsoft.ApiManagement/aigateways/workspaces/toolServers@2026-05-01-preview' = {
  parent: workspace
  name: 'catalog-mcp'
  properties: {
    displayName: 'Catalog MCP'
    description: 'Remote streamable HTTP MCP endpoint for catalog tools.'
    kind: 'mcp'
    failureMode: 'failClosed'
    backends: [
      {
        name: 'catalog'
        kind: 'mcp'
        endpoint: catalogMcpBackendUrl
        transport: 'streamableHttp'
        authentication: {
          kind: 'apiKey'
          apiKey: {
            location: 'header'
            name: 'x-gw-caller'
            value: toolCallerHeaderValue
          }
        }
      }
    ]
    policies: enableContentSafety ? [
      commonRequestRatePolicy
      contentSafetyPolicy
    ] : [
      commonRequestRatePolicy
    ]
  }
}

resource recordsToolServer 'Microsoft.ApiManagement/aigateways/workspaces/toolServers@2026-05-01-preview' = {
  parent: workspace
  name: 'records'
  properties: {
    displayName: 'Records'
    description: 'OpenAPI-generated MCP tool server for records-api operations.'
    kind: 'openApi'
    failureMode: 'failClosed'
    backends: [
      {
        name: 'records'
        kind: 'openApi'
        endpoint: recordsApiBackendUrl
        openApi: {
          specification: recordsOpenApiSpec
        }
        authentication: {
          kind: 'apiKey'
          apiKey: {
            location: 'header'
            name: 'x-gw-caller'
            value: toolCallerHeaderValue
          }
        }
      }
    ]
    policies: enableContentSafety ? [
      commonRequestRatePolicy
      contentSafetyPolicy
    ] : [
      commonRequestRatePolicy
    ]
  }
}

resource runtimeAccessKey 'Microsoft.ApiManagement/aigateways/apiKeys@2026-05-01-preview' = {
  parent: aiGateway
  name: 'agents'
  properties: {
    displayName: 'Hosted agents runtime key'
    owner: 'hosted-agents'
  }
}

output gatewayName string = aiGateway.name
output gatewayResourceId string = aiGateway.id
output gatewayUrl string = 'https://${aiGateway.properties.frontend.defaultHostname}'
output location string = location
output catalogMcpUrl string = 'https://${aiGateway.properties.frontend.defaultHostname}/default/toolservers/${catalogToolServer.name}/mcp'
output recordsMcpUrl string = 'https://${aiGateway.properties.frontend.defaultHostname}/default/toolservers/${recordsToolServer.name}/mcp'
output runtimeKeyResourceId string = runtimeAccessKey.id
output runtimeKeySecretName string = runtimeKeySecretName
output keyVaultName string = keyVaultName
output keyVaultSecretUri string = 'https://${keyVaultName}${environment().suffixes.keyvaultDns}/secrets/${runtimeKeySecretName}'
output apiVersionUsed string = apiVersion
