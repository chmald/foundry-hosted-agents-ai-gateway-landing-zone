# Changelog

## 1.2.0 - 2026-10-02

Official agent hosts, AI Gateway tier proven live, and isolation mode now creates its private endpoints.

### What changed

- **Official hosts, no fallback.** `agent-maf` runs on `agent_framework_foundry_hosting.ResponsesHostServer` and `agent-langgraph` on `langchain_azure_ai.agents.hosting.ResponsesHostServer`; both serve `responses` 2.0.0 on port 8088. The hand-written FastAPI fallback was removed. Agent requirements install with `--pre`; the Dockerfile gained `ARG PIP_INDEX_URL` and `chown app:app /app` (otherwise `PermissionError: /app/.agentserver`).
- **Runtime configuration.** Hosted agents read `HOSTED_DEFAULT_GATEWAY`, `HOSTED_PROTOCOL` and `HOSTED_RUNTIME` (the unprefixed `AGENT_*` names are a local-run fallback) and the platform-injected `APPLICATIONINSIGHTS_CONNECTION_STRING`, `FOUNDRY_AGENT_INSTANCE_CLIENT_ID` and `FOUNDRY_HOSTING_ENVIRONMENT`.
- **AI Gateway tier is live.** The tier is `Microsoft.ApiManagement/service@2025-09-01-preview` with sku `AIGateway` (it needs the `AIGatewayPreview` feature registered). The 1.1.0 `Microsoft.ApiManagement/aigateways` / `2026-05-01-preview` shape never worked and was removed. Model alias name must equal the request `model` (`chat`), the provider `modelName` must equal the Foundry deployment name, and the OpenAPI tool server needs an absolute `servers[0].url`.
- **Identity finding.** A hosted agent's effective runtime principal is its **instance identity** (`azd ai agent show <agent> --output json` -> `instance_identity.principal_id`), distinct from the blueprint and the Foundry project identity. It only exists after deploy, so Bicep cannot grant it **Key Vault Secrets User**.
- **Key delivery.** New `AIGW_KEY_DELIVERY` (`keyvault` default, `env` opt-in) and a `postdeploy` hook (`infra/hooks/postdeploy-agents.ps1`) that grants the instance identity Key Vault Secrets User. Under a Key Vault network policy (`ForbiddenByConnection`), isolation mode is the proper fix and `env` delivery the demo-only compromise. The hook is covered by offline tests but was **not live-verified** (the grant was made by hand).
- **Isolation mode creates private endpoints and DNS.** Nine private DNS zones and eight private endpoints (Foundry, Key Vault, Container Registry, APIM v2, AI Gateway tier, Cosmos DB, Storage, AI Search), `snet-aigw`, `AIGW_SUBNET_PREFIX` and `AIGW_INBOUND_PRIVATE_ENDPOINT`. Validated with `az bicep build` and `what-if` (127 resources, no errors); **not deployed live**.
- **Telemetry fixes.** The tier writes LLM and MCP calls to Application Insights `AppRequests`, not `ApiManagementGatewayLlmLog`. Saved queries 02, 04, 09 and 11 were rewritten; `run_audit_queries.py` substitutes `--trace-id`.
- **Docs and visuals.** Seven new diagrams (service catalog, prerequisites map, manual deployment steps, testing matrix, troubleshooting decision tree, gateway identity comparison, scale limits), badges for every status table, a doc-visuals linter (`scripts/lint_doc_visuals.py`) and test (`tests/test_doc_visuals.py`).

### Live validation (2026-10-02)

