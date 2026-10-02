// Scheduled query alerts for throttling, denied tools, gateway 5xx, content-safety blocks, and optional Entra failures.
param location string
param tags object = {}
param logAnalyticsWorkspaceId string
param alertEmail string = ''
param enableEntraDiagnostics bool = false

resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = if (!empty(alertEmail)) {
  name: 'ag-hosted-agent-gateway'
  location: 'global'
  tags: tags
  properties: {
    groupShortName: 'agentgw'
    enabled: true
    emailReceivers: [
      {
        name: 'operator'
        emailAddress: alertEmail
        useCommonAlertSchema: true
      }
    ]
  }
}

var actionGroups = empty(alertEmail) ? [] : [
  actionGroup.id
]

var alertDefinitions = [
  {
    name: 'token-limit-throttling-spike'
    description: '429 responses on LLM API increased.'
    query: 'ApiManagementGatewayLogs | where TimeGenerated > ago(15m) | where ResponseCode == 429 and ApiId has "llm" | summarize Count=count()'
    threshold: 5
  }
  {
    name: 'denied-tool-calls'
    description: 'Denied tool calls or auth failures on MCP endpoints.'
    query: 'union isfuzzy=true ApiManagementGatewayMCPLog, ApiManagementGatewayLogs | where TimeGenerated > ago(15m) | where tostring(Error) has "Forbidden" or ResponseCode in (401,403) | summarize Count=count()'
    threshold: 1
  }
  {
    name: 'gateway-5xx-rate'
    description: 'Gateway 5xx responses increased.'
    query: 'ApiManagementGatewayLogs | where TimeGenerated > ago(15m) | where ResponseCode between (500 .. 599) | summarize Count=count()'
    threshold: 3
  }
  {
    name: 'content-safety-blocks'
    description: 'Content-safety policy blocked requests.'
    query: 'ApiManagementGatewayLogs | where TimeGenerated > ago(15m) | extend ErrorText=tostring(column_ifexists("ErrorMessage", "")), BackendCode=toint(column_ifexists("BackendResponseCode", int(null))) | where ErrorText has "content" or BackendCode == 403 | summarize Count=count()'
    threshold: 1
  }
]

resource scheduledAlerts 'Microsoft.Insights/scheduledQueryRules@2022-06-15' = [for alert in alertDefinitions: {
  name: alert.name
  location: location
  tags: tags
  properties: {
    displayName: alert.name
    description: alert.description
    enabled: true
    severity: 2
    scopes: [
      logAnalyticsWorkspaceId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      allOf: [
        {
          query: alert.query
          timeAggregation: 'Total'
          metricMeasureColumn: 'Count'
          operator: 'GreaterThanOrEqual'
          threshold: alert.threshold
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    actions: {
      actionGroups: actionGroups
    }
  }
}]

resource entraFailures 'Microsoft.Insights/scheduledQueryRules@2022-06-15' = if (enableEntraDiagnostics) {
  name: 'agent-sign-in-failures'
  location: location
  tags: tags
  properties: {
    displayName: 'Agent sign-in failures'
    description: 'Service principal or managed identity sign-in failures for agent identities.'
    enabled: true
    severity: 2
    scopes: [
      logAnalyticsWorkspaceId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      allOf: [
        {
          query: 'union isfuzzy=true AADServicePrincipalSignInLogs, AADManagedIdentitySignInLogs | where TimeGenerated > ago(15m) | where ResultType != 0 | summarize Count=count()'
          timeAggregation: 'Total'
          metricMeasureColumn: 'Count'
          operator: 'GreaterThanOrEqual'
          threshold: 1
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    actions: {
      actionGroups: actionGroups
    }
  }
}

output alertCount int = length(alertDefinitions) + (enableEntraDiagnostics ? 1 : 0)
