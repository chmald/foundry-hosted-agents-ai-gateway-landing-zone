[README](../README.md) › [docs index](./00-reproduce-this-demo.md) › 03 Deployment

# 03 - Deployment

<p>
  <img src="./assets/icons/azure-devops.svg" width="40" alt="azd">
  <img src="./assets/icons/api-management.svg" width="40" alt="API Management">
  <img src="./assets/icons/ai-gateway.svg" width="40" alt="AI Gateway">
  <img src="./assets/icons/foundry-agent-service.svg" width="40" alt="Foundry Agent Service">
  <img src="./assets/icons/container-apps.svg" width="40" alt="Container Apps">
  <img src="./assets/icons/key-vault.svg" width="40" alt="Key Vault">
</p>

<p>
  <img src="./assets/badges/version.svg" alt="pattern: v1.1.0">
  <img src="./assets/badges/default.svg" alt="default: APIM v2">
  <img src="./assets/badges/public-preview.svg" alt="AI Gateway tier: public preview">
  <img src="./assets/badges/static-only.svg" alt="validation: static only">
</p>

Deployment runbook for the primary infrastructure-as-code path. v1.1 can deploy **both** APIM Standard v2 and the AI Gateway tier preview side by side for comparison, while keeping APIM v2 as the safe runtime baseline. For a no-IaC build, see [03b - Manual deployment](./03b-manual-deployment.md).

## At a glance

| | | |
|---|---|---|
| <img src="./assets/icons/azure-devops.svg" width="24" alt=""> | **Tool** | `azd up` with `preprovision` / `postprovision` hooks |
| <img src="./assets/icons/api-management.svg" width="24" alt=""> | **Pass 1** | Agents point at APIM v2 (`AGENT_DEFAULT_GATEWAY=apimv2`) |
| <img src="./assets/icons/ai-gateway.svg" width="24" alt=""> | **Pass 2** | Flip to `aigateway`, then `azd deploy agent-maf agent-langgraph` |
| <img src="./assets/icons/foundry-agent-service.svg" width="24" alt=""> | **Agents** | `agent-maf` and `agent-langgraph`, `host: azure.ai.agent`, `remoteBuild: true` |
| <img src="./assets/icons/resource-group.svg" width="24" alt=""> | **Cleanup** | `azd down --purge` |

> [!WARNING]
> **Phase 0 is not optional.** This workstation can hold several Azure tenants and subscriptions, and `az` and `azd` keep **separate** logins. Always run `az login --tenant` **and** `azd auth login --tenant-id`, then confirm with `az account show` before any provisioning. A bare `azd up` can target the wrong tenant or subscription.

## Fast path - `azd up` with both gateways

[![azd deployment flow](./assets/azd-deployment-flow.png)](./assets/azd-deployment-flow.png)

<sub>Editable source: [`assets/azd-deployment-flow.drawio`](./assets/azd-deployment-flow.drawio) - regenerate with `python scripts/export_diagrams.py docs/assets`.</sub>

| Step | | Action | Gate |
|---|---|---|---|
| **0** | <img src="./assets/icons/entra-id.svg" width="28" alt=""> | Authenticate to the right tenant (az **and** azd) | - [ ] `az account show` matches the target |
| **1** | <img src="./assets/icons/diagnostic-settings.svg" width="28" alt=""> | Configure deployment knobs with `azd env set` | - [ ] `azd env get-values` reviewed |
| **2** | <img src="./assets/icons/azure-devops.svg" width="28" alt=""> | `azd provision --preview`, then `azd up` | - [ ] Hooks pass, resources created |
| **3** | <img src="./assets/icons/api-management.svg" width="28" alt=""> | Validate both gateway routes | - [ ] `validate_gateway.py` reports no failed checks |
| **4** | <img src="./assets/icons/ai-gateway.svg" width="28" alt=""> | Switch hosted agents to the AI Gateway tier | - [ ] Agents redeployed with `aigateway` |

### Phase 0 - Authenticate to the right tenant

<img src="./assets/icons/entra-id.svg" width="20" alt=""> Resolve the intended tenant and subscription first (ask if unknown - never guess), then:

```powershell
$tenant = "<TENANT_ID>"
$subscription = "<SUBSCRIPTION_ID>"
$envName = "<ENV_NAME>"   # lowercase, <= 20 characters

azd auth login --tenant-id $tenant
az login --tenant $tenant
az account set --subscription $subscription
az account show --query "{tenant:tenantId, subscription:id, subName:name, user:user.name}" -o table

azd env new $envName
azd env set AZURE_TENANT_ID $tenant
azd env set AZURE_SUBSCRIPTION_ID $subscription
azd env set AZURE_LOCATION eastus2
```

