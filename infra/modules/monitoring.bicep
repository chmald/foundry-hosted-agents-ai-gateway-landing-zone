// Monitoring foundation: Log Analytics and workspace-based Application Insights.
param location string
param tags object = {}
param workspaceName string
param appInsightsName string
param retentionInDays int = 90

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: workspaceName
  location: location
  tags: tags
  properties: {
    retentionInDays: retentionInDays
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    sku: {
      name: 'PerGB2018'
    }
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  tags: tags
  properties: {
    Application_Type: 'web'
    IngestionMode: 'LogAnalytics'
    WorkspaceResourceId: workspace.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

output logAnalyticsWorkspaceId string = workspace.id
output logAnalyticsWorkspaceName string = workspace.name
output logAnalyticsCustomerId string = workspace.properties.customerId
@secure()
output logAnalyticsSharedKey string = workspace.listKeys().primarySharedKey
output appInsightsId string = appInsights.id
output appInsightsName string = appInsights.name
@secure()
output appInsightsConnectionString string = appInsights.properties.ConnectionString
@secure()
output appInsightsInstrumentationKey string = appInsights.properties.InstrumentationKey
