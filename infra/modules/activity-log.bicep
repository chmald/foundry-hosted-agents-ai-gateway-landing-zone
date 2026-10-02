// Optional subscription Activity Log export to the demo Log Analytics workspace.
targetScope = 'subscription'

param logAnalyticsWorkspaceId string

resource subscriptionActivityLog 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'activity-log-to-hosted-agent-gateway-law'
  scope: subscription()
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        category: 'Administrative'
        enabled: true
      }
      {
        category: 'Security'
        enabled: true
      }
      {
        category: 'Policy'
        enabled: true
      }
      {
        category: 'ResourceHealth'
        enabled: true
      }
      {
        category: 'Recommendation'
        enabled: true
      }
    ]
  }
}

output diagnosticSettingId string = subscriptionActivityLog.id

