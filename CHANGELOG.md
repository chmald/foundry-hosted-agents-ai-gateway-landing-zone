# Changelog

## 1.1.0 - 2026-10-01

Dual-gateway and dual-framework update.

### What changed

- Added `AI_GATEWAY_MODE=both` so APIM Standard v2 and AI Gateway tier preview can be deployed and tested side by side.
- Documented AI Gateway tier preview boundaries: East US 2 / Sweden Central, management API `2026-05-01-preview`, runtime `api-key` auth, gateway-scoped runtime keys, no SLA, pricing TBA, and standalone portal `ai.gateway.azure.com`.
- Replaced the legacy single `src/hosted-agent` narrative with two hosted-agent implementations: `src/agents/maf` and `src/agents/langgraph`.
- Updated deployment and testing instructions for `AGENT_DEFAULT_GATEWAY=aigateway` plus `azd deploy agent-maf agent-langgraph` second pass.
- Added configuration coverage for all new variables, outputs, demo ID keys, runtime env vars, and script surfaces.
- Updated diagrams for architecture, gateway modes, identity token flow, azd deployment flow, configuration flow, and agent-framework comparison.
- Added query 11 for AI Gateway tier OpenTelemetry GenAI telemetry comparison.

### Verification

- Microsoft Learn pages checked for AI Gateway tier overview, models/tools, security/operations, private networking, quickstart, Microsoft Agent Framework hosted agents, and LangGraph hosted agents.
- Expected validation: `pytest tests/test_configuration.py` in `%TEMP%\fhagl-venv`, draw.io validation/export, relative link/anchor check, and diagram freshness check.
- Live validation: **pending**. The concurrent deployment report `v11-live-report.md` was not present when this update was authored; reconcile this section when the report appears.

## 1.0.0 - 2026-09-30

Initial reusable demo pattern for Foundry hosted agents behind an APIM AI Gateway landing zone.

### Shipped

- Core document set: README plus `docs/00` through `docs/12`.
- Distribution guardrails: `.gitignore` and `demo-ids.template.json`.
- Locked decisions D1-D10, gateway-mode comparison, tenant-explicit quick start, manual deployment path, testing/troubleshooting runbooks, and diagrams.

---

*Last updated: 2026-10-01*
