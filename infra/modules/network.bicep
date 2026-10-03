// Private-mode virtual network with dedicated subnets for hosted-agent dependencies, ACA, APIM, and private endpoints.
param location string
param tags object = {}
param namePrefix string
param vnetAddressPrefix string
param agentSubnetPrefix string
param acaSubnetPrefix string
param apimSubnetPrefix string
param peSubnetPrefix string
@description('Dedicated /27+ subnet for AI Gateway tier outbound VNet integration (delegated Microsoft.Web/serverFarms).')
param aigwSubnetPrefix string = '10.40.6.0/27'

// AI Gateway tier outbound integration requires an NSG that allows 443 to Storage and Key Vault service tags.
resource aigwNsg 'Microsoft.Network/networkSecurityGroups@2024-05-01' = {
  name: 'nsg-aigw-outbound-${namePrefix}'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'AllowOutboundHttpsToStorage'
        properties: {
          priority: 100
          direction: 'Outbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: 'Storage'
        }
      }
      {
        name: 'AllowOutboundHttpsToKeyVault'
        properties: {
          priority: 110
          direction: 'Outbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: 'AzureKeyVault'
        }
      }
    ]
  }
}

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
        name: 'snet-aigw'
        properties: {
          addressPrefix: aigwSubnetPrefix
          networkSecurityGroup: {
            id: aigwNsg.id
          }
          delegations: [
            {
              name: 'aigw-outbound-delegation'
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
output aigwSubnetId string = '${vnet.id}/subnets/snet-aigw'
output privateEndpointSubnetId string = '${vnet.id}/subnets/snet-private-endpoints'

