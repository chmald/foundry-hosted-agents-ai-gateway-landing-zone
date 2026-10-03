// Private-mode BYO dependencies for Microsoft Foundry standard private-networking setup:
// Cosmos DB (thread storage), Storage (files), AI Search (vector store), each behind a private endpoint + DNS zone group.
param location string
param tags object = {}
param namePrefix string
param privateEndpointSubnetId string
@description('Private DNS zone ids from private-dns.bicep; uses the blob, search and cosmos zones.')
param dnsZoneIds object

var suffix = uniqueString(resourceGroup().id, namePrefix)
var storageName = take('st${replace(namePrefix, '-', '')}${suffix}', 24)
var searchName = take('srch-${namePrefix}-${suffix}', 60)
var cosmosName = take('cosmos-${namePrefix}-${suffix}', 44)

resource storage 'Microsoft.Storage/storageAccounts@2024-01-01' = {
  name: storageName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Disabled'
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Deny'
    }
  }
}

resource search 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: searchName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'standard'
  }
  properties: {
    hostingMode: 'default'
    publicNetworkAccess: 'disabled'
    disableLocalAuth: true
  }
}

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: cosmosName
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    publicNetworkAccess: 'Disabled'
    disableLocalAuth: true
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
  }
}

module storageBlobPe 'private-endpoint.bicep' = {
  name: 'pe-${storage.name}-blob'
  params: {
    location: location
    tags: tags
    name: 'pe-${storage.name}-blob'
    subnetId: privateEndpointSubnetId
    privateLinkServiceId: storage.id
    groupId: 'blob'
    dnsZoneIds: [
      dnsZoneIds.blob
    ]
  }
}

module searchPe 'private-endpoint.bicep' = {
  name: 'pe-${search.name}'
  params: {
    location: location
    tags: tags
    name: 'pe-${search.name}'
    subnetId: privateEndpointSubnetId
    privateLinkServiceId: search.id
    groupId: 'searchService'
    dnsZoneIds: [
      dnsZoneIds.search
    ]
  }
}

module cosmosPe 'private-endpoint.bicep' = {
  name: 'pe-${cosmos.name}'
  params: {
    location: location
    tags: tags
    name: 'pe-${cosmos.name}'
    subnetId: privateEndpointSubnetId
    privateLinkServiceId: cosmos.id
    groupId: 'Sql'
    dnsZoneIds: [
      dnsZoneIds.cosmos
    ]
  }
}

output storageAccountResourceId string = storage.id
output searchServiceResourceId string = search.id
output cosmosDbResourceId string = cosmos.id