Disposable `eastus2` deployment `fhagl1002`. Evidence and charts: [`docs/04-testing.md`](./docs/04-testing.md#live-validation-2026-10-02), [`docs/09-monitoring-and-audit.md`](./docs/09-monitoring-and-audit.md#live-evidence), [`docs/11-demo-walkthrough.md`](./docs/11-demo-walkthrough.md#live-evidence); raw run in `docs/assets/evidence/live-run-2026-10-02.json`.

- **Matrix:** both agents (MAF, LangGraph) x both gateways (APIM Standard v2, AI Gateway tier) passed S1-S5. Gateway validation: 401 without credential, 200 with, MCP `initialize`/`tools/list`/`tools/call` (`catalog_list_items`, `records_list_records`), and the 429 probe (183 of 240 requests throttled on the tier).
- **Saved queries (rows):** 01=75, 02=5, 03=70, 04=104, 05=67, 06=100, 07=0, 08=0, 09=0, 10=942, 11=30. Queries 07, 08 and 09 are empty by environment, not defects.
- **Durations:** provision #2 4m45s and #3 3m04s (#1 failed on the Container Apps registry pull identity); catalog deploy 1m24s, records 1m19s; MAF v1/v2/v3 2m48s / 1m43s / 1m48s; LangGraph 2m16s / 2m07s / 1m59s; APIM v2 walkthrough 32s.
- **Teardown:** `azd down --purge --force` took 36m33s; the Cognitive Services account was purged manually and the Entra app deleted by hand.

| # | Defect | Fix |
|---|---|---|
| 1 | Container Apps user-assigned identity could not pull from the registry | Grant `AcrPull` to the ACA identity |
| 2 | Missing outputs `AZURE_AI_PROJECT_ID`, `AZURE_AI_PROJECT_ENDPOINT`, `AIGW_RUNTIME_KEY_SECRET_NAME` | Added to `main.bicep` |
| 3 | Gateway provider `modelName` did not match the Foundry deployment name | Provider `modelName` = deployment name |
| 4 | `validate_gateway` used one tool name set and a serial 429 probe | Per-gateway tool names; concurrent probe |
| 5 | `postprovision` strict-mode and `listSecrets` parsing errors | Hook fixed |
| 6 | Hosted agent could not read Key Vault under policy | `AIGW_KEY_DELIVERY` and env fallback |
| 7 | Query 02 returned blank agent and user | Union of LLM log, tier `AppRequests` and agent spans |
| 8 | Query 11 returned placeholder noise | Rewritten over `AppRequests` and the MCP log |
| 9 | Query 04 returned thousands of rows (trace parameter never substituted) | `--trace-id` substitution |
| 10 | Query 09 failed: `ErrorMessage` does not exist | Use `LastErrorMessage` |
| 11 | Evidence renderer captions and labels | Updated; matrix labels show host type |

### Remaining gaps

- Network isolation mode is not deployed live; the hosted-agent endpoint is not private via azd, and APIM and the tier stay public until a manual lockdown.
- The `postdeploy` RBAC hook and the AI Gateway tier private endpoint are not live-verified.
- Only the 429 policy card was exercised on the tier (token limit, content safety and IP filter are deployed but untested).

### History

- The 1.1.0 `DD_*` telemetry variables and the `FHAGL_USE_FASTAPI_FALLBACK` switch were removed in this release.

## 1.1.0 - 2026-10-01

Dual-gateway and dual-framework update. Superseded in part by 1.2.0 (see corrections below).

### What changed

- Added `AI_GATEWAY_MODE=both` so APIM Standard v2 and AI Gateway tier preview can be deployed and tested side by side.
- Documented AI Gateway tier preview boundaries: East US 2 / Sweden Central, runtime `api-key` auth, gateway-scoped runtime keys, no SLA, pricing TBA, and standalone portal `ai.gateway.azure.com`. (The 1.1.0 management API shape was wrong; see 1.2.0.)
- Replaced the legacy single `src/hosted-agent` narrative with two hosted-agent implementations: `src/agents/maf` and `src/agents/langgraph`.
- Updated deployment and testing instructions for `AGENT_DEFAULT_GATEWAY=aigateway` plus `azd deploy agent-maf agent-langgraph` second pass.
- Added configuration coverage for all new variables, outputs, demo ID keys, runtime env vars, and script surfaces.
- Updated diagrams for architecture, gateway modes, identity token flow, azd deployment flow, configuration flow, and agent-framework comparison.
- Added query 11 for AI Gateway tier telemetry comparison.

### Live validation (2026-10-01)

Disposable `eastus2` deployment, torn down afterwards. Raw run: `docs/assets/evidence/live-run-2026-10-01.json`.

- **Live-tested (APIM Standard v2):** `azd up`, gateway validation, and walkthrough S1-S5 for both agents passed.
- **AI Gateway tier not deployable in 1.1.0:** the `aigateways` resource type failed with `InvalidResourceType`. Fixed in 1.2.0 by using the `service` resource with sku `AIGateway`.
- **17 defects found and fixed live** (Bicep ordering, RBAC, unsupported Standard v2 policy, MCP shape, container build context, reserved hosted-agent env names, schema drift in query 06 and others). Added `scripts/render_evidence.py` plus `docs/assets/evidence/` charts, and `matplotlib` to `scripts/requirements.txt`.
- **Teardown caveat:** `azd down --purge --force` left API Management behind; an explicit `az group delete` was required.

## 1.0.0 - 2026-09-30

Initial reusable demo pattern for Foundry hosted agents behind an APIM AI Gateway landing zone.

### Shipped

- Core document set: README plus `docs/00` through `docs/12`.
- Distribution guardrails: `.gitignore` and `demo-ids.template.json`.
- Locked decisions D1-D10, gateway-mode comparison, tenant-explicit quick start, manual deployment path, testing/troubleshooting runbooks, and diagrams.

---

*Last updated: 2026-10-02*
