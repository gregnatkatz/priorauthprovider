// Azure Functions MCP Server Deployment Template
// Denial Intelligence Platform - 42+ AI Agents as MCP Tools
// Region: eastus2

@description('The name of the function app')
param functionAppName string = 'denial-intelligence-mcp'

@description('The location for all resources')
param location string = 'eastus2'

@description('The name of the storage account')
param storageAccountName string = 'denialintelligencesa'

@description('The name of the App Service plan')
param appServicePlanName string = 'denial-intelligence-plan'

@description('The name of the Application Insights resource')
param appInsightsName string = 'denial-intelligence-insights'

@description('The name of the Azure AI Foundry project endpoint')
param projectEndpoint string

@description('The Azure subscription ID')
param subscriptionId string = 'edc5bc65-467b-4060-9bb2-285374d299df'

@description('The resource group name')
param resourceGroupName string = 'rg-gregorykatz-2103'

@description('The Azure AI Foundry project name')
param projectName string = 'pharma-agents-jnj'

@description('Azure AI Search endpoint')
param searchEndpoint string = ''

@description('Azure AI Search index name')
param searchIndexName string = 'payer-policies'

// Storage Account for Function App
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}

// Application Insights for monitoring
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    Request_Source: 'rest'
    RetentionInDays: 90
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// App Service Plan (Consumption plan for serverless)
resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: appServicePlanName
  location: location
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {
    reserved: true // Required for Linux
  }
}

// Function App
resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      pythonVersion: '3.11'
      linuxFxVersion: 'PYTHON|3.11'
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'WEBSITE_CONTENTSHARE'
          value: toLower(functionAppName)
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }
        {
          name: 'PROJECT_ENDPOINT'
          value: projectEndpoint
        }
        {
          name: 'SUBSCRIPTION_ID'
          value: subscriptionId
        }
        {
          name: 'RESOURCE_GROUP'
          value: resourceGroupName
        }
        {
          name: 'PROJECT_NAME'
          value: projectName
        }
        {
          name: 'AZURE_SEARCH_ENDPOINT'
          value: searchEndpoint
        }
        {
          name: 'AZURE_SEARCH_INDEX_NAME'
          value: searchIndexName
        }
        {
          name: 'MCP_SERVER_LABEL'
          value: 'denial-intelligence'
        }
        {
          name: 'LOG_LEVEL'
          value: 'INFO'
        }
      ]
      cors: {
        allowedOrigins: [
          'https://portal.azure.com'
          'https://ai.azure.com'
        ]
        supportCredentials: true
      }
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
    }
  }
}

// Role assignment for Function App to access Azure AI Foundry
resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(functionApp.id, 'Cognitive Services User')
  scope: functionApp
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908') // Cognitive Services User
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Outputs
output functionAppName string = functionApp.name
output functionAppUrl string = 'https://${functionApp.properties.defaultHostName}'
output mcpEndpoint string = 'https://${functionApp.properties.defaultHostName}/api/mcp'
output functionAppPrincipalId string = functionApp.identity.principalId
output appInsightsInstrumentationKey string = appInsights.properties.InstrumentationKey
