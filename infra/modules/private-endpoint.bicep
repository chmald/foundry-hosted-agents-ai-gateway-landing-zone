// Generic private endpoint + private DNS zone group.
param location string
param tags object = {}
param name string
param subnetId string
param privateLinkServiceId string
@description('Target sub-resource, e.g. account, vault, registry, Gateway, Sql, blob, searchService.')
param groupId string
@description('Private DNS zone resource ids to register the endpoint in (one config per zone).')
param dnsZoneIds array

resource pe 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    subnet: {
      id: subnetId
    }
    privateLinkServiceConnections: [
      {
        name: groupId
        properties: {
          privateLinkServiceId: privateLinkServiceId
          groupIds: [
            groupId
          ]
        }
      }
    ]
  }
}

resource dnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = {
  parent: pe
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [for zoneId in dnsZoneIds: {
      name: replace(last(split(zoneId, '/')), '.', '-')
      properties: {
        privateDnsZoneId: zoneId
      }
    }]
  }
}

output privateEndpointId string = pe.id
