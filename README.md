# Foundry Hosted Agents + AI Gateway Landing Zone

<p align="center">
  <img src="./docs/assets/icons/foundry.svg" width="40" alt="Microsoft Foundry">
  <img src="./docs/assets/icons/foundry-agent-service.svg" width="40" alt="Foundry Agent Service">
  <img src="./docs/assets/icons/api-management.svg" width="40" alt="API Management">
  <img src="./docs/assets/icons/ai-gateway.svg" width="40" alt="AI Gateway">
  <img src="./docs/assets/icons/container-apps.svg" width="40" alt="Container Apps">
  <img src="./docs/assets/icons/key-vault.svg" width="40" alt="Key Vault">
  <img src="./docs/assets/icons/entra-id.svg" width="40" alt="Microsoft Entra ID">
  <img src="./docs/assets/icons/application-insights.svg" width="40" alt="Application Insights">
</p>

<p align="center">
  <img src="./docs/assets/badges/version.svg" alt="pattern: v1.1.0">
  <img src="./docs/assets/badges/default.svg" alt="mode: Default">
  <img src="./docs/assets/badges/public-preview.svg" alt="status: Public preview">
  <img src="./docs/assets/badges/protocol.svg" alt="protocol: responses 2.0.0">
  <img src="./docs/assets/badges/regions-aigw.svg" alt="regions: East US 2 | Sweden Central">
  <img src="./docs/assets/badges/static-only.svg" alt="validation: Static only">
</p>

A reusable demo pattern for running **Microsoft Foundry** (formerly Azure AI Foundry) hosted agents behind governed model and tool gateways. It is for platform engineers, solution architects, and Solution Engineers who need to show - and then adapt - how an agent estate stays governed, observable, and auditable. Version 1.1 adds side-by-side gateway comparison (`apimv2`, `aigateway`, or `both`) and two hosted-agent implementations: Microsoft Agent Framework and LangGraph.

## At a glance

| | Item | Value |
|---|---|---|
| <img src="./docs/assets/icons/foundry-agent-service.svg" width="24" alt=""> | **What you get** | Two Foundry hosted agents (`agent-maf`, `agent-langgraph`) calling models and tools only through a gateway. |
| <img src="./docs/assets/icons/api-management.svg" width="24" alt=""> | **Default gateway** | Azure API Management Standard v2 (GA) - Entra token validation, `llm-*` policies, MCP governance. |
| <img src="./docs/assets/icons/ai-gateway.svg" width="24" alt=""> | **Preview gateway** | AI Gateway tier (public preview, East US 2 / Sweden Central) - runtime `api-key`, portal-first control plane. |
| <img src="./docs/assets/icons/log-analytics.svg" width="24" alt=""> | **Audit proof** | Structured tool-audit rows + 11 saved KQL queries + workbook tiles in Log Analytics / Application Insights. |
| <img src="./docs/assets/icons/azure-devops.svg" width="24" alt=""> | **Deploy with** | `azd up` (Bicep + hooks), then `azd deploy agent-maf agent-langgraph`. Manual portal path in [03b](./docs/03b-manual-deployment.md). |
| <img src="./docs/assets/icons/code.svg" width="24" alt=""> | **Example domain** | Manufacturing field operations (parts catalog + work orders). Retargetable by configuration only. |