> [!NOTE]
> `preprovision` re-checks that `az account show` matches the azd environment's tenant and subscription and stops if it does not.

### Phase 1 - Configure deployment knobs

<img src="./assets/icons/diagnostic-settings.svg" width="20" alt=""> Defaults live in `infra/azd.parameters.json`; this block sets the comparison (`both`) configuration.

```powershell
azd env set AI_GATEWAY_MODE both
azd env set AI_GATEWAY_TIER_LOCATION eastus2
azd env set AIGW_REQUEST_LIMIT_RPM 120
azd env set AIGW_RUNTIME_KEY_SECRET_NAME aigw-runtime-key
azd env set AGENT_DEFAULT_GATEWAY apimv2
azd env set APIM_SKU StandardV2
azd env set APIM_PUBLISHER_EMAIL <you@example.com>
azd env set APIM_PUBLISHER_NAME "Demo Publisher"
azd env set MODEL_NAME gpt-5.5
azd env set MODEL_VERSION 2026-04-24
azd env set MODEL_DEPLOYMENT_NAME chat
azd env set MODEL_SKU GlobalStandard
azd env set MODEL_CAPACITY 50
azd env set DOMAIN_PROFILE manufacturing-field-ops
```

| Knob | Values | Effect |
|---|---|---|
| `AI_GATEWAY_MODE` | `apimv2` (default) · `aigateway` · `both` | Which gateway resources are deployed. |
| `AI_GATEWAY_TIER_LOCATION` | `eastus2` · `swedencentral` | Preview tier region (see [02](./02-prerequisites.md#ai-gateway-tier-region-matrix)). |
| `AGENT_DEFAULT_GATEWAY` | `apimv2` · `aigateway` | Which gateway the hosted agents call. |
| `APIM_SKU` | `StandardV2` (default) · `PremiumV2` | APIM v2 tier. |
| `NETWORK_ISOLATION` | `false` (default) · `true` | Adds VNet `10.40.0.0/16`, delegated subnets, private endpoints. |
| `DEPLOY_AGENT_ON_ACA` | `false` (default) | Optional second runtime on Container Apps. |

Full reference: [12 - Configuration reference](./12-configuration-reference.md).

### Phase 2 - Preview and deploy

<img src="./assets/icons/azure-devops.svg" width="20" alt=""> Preview first, then deploy:

```powershell
azd provision --preview
azd up
```

#### What each hook does

| | Hook | v1.1 responsibilities |
|---|---|---|
| <img src="./assets/icons/policy.svg" width="20" alt=""> | `preprovision` | Validates the environment name (≤ 20 chars), tenant/subscription context, `AI_GATEWAY_MODE=apimv2\|aigateway\|both`, AI Gateway tier region (`eastus2\|swedencentral`), APIM SKU, and the network toggle. Ensures the gateway Entra app `gw-<env>` exists when `GATEWAY_APP_CLIENT_ID` is blank. Runs the soft-delete prompts for previously deleted Key Vault / Foundry / APIM names. |
| <img src="./assets/icons/key-vault.svg" width="20" alt=""> | `postprovision` | Writes `demo-ids.local.json`. When `ENABLE_ENTRA_DIAGNOSTICS=true`, runs `scripts/Enable-EntraDiagnostics.ps1`. If the AI Gateway tier is deployed, calls `.../apiKeys/agents/listSecrets?api-version=2026-05-01-preview` and stores the runtime key in Key Vault as `AIGW_RUNTIME_KEY_SECRET_NAME` (prints a portal fallback if the preview API shape differs). Reminds you to register the APIM v2 gateway in the Foundry portal (**Manage > AI Gateway > Register existing API Management gateway**). |

> [!NOTE]
> The hooks do **not** seed sample data. The tool services ship their own demo data, so no seeding step is needed.

> [!TIP]
> The agent services receive their environment through `azure.yaml` with a `DD_` prefix (for example `DD_AGENT_DEFAULT_GATEWAY` is projected from the azd value `AGENT_DEFAULT_GATEWAY`). Change the azd value, then redeploy the agents.

### Phase 3 - Validate both gateway routes

<img src="./assets/icons/api-management.svg" width="20" alt=""> <img src="./assets/icons/ai-gateway.svg" width="20" alt="">

```powershell
python scripts/validate_gateway.py --ids demo-ids.local.json --target apimv2
python scripts/validate_gateway.py --ids demo-ids.local.json --target aigateway
```

- [ ] `apimv2` target reports no failed checks.
- [ ] `aigateway` target reports no failed checks, or the preview-API fallback was followed.

> [!NOTE]
> APIM accepts two Entra audiences: the gateway app audience and `https://cognitiveservices.azure.com`, which is the audience used by hosted-agent identities.

### Phase 4 - Switch hosted agents to the AI Gateway tier

<img src="./assets/icons/foundry-agent-service.svg" width="20" alt=""> The first `azd up` deploys agents with `AGENT_DEFAULT_GATEWAY=apimv2`. After the preview tier is validated, run a second pass for the hosted agents only:

```powershell
azd env set AGENT_DEFAULT_GATEWAY aigateway
azd deploy agent-maf agent-langgraph
```

To return to the default path:

```powershell
azd env set AGENT_DEFAULT_GATEWAY apimv2
azd deploy agent-maf agent-langgraph
```

| Pass | `AGENT_DEFAULT_GATEWAY` | Command | Agent auth to gateway |
|---|---|---|---|
| <img src="./assets/icons/api-management.svg" width="20" alt=""> **1** | `apimv2` | `azd up` | Entra bearer token (validated by APIM) |
| <img src="./assets/icons/ai-gateway.svg" width="20" alt=""> **2** | `aigateway` | `azd deploy agent-maf agent-langgraph` | `api-key` runtime key read from Key Vault |

- [ ] Both agents redeployed with the new value.
- [ ] `scripts/demo_walkthrough.py --gateway aigateway --dry-run` completes (see Final validation).

## Gateway phase details

| | Mode | Resources / routes | Validation |
|---|---|---|---|
| <img src="./assets/icons/api-management.svg" width="20" alt=""> | `apimv2` | APIM v2, `/llm/openai/v1`, `/catalog-mcp/mcp`, `/records-mcp/mcp`, `/records`, XML policies, diagnostics. | Entra bearer token auth, APIM LLM/MCP logs, tool audit with principal headers. |
| <img src="./assets/icons/ai-gateway.svg" width="20" alt=""> | `aigateway` | `Microsoft.ApiManagement/aigateways@2026-05-01-preview`, workspace, model provider/model, model endpoint `/default/models/openai/v1`, tool servers, telemetry exporter, runtime key. | `api-key` auth, Key Vault secret exists, GenAI telemetry query 11 has rows after traffic. |
| <img src="./assets/icons/ai-gateway.svg" width="20" alt=""> <img src="./assets/icons/api-management.svg" width="20" alt=""> | `both` | Both sets. | Validate both with `scripts/validate_gateway.py`; choose the active agent path with `AGENT_DEFAULT_GATEWAY`. |

## Final validation

<img src="./assets/icons/log-analytics.svg" width="20" alt=""> <img src="./assets/icons/workbooks.svg" width="20" alt="">

```powershell
python scripts/demo_walkthrough.py --ids demo-ids.local.json --agent both --gateway apimv2 --dry-run
python scripts/demo_walkthrough.py --ids demo-ids.local.json --agent both --gateway aigateway --dry-run
python scripts/run_audit_queries.py --ids demo-ids.local.json --query 01
python scripts/run_audit_queries.py --ids demo-ids.local.json --query 11
pytest
```

- [ ] Walkthrough dry runs complete for both gateways.
- [ ] Audit query `01` (APIM) returns rows after traffic.
- [ ] Audit query `11` (AI Gateway tier GenAI telemetry) returns rows after traffic.
- [ ] `pytest` has no failures.

> [!IMPORTANT]
> Logs and telemetry can lag several minutes behind traffic. Wait and re-run before concluding a query is empty. See [04 - Testing](./04-testing.md) and [05 - Troubleshooting](./05-troubleshooting.md).

## Cleanup

<img src="./assets/icons/resource-group.svg" width="20" alt=""> Tear down everything the environment created. `--purge` also purges soft-deleted Key Vault, Foundry, and APIM names so the same names can be reused.

```powershell
azd down --purge
```

- [ ] Resource group removed.
- [ ] Soft-deleted resources purged (or the soft-delete prompts will appear on the next `azd up`).

---

Next: [03b - Manual deployment](./03b-manual-deployment.md) or [04 - Testing](./04-testing.md) →

*Last updated: 2026-10-02*
