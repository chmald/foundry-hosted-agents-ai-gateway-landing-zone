// Private-mode BYO dependencies for Microsoft Foundry standard private-networking setup.
param location string
param tags object = {}
param namePrefix string
param vnetId string
param privateEndpointSubnetId string

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

resource storageBlobPe 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: 'pe-${storage.name}-blob'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: privateEndpointSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'blob'
        properties: {
          privateLinkServiceId: storage.id
          groupIds: [
            'blob'
          ]
        }
      }
    ]
  }
}

resource searchPe 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: 'pe-${search.name}'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: privateEndpointSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'search'
        properties: {
          privateLinkServiceId: search.id
          groupIds: [
            'searchService'
          ]
        }
      }
    ]
  }
}

resource cosmosPe 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: 'pe-${cosmos.name}'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: privateEndpointSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'cosmos'
        properties: {
          privateLinkServiceId: cosmos.id
          groupIds: [
            'Sql'
          ]
        }
      }
    ]
  }
}

output storageAccountResourceId string = storage.id
output searchServiceResourceId string = search.id
output cosmosDbResourceId string = cosmos.id

