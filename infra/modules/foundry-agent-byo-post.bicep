// Post-capability-host data-plane roles for the Foundry project identity. The agent-owned blob containers
// (<workspace-guid>-azureml-agent) and the Cosmos `enterprise_memory` database only exist after the capability host
// is created, so these assignments run as a separate module after foundry-agent-byo.bicep.
param projectPrincipalId string
param storageAccountResourceId string
param cosmosDbResourceId string
@description('project.properties.internalId (32 hex chars, no dashes).')
param projectWorkspaceId string

var storageName = last(split(storageAccountResourceId, '/'))
var cosmosName = last(split(cosmosDbResourceId, '/'))
var workspaceGuid = '${substring(projectWorkspaceId, 0, 8)}-${substring(projectWorkspaceId, 8, 4)}-${substring(projectWorkspaceId, 12, 4)}-${substring(projectWorkspaceId, 16, 4)}-${substring(projectWorkspaceId, 20, 12)}'

resource storage 'Microsoft.Storage/storageAccounts@2024-01-01' existing = {
  name: storageName
}

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' existing = {
  name: cosmosName
}

var storageBlobDataOwnerRoleId = 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'
// ABAC: Storage Blob Data Owner limited to the project's own agent containers.
var blobCondition = '((!(ActionMatches{\'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/tags/read\'}) AND !(ActionMatches{\'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/filter/action\'}) AND !(ActionMatches{\'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/tags/write\'})) OR (@Resource[Microsoft.Storage/storageAccounts/blobServices/containers:name] StringStartsWithIgnoreCase \'${workspaceGuid}\' AND @Resource[Microsoft.Storage/storageAccounts/blobServices/containers:name] StringLikeIgnoreCase \'*-azureml-agent\'))'

resource storageBlobDataOwner 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storage
  name: guid(storage.id, projectPrincipalId, storageBlobDataOwnerRoleId, workspaceGuid)
  properties: {
    principalId: projectPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataOwnerRoleId)
    conditionVersion: '2.0'
    condition: blobCondition
  }
}

// Built-in Cosmos DB data-plane role "Cosmos DB Built-in Data Contributor".
var cosmosDataContributorRoleId = resourceId('Microsoft.DocumentDB/databaseAccounts/sqlRoleDefinitions', cosmosName, '00000000-0000-0000-0000-000000000002')

resource cosmosDataContributor 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2022-05-15' = {
  parent: cosmos
  name: guid(workspaceGuid, cosmosName, cosmosDataContributorRoleId, projectPrincipalId)
  properties: {
    principalId: projectPrincipalId
    roleDefinitionId: cosmosDataContributorRoleId
    scope: '${cosmos.id}/dbs/enterprise_memory'
  }
  dependsOn: [
    storageBlobDataOwner
  ]
}
