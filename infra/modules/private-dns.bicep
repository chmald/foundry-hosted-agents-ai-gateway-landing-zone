// Private DNS zones (linked to the VNet) for every private endpoint in the isolated landing zone.
// Zone names per Learn "Azure Private Endpoint private DNS zone values".
param tags object = {}
param vnetId string
param namePrefix string

var zoneNames = {
  cognitiveServices: 'privatelink.cognitiveservices.azure.com'
  openAi: 'privatelink.openai.azure.com'
  servicesAi: 'privatelink.services.ai.azure.com'
  keyVault: 'privatelink.vaultcore.azure.net'
  acr: 'privatelink.azurecr.io'
  apim: 'privatelink.azure-api.net'
  cosmos: 'privatelink.documents.azure.com'
  blob: 'privatelink.blob.${environment().suffixes.storage}'
  search: 'privatelink.search.windows.net'
}
var zoneKeys = objectKeys(zoneNames)

resource zones 'Microsoft.Network/privateDnsZones@2020-06-01' = [for key in zoneKeys: {
  name: zoneNames[key]
  location: 'global'
  tags: tags
}]

resource links 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = [for (key, i) in zoneKeys: {
  parent: zones[i]
  name: 'link-${namePrefix}'
  location: 'global'
  tags: tags
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnetId
    }
  }
}]

output zoneIds object = {
  cognitiveServices: resourceId('Microsoft.Network/privateDnsZones', zoneNames.cognitiveServices)
  openAi: resourceId('Microsoft.Network/privateDnsZones', zoneNames.openAi)
  servicesAi: resourceId('Microsoft.Network/privateDnsZones', zoneNames.servicesAi)
  keyVault: resourceId('Microsoft.Network/privateDnsZones', zoneNames.keyVault)
  acr: resourceId('Microsoft.Network/privateDnsZones', zoneNames.acr)
  apim: resourceId('Microsoft.Network/privateDnsZones', zoneNames.apim)
  cosmos: resourceId('Microsoft.Network/privateDnsZones', zoneNames.cosmos)
  blob: resourceId('Microsoft.Network/privateDnsZones', zoneNames.blob)
  search: resourceId('Microsoft.Network/privateDnsZones', zoneNames.search)
}
