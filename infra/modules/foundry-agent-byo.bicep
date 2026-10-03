// Foundry standard agent setup with BYO resources (network-isolated mode):
// project connections to Cosmos DB / Storage / AI Search, the project managed-identity roles they need,
// and the project capability host. Mirrors microsoft-foundry/foundry-samples 15-private-network-standard-agent-setup.
// Must run AFTER the private endpoints + DNS zone groups for the account, Cosmos, Storage and Search exist.
param accountName string
param projectName string
param projectPrincipalId string
param cosmosDbResourceId string
param storageAccountResourceId string
param searchServiceResourceId string
param projectCapabilityHostName string = 'caphostproj'

var cosmosName = last(split(cosmosDbResourceId, '/'))
var storageName = last(split(storageAccountResourceId, '/'))
var searchName = last(split(searchServiceResourceId, '/'))

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: accountName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' existing = {
  parent: account
  name: projectName
}

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' existing = {
  name: cosmosName
}

resource storage 'Microsoft.Storage/storageAccounts@2024-01-01' existing = {
  name: storageName
}

resource search 'Microsoft.Search/searchServices@2024-06-01-preview' existing = {
  name: searchName
}

resource cosmosConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = {
  parent: project
  name: cosmosName
  properties: {
    category: 'CosmosDB'
    target: cosmos.properties.documentEndpoint
    authType: 'AAD'
    metadata: {
      ApiType: 'Azure'
      ResourceId: cosmos.id
      location: cosmos.location
    }
  }
}

resource storageConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = {
  parent: project
  name: storageName
  properties: {
    category: 'AzureStorageAccount'
    target: storage.properties.primaryEndpoints.blob
    authType: 'AAD'
    metadata: {
      ApiType: 'Azure'
      ResourceId: storage.id
      location: storage.location
    }
  }
}

resource searchConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = {
  parent: project
  name: searchName
  properties: {
    category: 'CognitiveSearch'
    target: 'https://${searchName}.search.windows.net'
    authType: 'AAD'
    metadata: {
      ApiType: 'Azure'
      ResourceId: search.id
      location: search.location
    }
  }
}

var cosmosOperatorRoleId = '230815da-be43-4aae-9cb4-875f7bd000aa'
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var searchIndexDataContributorRoleId = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
var searchServiceContributorRoleId = '7ca78c08-252a-4471-8644-bb5ff32d4ba0'

resource cosmosOperator 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: cosmos
  name: guid(projectPrincipalId, cosmosOperatorRoleId, cosmos.id)
  properties: {
    principalId: projectPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cosmosOperatorRoleId)
  }
}

resource storageBlobContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storage
  name: guid(projectPrincipalId, storageBlobDataContributorRoleId, storage.id)
  properties: {
    principalId: projectPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRoleId)
  }
}

resource searchIndexContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: search
  name: guid(projectPrincipalId, searchIndexDataContributorRoleId, search.id)
  properties: {
    principalId: projectPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataContributorRoleId)
  }
}

resource searchServiceContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: search
  name: guid(projectPrincipalId, searchServiceContributorRoleId, search.id)
  properties: {
    principalId: projectPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchServiceContributorRoleId)
  }
}

resource projectCapabilityHost 'Microsoft.CognitiveServices/accounts/projects/capabilityHosts@2025-04-01-preview' = {
  parent: project
  name: projectCapabilityHostName
  properties: {
    #disable-next-line BCP037
    capabilityHostKind: 'Agents'
    vectorStoreConnections: [
      searchConnection.name
    ]
    storageConnections: [
      storageConnection.name
    ]
    threadStorageConnections: [
      cosmosConnection.name
    ]
  }
  dependsOn: [
    cosmosOperator
    storageBlobContributor
    searchIndexContributor
    searchServiceContributor
  ]
}

#disable-next-line BCP053
output projectWorkspaceId string = project.properties.internalId
output capabilityHostName string = projectCapabilityHost.name
