// Azure Monitor Workbook showing token, tool, denial, latency, trace, and LLM-log tiles.
param location string
param tags object = {}
param workbookDisplayName string
param logAnalyticsWorkspaceId string

resource workbook 'Microsoft.Insights/workbooks@2022-04-01' = {
  name: guid(resourceGroup().id, workbookDisplayName)
  location: location
  tags: tags
  kind: 'shared'
  properties: {
    displayName: workbookDisplayName
    category: 'workbook'
    sourceId: logAnalyticsWorkspaceId
    serializedData: loadTextContent('../monitoring/workbook.json')
    version: 'Notebook/1.0'
  }
}

output workbookId string = workbook.id

