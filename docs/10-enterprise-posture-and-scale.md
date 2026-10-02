[README](../README.md) › [docs index](./00-reproduce-this-demo.md) › 10 Enterprise posture and scale

# 10 - Enterprise posture and scale

<p>
  <img src="./assets/icons/virtual-network.svg" width="40" alt="Virtual Network"/>&nbsp;
  <img src="./assets/icons/private-endpoint.svg" width="40" alt="Private endpoint"/>&nbsp;
  <img src="./assets/icons/private-link.svg" width="40" alt="Private Link"/>&nbsp;
  <img src="./assets/icons/dns-zones.svg" width="40" alt="Private DNS zones"/>&nbsp;
  <img src="./assets/icons/nsg.svg" width="40" alt="Network security group"/>&nbsp;
  <img src="./assets/icons/cosmos-db.svg" width="40" alt="Azure Cosmos DB"/>&nbsp;
  <img src="./assets/icons/storage.svg" width="40" alt="Storage account"/>&nbsp;
  <img src="./assets/icons/ai-search.svg" width="40" alt="Azure AI Search"/>&nbsp;
  <img src="./assets/icons/key-vault.svg" width="40" alt="Key Vault"/>&nbsp;
  <img src="./assets/icons/ai-gateway.svg" width="40" alt="AI Gateway"/>&nbsp;
  <img src="./assets/icons/api-management.svg" width="40" alt="API Management"/>
</p>

![GA](./assets/badges/ga.svg) ![Preview](./assets/badges/preview.svg) ![Opt-in](./assets/badges/opt-in.svg) ![DIY](./assets/badges/diy.svg)

This document describes the **enterprise posture** of the hosted-agent and dual-gateway pattern: how traffic is isolated when `NETWORK_ISOLATION=true`, what the platform limits are, how the two gateways differ in private networking, and which parts of delivery (CI/CD, one-project-per-tier) remain your responsibility. It is for the network, security and platform architects who must say *yes* or *not yet* to a private deployment.

## At a glance