> [!NOTE]
> This README is the front door. Start with [`docs/00-reproduce-this-demo.md`](./docs/00-reproduce-this-demo.md) for the one-page build orchestrator, or jump to the [workshop agenda → doc map](#workshop-agenda--doc-map).

## What this pattern delivers

- Two **Foundry hosted agents** deployed from separate source folders: `src/agents/maf` and `src/agents/langgraph`.
- Three gateway modes: APIM Standard v2 as the default GA path, AI Gateway tier as an opt-in public preview path, or both gateways side by side for validation.
- Governed model routes, native MCP, REST-as-MCP, and REST routes through gateway controls.
- Honest identity/audit comparison: APIM Standard v2 validates Entra tokens; AI Gateway tier preview uses a gateway-scoped runtime access key in the `api-key` header.
- Monitoring with APIM logs, preview AI Gateway OpenTelemetry GenAI telemetry, App Insights, Log Analytics, saved KQL, workbook tiles, and structured tool audit records.

## Pattern at a glance

[![Pattern at a glance](./docs/assets/foundry-hosted-agents-ai-gateway-landing-zone-architecture.png)](./docs/assets/foundry-hosted-agents-ai-gateway-landing-zone-architecture.png)

<sub>Editable source: [`docs/assets/foundry-hosted-agents-ai-gateway-landing-zone-architecture.drawio`](./docs/assets/foundry-hosted-agents-ai-gateway-landing-zone-architecture.drawio) - regenerate with `python scripts/export_diagrams.py docs/assets`.</sub>

## What's inside

<table>
  <tr>
    <td align="center" width="25%"><img src="./docs/assets/icons/foundry-agent-service.svg" width="48" alt="Foundry Agent Service"><br><b>Foundry Agent Service</b><br><sub>Hosts the two containerised agents (responses 2.0.0).</sub></td>
    <td align="center" width="25%"><img src="./docs/assets/icons/foundry-models.svg" width="48" alt="Foundry Models"><br><b>Foundry Models</b><br><sub><code>gpt-5.5</code> deployment, reached only via a gateway.</sub></td>
    <td align="center" width="25%"><img src="./docs/assets/icons/api-management.svg" width="48" alt="API Management"><br><b>API Management v2</b><br><sub>Default GA gateway: Entra validation, <code>llm-*</code> policies, MCP.</sub></td>
    <td align="center" width="25%"><img src="./docs/assets/icons/ai-gateway.svg" width="48" alt="AI Gateway"><br><b>AI Gateway tier</b><br><sub>Preview gateway: model provider, tool servers, runtime key.</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="./docs/assets/icons/container-apps.svg" width="48" alt="Container Apps"><br><b>Container Apps</b><br><sub>Runs <code>catalog-mcp</code> and <code>records-api</code> tool backends.</sub></td>
    <td align="center"><img src="./docs/assets/icons/container-registry.svg" width="48" alt="Container Registry"><br><b>Container Registry</b><br><sub>Stores agent and tool images (remote build).</sub></td>
    <td align="center"><img src="./docs/assets/icons/key-vault.svg" width="48" alt="Key Vault"><br><b>Key Vault</b><br><sub>Holds the AI Gateway runtime key - never in code or env.</sub></td>
    <td align="center"><img src="./docs/assets/icons/entra-id.svg" width="48" alt="Microsoft Entra ID"><br><b>Microsoft Entra ID</b><br><sub>Gateway app registration; token audience for APIM.</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="./docs/assets/icons/managed-identity.svg" width="48" alt="Managed identity"><br><b>Managed identity</b><br><sub>Gateway-to-Foundry and project-to-Key Vault access.</sub></td>
    <td align="center"><img src="./docs/assets/icons/log-analytics.svg" width="48" alt="Log Analytics"><br><b>Log Analytics</b><br><sub>Resource-specific tables, saved KQL, retention.</sub></td>
    <td align="center"><img src="./docs/assets/icons/application-insights.svg" width="48" alt="Application Insights"><br><b>Application Insights</b><br><sub>Agent spans, GenAI telemetry, trace correlation.</sub></td>
    <td align="center"><img src="./docs/assets/icons/workbooks.svg" width="48" alt="Workbooks"><br><b>Workbooks</b><br><sub>Dashboard tiles incl. AI Gateway tier telemetry.</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="./docs/assets/icons/alerts.svg" width="48" alt="Alerts"><br><b>Alerts</b><br><sub>Throttling, denial, and error-rate alert rules.</sub></td>
    <td align="center"><img src="./docs/assets/icons/sentinel.svg" width="48" alt="Microsoft Sentinel"><br><b>Sentinel</b> <sub>(optional)</sub><br><sub><code>ENABLE_SENTINEL</code>; workspace onboarding only.</sub></td>
    <td align="center"><img src="./docs/assets/icons/virtual-network.svg" width="48" alt="Virtual Network"><br><b>VNet / Private Link</b> <sub>(optional)</sub><br><sub><code>NETWORK_ISOLATION=true</code> adds private endpoints.</sub></td>
    <td align="center"><img src="./docs/assets/icons/content-safety.svg" width="48" alt="Content Safety"><br><b>Content Safety</b><br><sub>Prompt/response screening at the gateway.</sub></td>
  </tr>
</table>

## Gateway modes

[![Gateway modes](./docs/assets/gateway-modes.png)](./docs/assets/gateway-modes.png)

| | Mode | What deploys | Runtime auth | Best use | Recommendation |
|---|---|---|---|---|---|
| <img src="./docs/assets/icons/api-management.svg" width="20" alt=""> | **`apimv2`** <br> <img src="./docs/assets/badges/default.svg" alt="Default"> <img src="./docs/assets/badges/ga.svg" alt="GA"> | APIM Standard v2 / Premium v2, XML policies, LLM API, MCP APIs, REST-as-MCP, REST API. | Entra bearer token for `api://<GATEWAY_APP_CLIENT_ID>`; optional subscription key only for entitlement. | Customer-facing repeatable demos and production-like policy review. | **Default.** Use unless preview tier testing is the explicit goal. |
| <img src="./docs/assets/icons/ai-gateway.svg" width="20" alt=""> | **`aigateway`** <br> <img src="./docs/assets/badges/opt-in.svg" alt="Opt-in"> <img src="./docs/assets/badges/public-preview.svg" alt="Public preview"> | AI Gateway tier public preview resource, model provider, model, MCP tool servers, telemetry exporter, runtime key. | Runtime access key in `api-key`; key is gateway-scoped in preview. | Learning the dedicated AI Gateway tier control plane. | Use only in supported preview regions and with preview risk accepted. |
| <img src="./docs/assets/icons/monitor.svg" width="20" alt=""> | **`both`** <br> <img src="./docs/assets/badges/opt-in.svg" alt="Opt-in"> | APIM Standard v2 and AI Gateway tier side by side. APIM remains primary for legacy outputs; AI Gateway tier outputs are also written. | Both mechanisms, selected by `AGENT_DEFAULT_GATEWAY`. | Migration/comparison workshops and live validation. | **Recommended for v1.1 validation** so both paths can be tested before choosing. |

> [!IMPORTANT]
> AI Gateway tier is **public preview**, available in East US 2 and Sweden Central during preview, uses management API `2026-05-01-preview`, has no SLA, and pricing is to be announced. Manage it in the standalone portal at `ai.gateway.azure.com`. Sources: [overview](https://learn.microsoft.com/en-us/azure/api-management/ai-gateway-overview), [quickstart](https://learn.microsoft.com/en-us/azure/api-management/quickstart-ai-gateway-create), [govern/security/operate](https://learn.microsoft.com/en-us/azure/api-management/ai-gateway-govern-secure-assets).

## Hosted-agent frameworks

[![Agent frameworks](./docs/assets/agent-frameworks.png)](./docs/assets/agent-frameworks.png)

| | Agent | Source path | Key packages | Host classes | Model client | MCP client | Injected / consumed env vars | Learn reference |
|---|---|---|---|---|---|---|---|---|
| <img src="./docs/assets/icons/foundry-agent-service.svg" width="20" alt=""> | **Microsoft Agent Framework** <br> <img src="./docs/assets/badges/protocol.svg" alt="protocol"> | `src/agents/maf` | `agent-framework-core`, `agent-framework-openai`, `agent-framework-foundry-hosting` | `ResponsesHostServer`, `InvocationsHostServer` from `agent_framework_foundry_hosting` | OpenAI-compatible client pointed at the selected gateway, not direct Foundry. | `MCPStreamableHTTPTool` with gateway headers. | Foundry injects `FOUNDRY_PROJECT_ENDPOINT`, `AZURE_AI_MODEL_DEPLOYMENT_NAME`, `APPLICATIONINSIGHTS_CONNECTION_STRING`; demo also uses `AGENT_DEFAULT_GATEWAY`, gateway URLs, `KEY_VAULT_URI`, and `AIGW_RUNTIME_KEY_SECRET_NAME`. | [Host Microsoft Agent Framework agents as Foundry hosted agents](https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/framework-hosted-agents?pivots=programming-language-python) |
| <img src="./docs/assets/icons/code.svg" width="20" alt=""> | **LangGraph** <br> <img src="./docs/assets/badges/protocol.svg" alt="protocol"> | `src/agents/langgraph` | `langchain-azure-ai[hosting]`, `langchain`, `langchain-openai`, `langchain-mcp-adapters` | `ResponsesHostServer`, `InvocationsHostServer` from `langchain_azure_ai.agents.hosting` | `ChatOpenAI` pointed at the selected gateway. | `MultiServerMCPClient` with Streamable HTTP gateway URLs. | Foundry injects `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_MODEL_NAME`, `APPLICATIONINSIGHTS_CONNECTION_STRING`; demo also uses the same gateway and Key Vault variables. | [Host LangGraph agents as Foundry hosted agents](https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/langchain-hosted-agents) |

Both agents use hosted protocol `responses` version `2.0.0`; protocol `1.0.0` is not supported by the v1.1 implementation. Both are deployed with the azd extension `azure.ai.agents` (`host: azure.ai.agent`, `kind: hosted`) and share one gateway-auth and telemetry contract.

## Workshop agenda → doc map

| | Segment | What the audience sees | Doc |
|---|---|---|---|
| <img src="./docs/assets/icons/foundry-agent-service.svg" width="20" alt=""> | **Hosted agents** | Container contract, sessions, the two frameworks. | [06 - Hosted agents explained](./docs/06-hosted-agents-explained.md) |
| <img src="./docs/assets/icons/entra-id.svg" width="20" alt=""> | **Identity and traceability** | Who called what; token flow; trace correlation. | [07 - Identity, authentication, traceability](./docs/07-identity-auth-traceability.md) |
| <img src="./docs/assets/icons/api-management.svg" width="20" alt=""> | **Tools through the gateway** | Native MCP, REST-as-MCP, allow-lists. | [08 - Tools, APIM, MCP topology](./docs/08-tools-apim-mcp-topology.md) |
| <img src="./docs/assets/icons/log-analytics.svg" width="20" alt=""> | **Monitoring and audit** | Saved KQL, workbook, alerts, audit proof. | [09 - Monitoring and audit](./docs/09-monitoring-and-audit.md) |
| <img src="./docs/assets/icons/virtual-network.svg" width="20" alt=""> | **Enterprise posture and scale** | Network isolation, limits, known gaps. | [10 - Enterprise posture and scale](./docs/10-enterprise-posture-and-scale.md) |
| <img src="./docs/assets/icons/workbooks.svg" width="20" alt=""> | **End-to-end walkthrough** | Scripted agent × gateway matrix. | [11 - Demo walkthrough](./docs/11-demo-walkthrough.md) |
| <img src="./docs/assets/icons/policy.svg" width="20" alt=""> | **Reference and testing** | Every variable, output, test. | [12 - Configuration reference](./docs/12-configuration-reference.md), [04 - Testing](./docs/04-testing.md), [05 - Troubleshooting](./docs/05-troubleshooting.md) |

[![Demo walkthrough story](./docs/assets/demo-walkthrough-story.png)](./docs/assets/demo-walkthrough-story.png)

## Quick start

> [!WARNING]
> Replace placeholders with your tenant/subscription. **Never rely on ambient `az` or `azd` state** - both CLIs keep separate logins that drift between tenants. The `preprovision` hook stops the deployment if the `az` context does not match `AZURE_TENANT_ID` / `AZURE_SUBSCRIPTION_ID`.

| Step | | Action | Validation |
|---|---|---|---|
| **1** | <img src="./docs/assets/icons/entra-id.svg" width="28" alt="Entra"> | Sign in tenant-explicitly with **both** `azd auth login --tenant-id <TENANT_ID>` and `az login --tenant <TENANT_ID>`; then `az account set`. | - [ ] `az account show` prints the intended tenant + subscription. |
| **2** | <img src="./docs/assets/icons/subscription.svg" width="28" alt="Subscription"> | Create the azd environment and set the knobs (`AI_GATEWAY_MODE both`, `MODEL_NAME gpt-5.5`, `DOMAIN_PROFILE manufacturing-field-ops`). | - [ ] `azd env get-values` shows the values. |
| **3** | <img src="./docs/assets/icons/container-apps.svg" width="28" alt="Container Apps"> | `azd up` provisions infra, runs the hooks, and deploys tools + agents. | - [ ] `demo-ids.local.json` exists; Key Vault holds `aigw-runtime-key`. |
| **4** | <img src="./docs/assets/icons/api-management.svg" width="28" alt="APIM"> | Validate both gateways with `scripts/validate_gateway.py --target apimv2` then `--target aigateway`. | - [ ] Both targets finish with no failed checks. |
| **5** | <img src="./docs/assets/icons/ai-gateway.svg" width="28" alt="AI Gateway"> | Second pass: `AGENT_DEFAULT_GATEWAY=aigateway` then `azd deploy agent-maf agent-langgraph`. | - [ ] Walkthrough dry-run passes for `--gateway aigateway`. |

<details>
<summary><b>Full command block (copy/paste)</b></summary>

```powershell
azd auth login --tenant-id <TENANT_ID>
az login --tenant <TENANT_ID>
az account set --subscription <SUBSCRIPTION_ID>
az account show --query "{tenant:tenantId, subscription:id, subName:name, user:user.name}" -o table

azd env new <ENV_NAME>
azd env set AZURE_TENANT_ID <TENANT_ID>
azd env set AZURE_SUBSCRIPTION_ID <SUBSCRIPTION_ID>
azd env set AZURE_LOCATION eastus2
azd env set APIM_PUBLISHER_EMAIL <you@example.com>
azd env set AI_GATEWAY_MODE both
azd env set AI_GATEWAY_TIER_LOCATION eastus2
azd env set AIGW_RUNTIME_KEY_SECRET_NAME aigw-runtime-key
azd env set AGENT_DEFAULT_GATEWAY apimv2
azd env set MODEL_NAME gpt-5.5
azd env set MODEL_VERSION 2026-04-24
azd env set MODEL_SKU GlobalStandard
azd env set DOMAIN_PROFILE manufacturing-field-ops

azd up
```

To validate the preview tier after the first pass:

```powershell
python scripts/validate_gateway.py --ids demo-ids.local.json --target apimv2
python scripts/validate_gateway.py --ids demo-ids.local.json --target aigateway
azd env set AGENT_DEFAULT_GATEWAY aigateway
azd deploy agent-maf agent-langgraph
python scripts/demo_walkthrough.py --ids demo-ids.local.json --agent both --gateway aigateway --dry-run
```

</details>

> [!TIP]
> Model availability and quota change. Re-verify `gpt-5.5` `2026-04-24` (GlobalStandard) in your region before deploying - see the dated matrix in [02 - Prerequisites](./docs/02-prerequisites.md#model-availability-matrix-dated-2026-10-02).

## File index

| | Path | Purpose |
|---|---|---|
| <img src="./docs/assets/icons/code.svg" width="20" alt=""> | `README.md` | Overview, gateway/agent comparison, quick start, distribution, provenance. |
| <img src="./docs/assets/icons/code.svg" width="20" alt=""> | `CHANGELOG.md` | Version history, verification, and live-validation status. |
| <img src="./docs/assets/icons/azure-devops.svg" width="20" alt=""> | `azure.yaml` | azd template with `agent-maf`, `agent-langgraph`, `catalog-mcp`, and `records-api` services. |
| <img src="./docs/assets/icons/resource-group.svg" width="20" alt=""> | `infra/azd.parameters.json`, `infra/azd.bicep` | azd parameter substitutions and subscription-scope wrapper outputs. |
| <img src="./docs/assets/icons/diagnostic-settings.svg" width="20" alt=""> | `infra/hooks/*.ps1` | Tenant guard, AI Gateway tier region guard, local ID writing, and runtime-key Key Vault storage. |
| <img src="./docs/assets/icons/foundry-agent-service.svg" width="20" alt=""> | `src/agents/maf/` | Microsoft Agent Framework hosted-agent implementation. |
| <img src="./docs/assets/icons/foundry-agent-service.svg" width="20" alt=""> | `src/agents/langgraph/` | LangGraph hosted-agent implementation. |
| <img src="./docs/assets/icons/code.svg" width="20" alt=""> | `scripts/sync-agent-profiles.ps1` | Copies root profile JSON files into each hosted-agent Docker build context. |
| <img src="./docs/assets/icons/api-management.svg" width="20" alt=""> | `scripts/validate_gateway.py` | Validates APIM v2 or AI Gateway tier runtime routes with `--target`. |
| <img src="./docs/assets/icons/workbooks.svg" width="20" alt=""> | `scripts/demo_walkthrough.py` | Runs/dry-runs the agent x gateway walkthrough matrix. |
| <img src="./docs/assets/icons/query-pack.svg" width="20" alt=""> | `infra/monitoring/queries/11-ai-gateway-tier-telemetry.kql` | Preview tier GenAI telemetry comparison query. |
| <img src="./docs/assets/icons/resource-group.svg" width="20" alt=""> | `docs/` | Shareable runbooks; all narrative docs live here. |
| <img src="./docs/assets/icons/resource-group.svg" width="20" alt=""> | `docs/assets/` | Draw.io sources, PNG exports, [product icons](./docs/assets/icons/README.md) and status badges. |

## Distribution

This folder is intended to be checked into Azure DevOps or GitHub as a standalone demo repository. Do not commit populated IDs, tenant/subscription GUIDs, runtime keys, connection strings, `.env` files, or secrets. `demo-ids.template.json` is a shape reference only; the populated `demo-ids.local.json` stays local and gitignored.

> [!CAUTION]
> Never paste the AI Gateway runtime key (or any `listSecrets` output) into docs, issues, chat, or logs. It is gateway-scoped in preview - one key reaches every model and tool.

## Provenance

| Source | License | Used for |
|---|---|---|
| [`Azure-Samples/AI-Gateway`](https://github.com/Azure-Samples/AI-Gateway) (`1679e31`) | MIT | APIM inference policy and streamable-MCP patterns. |
| [`Azure-Samples/fibey`](https://github.com/Azure-Samples/fibey) (`5408f6e`) | MIT | Catalog/inventory MCP service shape. |
| [`Azure-Samples/simple-foundry-hosted-agent-python-aigateway`](https://github.com/Azure-Samples/simple-foundry-hosted-agent-python-aigateway) (`c572db8`) | MIT | Hosted-agent + AI Gateway wiring. |
| [Azure Architecture Icons V24](https://learn.microsoft.com/en-us/azure/architecture/icons/) and [Entra icons](https://learn.microsoft.com/en-us/entra/architecture/architecture-icons) | Microsoft icon terms | Product icons - see [`docs/assets/icons/README.md`](./docs/assets/icons/README.md). |

Upstream samples were used as design references; this demo re-implements the patterns with generic domain data.

## Known gaps

> [!NOTE]
> **Be honest in the room.** These are open items, not hidden ones.
> - No first-party hosted-agent CI/CD template exists; treat `.github/workflows/deploy.yml` as a starting point only.
> - One Foundry project per environment tier is the supported isolation model.
> - Cross-system trace correlation (agent ↔ gateway ↔ backend) is DIY - the pattern propagates `traceparent` and `x-gw-request-id`, but there is no single platform join.
> - Exact hosted-agent OpenTelemetry environment-variable names and the Foundry-injected variable list are not fully confirmed in Learn.
> - The AI Gateway tier ARM shape (`2026-05-01-preview`) is unverified live; `postprovision` prints a portal fallback if `listSecrets` differs.

> [!IMPORTANT]
> **Validation status:** v1.1 is statically verified (tests, link check, diagram freshness). A live deployment test was in progress when these docs were updated; see `CHANGELOG.md` for the reconciled status before claiming a live result.

## Decision provenance

| Date | Decision | Reference |
|---|---|---|
| 2026-09-30 | Locked v1 demo pattern for Foundry hosted agents behind APIM AI Gateway with governed MCP/REST tools and audit-first landing-zone posture. | `CHANGELOG.md` 1.0.0 entry. |
| 2026-10-01 | v1.1 adds AI Gateway tier preview sidecar and dual hosted-agent frameworks while keeping APIM Standard v2 the safe default. | This docs update and `CHANGELOG.md` 1.1.0 entry. |
| 2026-10-02 | Visual documentation pass: product icons, status badges, callouts, step cards. | [`docs/assets/icons/README.md`](./docs/assets/icons/README.md). |

---

*Last updated: 2026-10-02*
