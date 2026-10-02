// Private-mode virtual network with dedicated subnets for hosted-agent dependencies, ACA, APIM, and private endpoints.
param location string
param tags object = {}
param namePrefix string
param vnetAddressPrefix string
param agentSubnetPrefix string
param acaSubnetPrefix string
param apimSubnetPrefix string
param peSubnetPrefix string

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: 'vnet-${namePrefix}'
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        vnetAddressPrefix
      ]
    }
    subnets: [
      {
        name: 'snet-agent'
        properties: {
          addressPrefix: agentSubnetPrefix
          delegations: [
            {
              name: 'agent-aca-delegation'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
        }
      }
      {
        name: 'snet-aca'
        properties: {
          addressPrefix: acaSubnetPrefix
          delegations: [
            {
              name: 'aca-delegation'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
        }
      }
      {
        name: 'snet-apim'
        properties: {
          addressPrefix: apimSubnetPrefix
          delegations: [
            {
              name: 'apim-v2-outbound-delegation'
              properties: {
                serviceName: 'Microsoft.Web/serverFarms'
              }
            }
          ]
        }
      }
      {
        name: 'snet-private-endpoints'
        properties: {
          addressPrefix: peSubnetPrefix
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
    ]
  }
}

output vnetId string = vnet.id
output agentSubnetId string = '${vnet.id}/subnets/snet-agent'
output acaSubnetId string = '${vnet.id}/subnets/snet-aca'
output apimSubnetId string = '${vnet.id}/subnets/snet-apim'
output privateEndpointSubnetId string = '${vnet.id}/subnets/snet-private-endpoints'