| | Topic | Bottom line |
|---|---|---|
| <img src="./assets/icons/virtual-network.svg" width="24" alt=""/> | **Default vs isolated** | Default is public endpoints with Entra auth (demo friendly). `NETWORK_ISOLATION=true` adds a VNet `10.40.0.0/16`, delegated subnets and private data dependencies. |
| <img src="./assets/icons/private-endpoint.svg" width="24" alt=""/> | **What is private** | Storage, AI Search and Cosmos DB get private endpoints; Foundry, Key Vault and Container Registry switch public access off. Private endpoints for those three, and the DNS zones, are still yours to add (see [known gaps](#known-gaps)). |
| <img src="./assets/icons/foundry-agent-service.svg" width="24" alt=""/> | **Hosted agent endpoint** | The agent endpoint itself cannot be made private through azd today. |
| <img src="./assets/icons/api-management.svg" width="24" alt=""/> | **Two gateways, two answers** | Standard v2 and the preview AI Gateway tier have different private-networking options; one setting does not secure both. |
| <img src="./assets/icons/azure-devops.svg" width="24" alt=""/> | **Delivery** | No first-party hosted-agent CI/CD exists; the demo ships a do-it-yourself workflow. |

## The network path

[![Network topology](./assets/network-topology.png)](./assets/network-topology.png)

<sub>Editable source: [`assets/network-topology.drawio`](./assets/network-topology.drawio) - regenerate with `python scripts/export_diagrams.py docs/assets`.</sub>

A request crosses five hops. Each hop has a different privacy control, which is why "private" is never a single switch.

| Step | | Hop | Control | Validation |
|---|---|---|---|---|
| 1 | <img src="./assets/icons/private-link.svg" width="28" alt=""/> | **Client to gateway** | Public endpoint or inbound private endpoint on the gateway (see the [SKU table](#api-management-v2-networking)). | - [ ] The gateway host resolves to a private IP from the client network when inbound private access is required. |
| 2 | <img src="./assets/icons/foundry-agent-service.svg" width="28" alt=""/> | **Agent runtime to gateway** | Hosted-agent sessions run in dedicated micro-VMs; with a BYO VNet they use the delegated agent subnet and a platform data proxy ([networking deep dive](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/agents-networking-deep-dive)). | - [ ] Agent calls carry `traceparent` and identity headers to the gateway. |
| 3 | <img src="./assets/icons/api-management.svg" width="28" alt=""/> | **Gateway to model** | Managed identity of the gateway calls the Foundry model deployment (no keys). | - [ ] No API key for the model exists in policy or configuration. |
| 4 | <img src="./assets/icons/container-apps.svg" width="28" alt=""/> | **Gateway to tools** | APIM outbound VNet integration reaches the internal Container Apps environment (`snet-aca`). | - [ ] Tool backends are not reachable from the internet. |
| 5 | <img src="./assets/icons/cosmos-db.svg" width="28" alt=""/> | **Platform to state** | Cosmos DB, Storage and AI Search are reached over private endpoints from `snet-private-endpoints`. | - [ ] `publicNetworkAccess` is `Disabled` on all three. |

### Gateway comparison per hop

| Hop | <img src="./assets/icons/api-management.svg" width="20" alt=""/> APIM Standard v2 | <img src="./assets/icons/ai-gateway.svg" width="20" alt=""/> AI Gateway tier (preview) | Recommendation |
|---|---|---|---|
| Client to gateway | Public endpoint, or inbound private endpoint (Standard v2 and Premium v2). | Inbound Private Link / private endpoint, ![Preview](./assets/badges/preview.svg) | Use private endpoints when policy requires private ingress. |
| Gateway to backends | Outbound VNet integration (Standard v2 / Premium v2); VNet injection on Premium v2 only. | Outbound VNet integration, ![Preview](./assets/badges/preview.svg) subnet must be same region, dedicated, at least `/27` (`/24` recommended), delegated to `Microsoft.Web/serverFarms`. | Plan a separate subnet for each gateway. |
| Gateway to model | Managed identity to the Foundry model backend. | Managed identity with the Foundry User role. | Managed identity is preferred for both. |
| Gateway to tools | APIM to Container Apps / private backends. | Remote MCP / OpenAPI / connectors. | Confirm reachability from the selected gateway subnet. |

Sources: [AI Gateway tier private networking](https://learn.microsoft.com/en-us/azure/api-management/ai-gateway-configure-private-networking), [APIM v2 tiers](https://learn.microsoft.com/en-us/azure/api-management/v2-service-tiers-overview).

## What `NETWORK_ISOLATION=true` deploys

![Opt-in](./assets/badges/opt-in.svg) The flag is read by `infra/main.bicep` and drives `modules/network.bicep`, `modules/foundry-private.bicep` and the network arguments of the Foundry, Key Vault, Container Apps and APIM modules. Subnet prefixes are the `*_SUBNET_PREFIX` variables in [doc 12](./12-configuration-reference.md).

| Resource | Setting when isolated | Deployed by the template today |
|---|---|---|
| <img src="./assets/icons/virtual-network.svg" width="20" alt=""/> **Virtual network** `vnet-<prefix>` | `10.40.0.0/16` (`VNET_ADDRESS_PREFIX`) | ✅ |
| <img src="./assets/icons/nsg.svg" width="20" alt=""/> **`snet-agent`** | `10.40.0.0/24`, delegated to `Microsoft.App/environments` (hosted-agent sessions) | ✅ subnet and delegation; ⏳ binding the Foundry account to it is a [known gap](#known-gaps) |
| <img src="./assets/icons/container-apps-environment.svg" width="20" alt=""/> **`snet-aca`** | `10.40.2.0/23`, delegated to `Microsoft.App/environments`; the Container Apps environment is created `internal` | ✅ |
| <img src="./assets/icons/api-management.svg" width="20" alt=""/> **`snet-apim`** | `10.40.4.0/27`, delegated to `Microsoft.Web/serverFarms`; APIM `virtualNetworkConfiguration` points to it | ✅ |
| <img src="./assets/icons/private-endpoint.svg" width="20" alt=""/> **`snet-private-endpoints`** | `10.40.5.0/24`, private-endpoint network policies disabled | ✅ |
| <img src="./assets/icons/storage.svg" width="20" alt=""/> **Storage account** | Public access disabled, shared-key access off, TLS 1.2, private endpoint (`blob`) | ✅ |
| <img src="./assets/icons/ai-search.svg" width="20" alt=""/> **AI Search** (`standard`) | Public access disabled, local auth off, private endpoint (`searchService`) | ✅ |
| <img src="./assets/icons/cosmos-db.svg" width="20" alt=""/> **Cosmos DB** | Public access disabled, local auth off, private endpoint (`Sql`) | ✅ |
| <img src="./assets/icons/foundry.svg" width="20" alt=""/> **Foundry account** | `publicNetworkAccess: Disabled`; BYO IDs for Cosmos, Storage and Search are passed to the account | ✅ flag and BYO wiring; ⏳ private endpoint |
| <img src="./assets/icons/key-vault.svg" width="20" alt=""/> **Key Vault** | `publicNetworkAccess: Disabled` | ✅ flag; ⏳ private endpoint |
| <img src="./assets/icons/container-registry.svg" width="20" alt=""/> **Container Registry** (`Premium`) | `publicNetworkAccess: Disabled` | ✅ flag; ⏳ private endpoint |
| <img src="./assets/icons/dns-zones.svg" width="20" alt=""/> **Private DNS zones** | `privatelink.services.ai.azure.com`, `privatelink.openai.azure.com`, `privatelink.blob.core.windows.net`, `privatelink.vaultcore.azure.net`, `privatelink.azurecr.io`, `privatelink.search.windows.net`, `privatelink.documents.azure.com` (as drawn in the topology) | ⏳ not created by the template |

> [!WARNING]
> **Disabling public access without private endpoints blocks the deployer.** Key Vault, Foundry and the registry have public access off when isolation is on, but their private endpoints and DNS zone groups are not part of this template. Add them (see the reference samples below) and deploy from a host that can resolve them, or the post-provision steps that write secrets and push images will fail. Treat isolation mode as a **reviewed starting point**, not a finished private landing zone.

> [!NOTE]
> Private ACR is only supported for Foundry projects **created after 2026-06-25**; older projects need a publicly reachable registry ([private ACR](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/deploy-hosted-agent-private-azure-container-registry)). The hosted-agent endpoint itself cannot be made private through azd.

## Egress options, BYO resources and encryption

Foundry describes egress as a taxonomy, **not** as Basic/Standard tiers ([networking options](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/networking-options)):

| Option | <img src="./assets/icons/virtual-network.svg" width="20" alt=""/> Meaning | Status |
|---|---|---|
| Public egress | Default; agent traffic leaves over the platform's public path. | ![GA](./assets/badges/ga.svg) |
| BYO VNet | Hosted agents get micro-VMs on your delegated subnet; outbound goes through a platform data proxy per project. | ![GA](./assets/badges/ga.svg) |
| Managed VNet | Full isolation managed by the platform. | Capability settings use API `2026-07-15-preview` |
| Standard setup with private networking | BYO Cosmos DB, Storage and AI Search plus private endpoints. This is the pattern `foundry-private.bicep` follows. | ![GA](./assets/badges/ga.svg) |

| BYO resource | <img src="./assets/icons/foundry.svg" width="20" alt=""/> Account property | Created by this demo when isolated | Private endpoint |
|---|---|---|---|
| <img src="./assets/icons/cosmos-db.svg" width="20" alt=""/> **Cosmos DB** | `azureCosmosDBAccountResourceId` | `cosmos-<prefix>-<hash>` | ✅ `Sql` |
| <img src="./assets/icons/storage.svg" width="20" alt=""/> **Storage** | `azureStorageAccountResourceId` | `st<prefix><hash>` | ✅ `blob` |
| <img src="./assets/icons/ai-search.svg" width="20" alt=""/> **AI Search** | `aiSearchResourceId` | `srch-<prefix>-<hash>` | ✅ `searchService` |

Private endpoints are **not created automatically** by Foundry for these dependencies ([configure private link](https://learn.microsoft.com/en-us/azure/foundry/how-to/configure-private-link)). **Customer-managed keys (CMK)** are GA at the Foundry account level; CMK on the BYO dependencies relies on each service's own CMK feature, with no integrated pipeline documented ([encryption keys](https://learn.microsoft.com/en-us/azure/foundry/concepts/encryption-keys-portal)). The demo does not enable CMK.

> [!TIP]
> Reference templates live in `microsoft-foundry/foundry-samples` under `infrastructure/infrastructure-setup-bicep/`: `15-private-network-standard-agent-setup`, `16-private-network-standard-agent-apim-setup`, `25-entraid-passthrough`, and `30`/`31`/`32` `customer-managed-keys*`. Start from `15` and `16` to close the gaps above.

## Scale numbers

Plan capacity from the documented limits, not from the demo's defaults ([networking deep dive](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/agents-networking-deep-dive), [limits, quotas and regions](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/limits-quotas-regions)).

| | Dimension | Number | Note |
|---|---|---|---|
| <img src="./assets/icons/virtual-network.svg" width="24" alt=""/> | **Agent subnet size** | `/24` ≈ 2,000 sessions; `/26` ≈ 100; `/27` ≈ 20 (hard minimum) | `/24` is recommended; the demo default is `10.40.0.0/24`. |
| <img src="./assets/icons/virtual-network.svg" width="24" alt=""/> | **Session to IP ratio** | 1:1 by default; up to 1:10 via a support request | Each session gets a dedicated micro-VM with its own NIC and IP. |
| <img src="./assets/icons/foundry-agent-service.svg" width="24" alt=""/> | **Concurrent sessions per region** | 2,000 in Canada Central, East US 2, Japan East, North Central US, South Africa North, Southeast Asia and Sweden Central; 1,000 elsewhere | Quotas can change; check the limits page before sizing. |
| <img src="./assets/icons/toolbox.svg" width="24" alt=""/> | **Tools per agent** | 128 | Prefer a few well-governed MCP servers over many ad-hoc tools. |
| <img src="./assets/icons/foundry-agent-service.svg" width="24" alt=""/> | **Hosted-agent regions** | 31 (list is growing) | Confirm your region on the hosted-agents page. |
| <img src="./assets/icons/foundry-agent-service.svg" width="24" alt=""/> | **Session lifecycle** | Idle timeout 2-60 minutes (15 default); deleted after 30 days of inactivity | Sessions are not durable records. |
| <img src="./assets/icons/entra-workload-id.svg" width="24" alt=""/> | **Identity limit nuance** | The 250 limit applies only to non-Microsoft platforms using client credentials, and Foundry is exempt | A nuance, **not** a cap on hosted agents. Hosted agents share one project identity until published. |
| <img src="./assets/icons/foundry-models.svg" width="24" alt=""/> | **Model quota** | `MODEL_CAPACITY` (default 50), `GlobalStandard` | `TOKEN_LIMIT_TPM_PER_AGENT` protects the gateway but does not create model quota. |
| <img src="./assets/icons/log-analytics.svg" width="24" alt=""/> | **Log ingestion** | Driven by LLM message logging and GenAI telemetry | Set `LOG_RETENTION_DAYS` explicitly; see [doc 09](./09-monitoring-and-audit.md#retention-and-cost). |

> [!NOTE]
> The delegated agent subnet requires the `Microsoft.App` and `Microsoft.ContainerService` resource providers to be registered in the subscription. No per-account project limit is documented, so this demo does not quote one.

## API Management v2 networking

<img src="./assets/icons/api-management.svg" width="28" alt=""/> The demo defaults to `StandardV2` (`APIM_SKU`); `PremiumV2` is the alternative ([v2 tiers overview](https://learn.microsoft.com/en-us/azure/api-management/v2-service-tiers-overview)).

| SKU | Outbound VNet integration | Inbound private endpoint | VNet injection | Status |
|---|---|---|---|---|
| <img src="./assets/icons/api-management.svg" width="20" alt=""/> **Standard v2** | Yes | Yes | No | ![GA](./assets/badges/ga.svg) |
| <img src="./assets/icons/api-management.svg" width="20" alt=""/> **Premium v2** | Yes | Yes | Yes | ![GA](./assets/badges/ga.svg) |
| <img src="./assets/icons/api-management.svg" width="20" alt=""/> **Classic tiers** | - | - | Premium only | ![GA](./assets/badges/ga.svg) |
| <img src="./assets/icons/foundry.svg" width="20" alt=""/> **Foundry portal "AI Gateway" feature** | Requires a v2 APIM instance | - | - | ![Public preview](./assets/badges/public-preview.svg) |

> [!IMPORTANT]
> **AI Gateway tier private networking** ![Preview](./assets/badges/preview.svg) ![Release gated](./assets/badges/release-gated.svg) supports inbound Private Link and outbound VNet integration, with a same-region, dedicated outbound subnet of at least `/27` (`/24` recommended) delegated to `Microsoft.Web/serverFarms` ([Learn](https://learn.microsoft.com/en-us/azure/api-management/ai-gateway-configure-private-networking)). It has **no SLA**, is available in East US 2 and Sweden Central only, and runtime access keys are gateway-scoped. **This demo documents the capability but does not deploy it** for the tier module - validate it as a separate track.

## Environment strategy

| | Strategy | Recommended settings |
|---|---|---|
| <img src="./assets/icons/resource-group.svg" width="24" alt=""/> | **Demo / comparison** | `AI_GATEWAY_MODE=both`; start with `AGENT_DEFAULT_GATEWAY=apimv2`, then a second pass with `aigateway`. |
| <img src="./assets/icons/api-management.svg" width="24" alt=""/> | **Customer-facing, repeatable** | `AI_GATEWAY_MODE=apimv2` unless preview-tier testing is explicitly approved. |
| <img src="./assets/icons/ai-gateway.svg" width="24" alt=""/> | **Preview validation** | `AI_GATEWAY_MODE=both` in East US 2 or Sweden Central, with a live report captured. |
| <img src="./assets/icons/private-endpoint.svg" width="24" alt=""/> | **Private posture** | Keep the decision explicit per gateway; one setting does not secure both. |
| <img src="./assets/icons/subscription.svg" width="24" alt=""/> | **Environment tiers** | Use one Foundry project per environment tier (dev, test, production), each its own azd environment. |

## CI/CD is do-it-yourself

![DIY](./assets/badges/diy.svg) <img src="./assets/icons/azure-devops.svg" width="28" alt=""/> There is **no first-party CI/CD** for hosted agents. The demo ships `.github/workflows/deploy.yml`, a manually triggered workflow that signs in with OpenID Connect (no stored secrets) and runs `azd up`. Adapt it to your pipeline system and add approvals, scanning and environment promotion.

> [!CAUTION]
> The workflow is a **starting point**, not a production pipeline: it has no tests, no approval gates, no image scanning and a single environment per run. Use a federated credential with least privilege for the pipeline identity, and keep tenant and subscription explicit.

<details><summary><b>Show workflow excerpt</b></summary>

```yaml
name: Deploy demo

on:
  workflow_dispatch:
    inputs:
      environment:
        description: azd environment name
        required: true
        default: demo

permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    steps:
      - uses: actions/checkout@v4

      - name: Azure login with OIDC
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: Install azd
        uses: Azure/setup-azd@v2

      - name: Install azd hosted-agent extension
        run: azd extension install azure.ai.agents

      - name: Provision and deploy
        run: azd up --no-prompt
```

The full file also runs `azd env new`/`azd env select` and sets `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_LOCATION`, `AI_GATEWAY_MODE`, `AI_GATEWAY_TIER_LOCATION`, `AIGW_REQUEST_LIMIT_RPM`, `AIGW_RUNTIME_KEY_SECRET_NAME`, `APIM_PUBLISHER_EMAIL`, `APIM_PUBLISHER_NAME` and `GATEWAY_APP_CLIENT_ID` from repository variables before `azd up`.

</details>

## Known gaps

![Static only](./assets/badges/static-only.svg) These are the honest limits of the current demo. None of them changes the audit or tool contracts.

| | Gap | Impact | Workaround |
|---|---|---|---|
| <img src="./assets/icons/private-endpoint.svg" width="24" alt=""/> | Private endpoints and DNS zones for Foundry, Key Vault, Container Registry and APIM inbound are not in the template | Isolation mode blocks public access without a private path | Add them from samples `15` and `16`. |
| <img src="./assets/icons/virtual-network.svg" width="24" alt=""/> | The agent subnet is created and delegated, but not bound to the Foundry account | Hosted-agent sessions use the platform's default egress | Follow the BYO VNet account configuration in the networking guide. |
| <img src="./assets/icons/foundry-agent-service.svg" width="24" alt=""/> | The hosted-agent endpoint cannot be made private with azd | Clients reach the agent over its public endpoint with Entra auth | Front it with a gateway and restrict callers by identity. |
| <img src="./assets/icons/ai-gateway.svg" width="24" alt=""/> | The AI Gateway tier module does not configure private networking | Preview tier is public in this demo | Validate Private Link and VNet integration separately. |
| <img src="./assets/icons/azure-devops.svg" width="24" alt=""/> | No first-party hosted-agent CI/CD | Delivery is DIY | Use the sample workflow as a template. |
| <img src="./assets/icons/foundry.svg" width="24" alt=""/> | One Foundry project per environment tier | Cross-environment isolation relies on separate azd environments | Keep tiers in separate resource groups. |
| <img src="./assets/icons/application-insights.svg" width="24" alt=""/> | Cross-system correlation is DIY | Joins rely on `traceparent` and APIM correlation ids | Use the [saved queries](./09-monitoring-and-audit.md#the-saved-queries). |
| <img src="./assets/icons/foundry-control-plane.svg" width="24" alt=""/> | Agent Optimizer cost estimates cover prompt agents only; exact hosted-agent OpenTelemetry environment variable names are unconfirmed | Cost and telemetry tuning is manual for hosted agents | Re-check the Learn pages before relying on either. |

## Recommendation

Run default demos on APIM Standard v2, add `both` when evaluating the AI Gateway tier, and treat preview private networking as a separate validation track. Keep the hosted-agent, tool, telemetry and audit contracts stable so posture changes do not fork application code.

Next: [11 - Demo walkthrough](./11-demo-walkthrough.md) →

---

*Last updated: 2026-10-02*
