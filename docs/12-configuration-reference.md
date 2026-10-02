[README](../README.md) › [docs index](./00-reproduce-this-demo.md) › 12 Configuration reference

# 12 - Configuration reference

<p>
  <img src="./assets/icons/code.svg" width="40" alt="Configuration"/>&nbsp;
  <img src="./assets/icons/subscription.svg" width="40" alt="Subscription"/>&nbsp;
  <img src="./assets/icons/api-management.svg" width="40" alt="API Management"/>&nbsp;
  <img src="./assets/icons/ai-gateway.svg" width="40" alt="AI Gateway"/>&nbsp;
  <img src="./assets/icons/virtual-network.svg" width="40" alt="Virtual Network"/>&nbsp;
  <img src="./assets/icons/foundry-models.svg" width="40" alt="Foundry models"/>&nbsp;
  <img src="./assets/icons/foundry-agent-service.svg" width="40" alt="Foundry Agent Service"/>&nbsp;
  <img src="./assets/icons/log-analytics.svg" width="40" alt="Log Analytics"/>&nbsp;
  <img src="./assets/icons/key-vault.svg" width="40" alt="Key Vault"/>
</p>

![GA](./assets/badges/ga.svg) ![Opt-in](./assets/badges/opt-in.svg) ![Preview](./assets/badges/preview.svg)

The complete configuration index for the demo. If a value is configurable, generated as an azd output, read by a hook, script or runtime component, or written to `demo-ids.local.json`, it is documented here. A test (`tests/test_configuration.py`) fails when any of them is missing.

## At a glance

| | Layer | What it holds |
|---|---|---|
| <img src="./assets/icons/subscription.svg" width="24" alt=""/> | **azd environment** | 38 input variables (target, gateway, network, model, workload, monitoring). |
| <img src="./assets/icons/resource-group.svg" width="24" alt=""/> | **azd outputs** | 29 outputs, mirrored into `demo-ids.local.json` by the postprovision hook. |
| <img src="./assets/icons/foundry-agent-service.svg" width="24" alt=""/> | **Runtime environment** | Per-component variables for hosted agents, tool backends, scripts, hooks and tests. |
| <img src="./assets/icons/code.svg" width="24" alt=""/> | **Domain profile JSON** | Labels, agent instructions, tool descriptions, seed data and walkthrough prompts. |

## How configuration flows

[![Configuration flow](./assets/configuration-flow.png)](./assets/configuration-flow.png)

<sub>Editable source: [`assets/configuration-flow.drawio`](./assets/configuration-flow.drawio) - regenerate with `python scripts/export_diagrams.py docs/assets`.</sub>

### Configuration precedence

When the same value exists in several places, the lower number wins.

| Precedence | | Source | Contents |
|---:|---|---|---|
| 1 | <img src="./assets/icons/code.svg" width="20" alt=""/> | **Process environment / command-line parameter** | Temporary script overrides such as `AIGW_RUNTIME_KEY`, `DRAWIO_EXE`, `REUSABILITY_DENYLIST`. |
| 2 | <img src="./assets/icons/subscription.svg" width="20" alt=""/> | **azd environment values** | Tenant, subscription, region, gateway modes, model, monitoring, networking. |
| 3 | <img src="./assets/icons/resource-group.svg" width="20" alt=""/> | **`demo-ids.local.json`** | Resource names, endpoints, workspace IDs, Key Vault URI, runtime discovery values. |
| 4 | <img src="./assets/icons/toolbox.svg" width="20" alt=""/> | **Domain profile JSON** | Labels, instructions, tool descriptions, seed data, walkthrough prompts. |
| 5 | <img src="./assets/icons/policy.svg" width="20" alt=""/> | **Code defaults** | Safe defaults only; never domain-specific or customer-specific values. |

