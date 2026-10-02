// Optional Microsoft Sentinel onboarding for the Log Analytics workspace.
param logAnalyticsWorkspaceName string

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: logAnalyticsWorkspaceName
}

resource onboarding 'Microsoft.SecurityInsights/onboardingStates@2023-02-01' = {
  scope: workspace
  name: 'default'
  properties: {
    customerManagedKey: false
  }
}

output onboardingStateId string = onboarding.id