> [!IMPORTANT]
> **Secrets are not configuration.** Runtime keys, tokens, connection strings and populated identifiers belong in Key Vault, managed identity, the azd secret store or ignored local files. `APPLICATIONINSIGHTS_CONNECTION_STRING` is an azd output but is deliberately **not** written to `demo-ids.local.json`.

## azd environment variables

Set a value with `azd env set <NAME> <value>`. Defaults come from `infra/azd.parameters.json`. The same variables are parameters of `infra/deploy.ps1` ([below](#deployps1-parameters)).

### <img src="./assets/icons/subscription.svg" width="28" alt=""/> Target and identity

| Variable | Default | Effect |
|---|---|---|
| `AZURE_ENV_NAME` | Set by `azd env new` | Environment slug used in resource names. |
| `AZURE_LOCATION` | `eastus2` recommended | Primary region. |
| `AZURE_SUBSCRIPTION_ID` | azd-provided | Subscription target. Keep it explicit when you work across tenants. |
| `AZURE_TENANT_ID` | azd-provided | Tenant target. |
| `AZURE_PRINCIPAL_ID` | azd-provided | Deployment principal. |
| `AZURE_PRINCIPAL_TYPE` | `User` | Role assignment principal type. |
| `AZURE_RESOURCE_GROUP` | Blank | Reuse an existing resource group, or create `rg-<env>`. |

### <img src="./assets/icons/api-management.svg" width="28" alt=""/> Gateway

| Variable | Default | Allowed values | Effect |
|---|---|---|---|
| `AI_GATEWAY_MODE` | `apimv2` | `apimv2`, `aigateway`, `both` | Deploy APIM v2, the AI Gateway tier ![Preview](./assets/badges/preview.svg), or both. |
| `APIM_SKU` | `StandardV2` | `StandardV2`, `PremiumV2` | APIM SKU. |
| `APIM_PUBLISHER_EMAIL` | `demo@example.com` | Email | APIM publisher email. |
| `APIM_PUBLISHER_NAME` | `Demo Publisher` | String | APIM publisher name. |
| `GATEWAY_APP_CLIENT_ID` | Blank | App client ID | Blank lets preprovision create `gw-<env>`. |
| `TOKEN_LIMIT_TPM_PER_AGENT` | `20000` | Integer | Token-per-minute guard per agent. It does not create model quota. |
| `ENABLE_CONTENT_SAFETY` | `true` | Boolean | Enables the content-safety control where configured. |
| `ENABLE_LLM_MESSAGE_LOGGING` | `true` | Boolean | Enables APIM LLM prompt and completion logs. Review the [privacy warning](./09-monitoring-and-audit.md#llm-message-logging-and-privacy) before production. |

### <img src="./assets/icons/ai-gateway.svg" width="28" alt=""/> AI Gateway tier ![Preview](./assets/badges/preview.svg) ![Release gated](./assets/badges/release-gated.svg)

| Variable | Default | Allowed values | Effect |
|---|---|---|---|
| `AI_GATEWAY_TIER_LOCATION` | `eastus2` | `eastus2`, `swedencentral` | Region for the AI Gateway tier; independent of `AZURE_LOCATION`. |
| `AIGW_REQUEST_LIMIT_RPM` | `120` | Integer | Request-rate policy target for the tier. |
| `AIGW_RUNTIME_KEY_SECRET_NAME` | `aigw-runtime-key` | Key Vault secret name | Secret where postprovision stores the runtime key named `agents`. |

### <img src="./assets/icons/virtual-network.svg" width="28" alt=""/> Network ![Opt-in](./assets/badges/opt-in.svg)

| Variable | Default | Effect |
|---|---|---|
| `NETWORK_ISOLATION` | `false` | Deploy the VNet and private-endpoint posture when `true` ([doc 10](./10-enterprise-posture-and-scale.md#what-network_isolationtrue-deploys)). |
| `VNET_ADDRESS_PREFIX` | `10.40.0.0/16` | VNet address space. |
| `AGENT_SUBNET_PREFIX` | `10.40.0.0/24` | Hosted-agent session subnet (`/24` recommended, `/27` minimum). |
| `ACA_SUBNET_PREFIX` | `10.40.2.0/23` | Container Apps subnet. |
| `APIM_SUBNET_PREFIX` | `10.40.4.0/27` | APIM outbound integration subnet. |
| `PE_SUBNET_PREFIX` | `10.40.5.0/24` | Private endpoint subnet. |

### <img src="./assets/icons/foundry-models.svg" width="28" alt=""/> Models

| Variable | Default | Effect |
|---|---|---|
| `MODEL_NAME` | `gpt-5.5` | Model name. |
| `MODEL_VERSION` | `2026-04-24` | Model version. |
| `MODEL_DEPLOYMENT_NAME` | `chat` | Deployment name used by the gateways and agents. |
| `MODEL_SKU` | `GlobalStandard` | Model deployment SKU ([deployment types](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/deployment-types)). |
| `MODEL_CAPACITY` | `50` | Model capacity parameter. |

### <img src="./assets/icons/foundry-agent-service.svg" width="28" alt=""/> Agents and workload

| Variable | Default | Effect |
|---|---|---|
| `DOMAIN_PROFILE` | `manufacturing-field-ops` | Selects the domain profile and seed data. |
| `DEPLOY_AGENT_ON_ACA` | `false` | Optional Container Apps comparison runtime for the agent. |
| `SEED_SAMPLE_DATA` | `true` | Seed the profile's sample data. |

### <img src="./assets/icons/log-analytics.svg" width="28" alt=""/> Monitoring

| Variable | Default | Effect |
|---|---|---|
| `LOG_RETENTION_DAYS` | `90` | Log Analytics retention in days. |
| `ENABLE_ALERTS` | `true` | Scheduled-query alerts. |
| `ALERT_EMAIL` | Blank | Optional action-group email. |
| `ENABLE_ACTIVITY_LOG_EXPORT` | `false` | Subscription Activity Log export ![Opt-in](./assets/badges/opt-in.svg). |
| `ENABLE_SENTINEL` | `false` | Optional Microsoft Sentinel onboarding ![Opt-in](./assets/badges/opt-in.svg). |
| `ENABLE_ENTRA_DIAGNOSTICS` | `false` | Optional tenant diagnostic export for Entra sign-in logs ![Opt-in](./assets/badges/opt-in.svg). |

## azd outputs to `demo-ids.local.json`

<img src="./assets/icons/resource-group.svg" width="28" alt=""/> The postprovision hook writes the azd outputs to `demo-ids.local.json` (ignored by git). Scripts read that file instead of querying Azure.

| | azd output | `demo-ids.local.json` key | Notes |
|---|---|---|---|
| <img src="./assets/icons/resource-group.svg" width="20" alt=""/> | `AZURE_RESOURCE_GROUP` | `resourceGroup` | Resource group. |
| <img src="./assets/icons/foundry.svg" width="20" alt=""/> | `FOUNDRY_ACCOUNT_NAME` | `foundryAccountName` | Foundry account. |
| <img src="./assets/icons/foundry-project.svg" width="20" alt=""/> | `FOUNDRY_PROJECT_NAME` | `foundryProjectName` | Foundry project. |
| <img src="./assets/icons/foundry-project.svg" width="20" alt=""/> | `FOUNDRY_PROJECT_ENDPOINT` | `foundryProjectEndpoint` | Project endpoint. |
| <img src="./assets/icons/foundry-models.svg" width="20" alt=""/> | `MODEL_DEPLOYMENT_NAME` | `modelDeploymentName` | Model deployment. |
| <img src="./assets/icons/container-registry.svg" width="20" alt=""/> | `AZURE_CONTAINER_REGISTRY_ENDPOINT` | `containerRegistryEndpoint` | Container registry endpoint. |
| <img src="./assets/icons/container-apps-environment.svg" width="20" alt=""/> | `CONTAINER_APPS_ENVIRONMENT_NAME` | `containerAppsEnvironmentName` | Container Apps environment. |
| <img src="./assets/icons/api-management.svg" width="20" alt=""/> | `APIM_NAME` | `apimName` | APIM service. |
| <img src="./assets/icons/api-management.svg" width="20" alt=""/> | `APIM_GATEWAY_URL` | `apimGatewayUrl` | APIM base URL. |
| <img src="./assets/icons/ai-gateway.svg" width="20" alt=""/> | `AI_GATEWAY_MODE` | `aiGatewayMode` | `apimv2`, `aigateway` or `both`. |
| <img src="./assets/icons/ai-gateway.svg" width="20" alt=""/> | `AIGW_GATEWAY_NAME` | `aigwGatewayName` | AI Gateway tier name; blank when not deployed. |
| <img src="./assets/icons/ai-gateway.svg" width="20" alt=""/> | `AIGW_GATEWAY_URL` | `aigwGatewayUrl` | AI Gateway tier base URL. |
| <img src="./assets/icons/ai-gateway.svg" width="20" alt=""/> | `AIGW_LOCATION` | `aigwLocation` | AI Gateway tier region. |
| <img src="./assets/icons/toolbox.svg" width="20" alt=""/> | `AIGW_MCP_CATALOG_URL` | `aigwMcpCatalogUrl` | Preview catalog MCP tool-server URL. |
| <img src="./assets/icons/toolbox.svg" width="20" alt=""/> | `AIGW_MCP_RECORDS_URL` | `aigwMcpRecordsUrl` | Preview records MCP tool-server URL. |
| <img src="./assets/icons/api-management.svg" width="20" alt=""/> | `LLM_API_PATH` | `llmApiPath` | APIM LLM path, default `llm`. |
| <img src="./assets/icons/toolbox.svg" width="20" alt=""/> | `MCP_CATALOG_URL` | `mcpCatalogUrl` | APIM catalog MCP URL. |
| <img src="./assets/icons/toolbox.svg" width="20" alt=""/> | `MCP_RECORDS_URL` | `mcpRecordsUrl` | APIM records MCP URL. |
| <img src="./assets/icons/container-apps.svg" width="20" alt=""/> | `RECORDS_API_URL` | `recordsApiUrl` | APIM records REST URL. |
| <img src="./assets/icons/app-registrations.svg" width="20" alt=""/> | `GATEWAY_APP_CLIENT_ID` | `gatewayAppClientId` | Entra gateway app. |
| <img src="./assets/icons/log-analytics.svg" width="20" alt=""/> | `LOG_ANALYTICS_WORKSPACE_ID` | `logAnalyticsWorkspaceId` | Workspace resource ID. |
| <img src="./assets/icons/log-analytics.svg" width="20" alt=""/> | `LOG_ANALYTICS_CUSTOMER_ID` | `logAnalyticsCustomerId` | Workspace customer ID. |
| <img src="./assets/icons/application-insights.svg" width="20" alt=""/> | `APPLICATIONINSIGHTS_NAME` | `applicationInsightsName` | Application Insights component. |
| <img src="./assets/icons/application-insights.svg" width="20" alt=""/> | `APPLICATIONINSIGHTS_CONNECTION_STRING` | Not written to IDs file | Secret-like; keep in azd or app settings. |
| <img src="./assets/icons/workbooks.svg" width="20" alt=""/> | `WORKBOOK_ID` | `workbookId` | Workbook ID. |
| <img src="./assets/icons/query-pack.svg" width="20" alt=""/> | `QUERY_PACK_ID` | `queryPackId` | Query pack ID. |
| <img src="./assets/icons/key-vault.svg" width="20" alt=""/> | `KEY_VAULT_NAME` | `keyVaultName` | Key Vault name. |
| <img src="./assets/icons/key-vault.svg" width="20" alt=""/> | `KEY_VAULT_URI` | `keyVaultUri` | Key Vault URI for runtime secret reads. |
| <img src="./assets/icons/virtual-network.svg" width="20" alt=""/> | `VNET_ID` | `vnetId` | Empty when there is no isolation. |

### All `demo-ids.local.json` keys

<details><summary><b>Show the complete key list</b></summary>

`resourceGroup`, `foundryAccountName`, `foundryProjectName`, `foundryProjectEndpoint`, `modelDeploymentName`, `containerRegistryEndpoint`, `containerAppsEnvironmentName`, `apimName`, `apimGatewayUrl`, `aiGatewayMode`, `aigwGatewayName`, `aigwGatewayUrl`, `aigwLocation`, `aigwMcpCatalogUrl`, `aigwMcpRecordsUrl`, `llmApiPath`, `mcpCatalogUrl`, `mcpRecordsUrl`, `recordsApiUrl`, `gatewayAppClientId`, `logAnalyticsWorkspaceId`, `logAnalyticsCustomerId`, `applicationInsightsName`, `workbookId`, `queryPackId`, `keyVaultName`, `keyVaultUri`, `vnetId`, optional `hostedAgentUrl`, optional `agentMafResponsesEndpoint`, optional `agentLanggraphResponsesEndpoint`, `workload.domainProfile`, and `workload.profilePath`.

</details>

## `deploy.ps1` parameters

<img src="./assets/icons/code.svg" width="28" alt=""/> `infra/deploy.ps1` is the manual alternative to `azd up`: it validates the environment name, the Azure tenant and subscription context, `AI_GATEWAY_MODE` (`apimv2`, `aigateway`, `both`) and the tier location, then runs `az deployment sub create` against `infra/azd.bicep` with the deployment name `foundry-hosted-agents-<EnvironmentName>`. Each parameter defaults to the environment variable of the same azd name.

| Group | Parameters |
|---|---|
| <img src="./assets/icons/subscription.svg" width="20" alt=""/> **Target and identity** | `-EnvironmentName`, `-AzureLocation`, `-AzureSubscriptionId`, `-AzureTenantId`, `-AzurePrincipalId`, `-AzurePrincipalType`, `-AzureResourceGroup` |
| <img src="./assets/icons/api-management.svg" width="20" alt=""/> **Gateway** | `-AiGatewayMode`, `-ApimSku`, `-ApimPublisherEmail`, `-ApimPublisherName`, `-GatewayAppClientId`, `-TokenLimitTpmPerAgent`, `-EnableContentSafety`, `-EnableLlmMessageLogging` |
| <img src="./assets/icons/ai-gateway.svg" width="20" alt=""/> **AI Gateway tier** | `-AiGatewayTierLocation`, `-AigwRequestLimitRpm`, `-AigwRuntimeKeySecretName` |
| <img src="./assets/icons/virtual-network.svg" width="20" alt=""/> **Network** | `-NetworkIsolation`, `-VnetAddressPrefix`, `-AgentSubnetPrefix`, `-AcaSubnetPrefix`, `-ApimSubnetPrefix`, `-PeSubnetPrefix` |
| <img src="./assets/icons/foundry-models.svg" width="20" alt=""/> **Models** | `-ModelName`, `-ModelVersion`, `-ModelDeploymentName`, `-ModelSku`, `-ModelCapacity` |
| <img src="./assets/icons/foundry-agent-service.svg" width="20" alt=""/> **Agents and workload** | `-DomainProfile`, `-DeployAgentOnAca`, `-SeedSampleData` |
| <img src="./assets/icons/log-analytics.svg" width="20" alt=""/> **Monitoring** | `-LogRetentionDays`, `-EnableAlerts`, `-AlertEmail`, `-EnableActivityLogExport`, `-EnableSentinel`, `-EnableEntraDiagnostics` |

## Runtime environment variables

Names are grouped by the component that reads them. Hosted agents get their values from `azure.yaml`, where the platform-injected names carry a `DD_` prefix; the code reads the `DD_` name first and falls back to the unprefixed one.

### <img src="./assets/icons/foundry-agent-service.svg" width="28" alt=""/> Hosted agents (`agent-maf`, `agent-langgraph`)

| Variable | Purpose |
|---|---|
| `AGENT_DEFAULT_GATEWAY` | `apimv2` or `aigateway`; selects the runtime path. |
| `DD_AGENT_DEFAULT_GATEWAY` | Prefixed form set in `azure.yaml` from `${AGENT_DEFAULT_GATEWAY}`; read before the unprefixed name. |
| `APIM_GATEWAY_URL` | APIM base URL. |
| `LLM_API_PATH` | APIM LLM route path. |
| `MCP_CATALOG_URL` | APIM catalog MCP URL. |
| `MCP_RECORDS_URL` | APIM records MCP URL. |
| `GATEWAY_AUDIENCE` | APIM token audience. |
| `AIGW_GATEWAY_URL` | AI Gateway tier base URL. |
| `AIGW_MCP_CATALOG_URL` | AI Gateway tier catalog MCP URL. |
| `AIGW_MCP_RECORDS_URL` | AI Gateway tier records MCP URL. |
| `KEY_VAULT_URI` | Key Vault URI used to read the runtime key. |
| `AIGW_RUNTIME_KEY_SECRET_NAME` | Secret name for the AI Gateway runtime key. |
| `AIGW_RUNTIME_KEY` | Local-only fallback for diagnostics; never commit. |
| `MODEL_DEPLOYMENT_NAME` | Model deployment name. |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | Foundry-injected model variable (MAF). |
| `FOUNDRY_MODEL_NAME` | Foundry-injected model variable (LangGraph). |
| `FOUNDRY_PROJECT_ENDPOINT` | Foundry project endpoint. |
| `DOMAIN_PROFILE` | Profile selector. |
| `AGENT_PROTOCOL` | `responses` or `invocations`. |
| `DD_AGENT_PROTOCOL` | Prefixed form set in `azure.yaml`; the value is `responses`. |
| `AGENT_RUNTIME` | `foundry-hosted`, `aca` or `local`. |
| `DD_AGENT_RUNTIME` | Prefixed form set in `azure.yaml`; the value is `foundry-hosted`. |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Application Insights exporter. |
| `DD_APPLICATIONINSIGHTS_CONNECTION_STRING` | Prefixed form set in `azure.yaml` from `${APPLICATIONINSIGHTS_CONNECTION_STRING}`. |
| `PORT` | Container port. |
| `FHAGL_USE_FASTAPI_FALLBACK` | Local diagnostic fallback flag. |

### <img src="./assets/icons/container-apps.svg" width="28" alt=""/> Tool backends (`catalog-mcp`, `records-api`)

| Variable | Purpose |
|---|---|
| `PORT` | Container port (`8080`). |
| `LOG_LEVEL` | Runtime logging verbosity. |
| `DOMAIN_PROFILE` | Profile selector for seed data. |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Application Insights exporter. |

### <img src="./assets/icons/code.svg" width="28" alt=""/> Scripts, hooks and tests

| Variable | Used by | Purpose |
|---|---|---|
| `AZURE_TENANT_ID` | Scripts and hooks | Tenant-explicit authentication. |
| `AZURE_SUBSCRIPTION_ID` | Scripts and hooks | Subscription-explicit authentication. |
| `LOG_ANALYTICS_CUSTOMER_ID` | `run_audit_queries.py` | Workspace customer ID. |
| `DRAWIO_EXE` | `export_diagrams.py` | draw.io executable override. |
| `REUSABILITY_DENYLIST` | Tests | Runtime denylist for customer-specific terms. |
| `AGENT_AGENT_MAF_RESPONSES_ENDPOINT` | `demo_walkthrough.py` | Explicit MAF endpoint override. |
| `AGENT_AGENT_LANGGRAPH_RESPONSES_ENDPOINT` | `demo_walkthrough.py` | Explicit LangGraph endpoint override. |

## Domain profile JSON

<img src="./assets/icons/toolbox.svg" width="28" alt=""/> A profile in `config/profiles/<name>.json` carries everything domain-specific, so retargeting the demo never touches code.

| Key | Contains |
|---|---|
| `profileName`, `displayName` | Identifier and display name. |
| `agent` | `name`, `description`, `instructions` for the agent. |
| `labels` | Singular and plural nouns for items and records, used in prompts and docs. |
| `catalogTools` | Tool name to description: `list_items`, `search_items`, `get_item`, `check_availability`, `check_availability_batch`. |
| `recordsTools` | Tool name to description: `list_records`, `get_record`, `create_record`, `update_record`. |
| `seedData` | Paths to the items and records seed files. |
| `walkthrough[]` | Prompts for the demo: `step`, `segment`, `prompt`, `expectedTool`, `assertion`. |

<details><summary><b>Show a profile skeleton</b></summary>

```json
{
  "profileName": "manufacturing-field-ops",
  "displayName": "Manufacturing field operations",
  "agent": { "name": "FieldOpsGatewayAgent", "description": "...", "instructions": "..." },
  "labels": { "item": "part", "items": "parts", "record": "work order", "records": "work orders" },
  "catalogTools": { "list_items": "...", "check_availability": "..." },
  "recordsTools": { "list_records": "...", "create_record": "..." },
  "seedData": {
    "items": "src/catalog-mcp/data/profiles/manufacturing-field-ops/items.json",
    "records": "src/records-api/data/profiles/manufacturing-field-ops/records.json"
  },
  "walkthrough": [
    { "step": "S3", "segment": "Tools / MCP", "prompt": "...", "expectedTool": "check_availability", "assertion": "..." }
  ]
}
```

Values are shortened here; the real profile lists every tool in `catalogTools` and `recordsTools`.

</details>

## Recipes

| | Goal | Configuration change |
|---|---|---|
| <img src="./assets/icons/ai-gateway.svg" width="24" alt=""/> | **Deploy both gateways** | `azd env set AI_GATEWAY_MODE both`; `azd env set AI_GATEWAY_TIER_LOCATION eastus2`. |
| <img src="./assets/icons/api-management.svg" width="24" alt=""/> | **Use APIM v2 for agents** | `azd env set AGENT_DEFAULT_GATEWAY apimv2`; `azd deploy agent-maf agent-langgraph`. |
| <img src="./assets/icons/ai-gateway.svg" width="24" alt=""/> | **Use the AI Gateway tier for agents** | `azd env set AGENT_DEFAULT_GATEWAY aigateway`; confirm the Key Vault runtime key; `azd deploy agent-maf agent-langgraph`. |
| <img src="./assets/icons/api-management.svg" width="24" alt=""/> | **Validate APIM** | `python scripts/validate_gateway.py --ids demo-ids.local.json --target apimv2`. |
| <img src="./assets/icons/ai-gateway.svg" width="24" alt=""/> | **Validate the AI Gateway tier** | `python scripts/validate_gateway.py --ids demo-ids.local.json --target aigateway`. |
| <img src="./assets/icons/toolbox.svg" width="24" alt=""/> | **Retarget the domain** | Add the profile JSON and seed data, then `azd env set DOMAIN_PROFILE <new-profile>` and run `scripts/sync-agent-profiles.ps1`. |

> [!TIP]
> After any change to a gateway variable, redeploy the hosted agents (`azd deploy agent-maf agent-langgraph`). Their environment is fixed at deploy time, so a changed value is not picked up by running sessions.

Next: back to the [docs index](./00-reproduce-this-demo.md) →

---

*Last updated: 2026-10-02*
