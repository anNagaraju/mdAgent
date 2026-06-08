# Master Data Harmonization & Deduplication Agent

AI-powered agent to detect, harmonize, and resolve duplicate master data records across SAP systems.

## Business challenge

Organizations running SAP S/4HANA struggle with fragmented and inconsistent master data — duplicate Business Partners, mismatched Customer/Vendor records, and inconsistent Product/Material masters — arising from migrations, integrations, and manual entry. This leads to erroneous transactions, compliance risks, reporting inaccuracies, and operational inefficiency. An autonomous agent is needed to continuously scan master data, detect duplicates using fuzzy matching and business rules, harmonize attributes to a golden record standard, and trigger merge/update actions via SAP APIs.

## Key Milestones

1. **Master Data Profiling** — Agent scans Business Partner, Customer, and Product entities; profiles completeness and quality scores.
2. **Duplicate Detection** — Agent identifies candidate duplicate pairs using name/address/tax ID similarity and confidence scoring.
3. **Harmonization Analysis** — Agent applies golden record rules to resolve attribute conflicts and determine the surviving record.
4. **Merge/Update Recommendation** — Agent presents a ranked list of merge candidates with proposed master record values for human review or auto-approval.
5. **SAP System Update** — Agent executes approved merges/updates via Business Partner Merge and Product Master APIs and confirms completion.

## Business Architecture (RBA)

### End-to-End Process

Governance (E2E)

### Process Hierarchy

```
Governance (E2E)
└── Manage Governance, Risk and Compliance (generic)
    └── Manage cybersecurity, data protection and privacy (BPS-400)
        └── Manage data privacy
        └── Manage data protection
    └── Manage identity and access governance (BPS-399)
        └── Manage access governance and authorisations
└── Manage Information Technology (generic)
    └── Manage IT governance (BPS-456)
        └── Operate IT Governance Framework
```

### Summary

Master data harmonization maps to the Governance E2E under data protection/privacy and IT governance sub-processes, with cross-cutting relevance to all core domains wherever Business Partner, Product, and Customer master data drive transactional accuracy.

## Fit Gap Analysis

| Requirement (business) | Standard asset(s) found | API ORD ID | MCP Server ORD ID | Gap? | Notes / assumptions |
| --- | --- | --- | --- | --- | --- |
| Read & update Business Partner records | SAP S/4HANA Cloud (Public/Private) | `sap.s4:apiResource:API_BUSINESS_PARTNER:v1` | `sap.mcpbuilder:apiResource:business_partner_mcp_demo:v1` ✓ | No | Full CRUD via OData + MCP server available |
| Detect duplicate Business Partners | Contact/Account Duplicate Check APIs (S/4HANA) | — (no ORD ID) | — | Maybe | API available but no MCP; custom agent logic needed for fuzzy match scoring |
| Merge duplicate Business Partners | Business Partner Merge API (S/4HANA) | — (no ORD ID) | — | Maybe | API available; agent must orchestrate merge decisions |
| Read & update Product/Material masters | SAP S/4HANA Product Master A2X | `sap.s4:apiResource:API_PRODUCT_SRV:v1` | — | Yes | No MCP server; direct OData calls required |
| Data profiling & maturity assessment | Data Profiling / Data Maturity Assessment APIs | — (no ORD ID) | — | Maybe | REST APIs available; agent integrates for quality scoring |
| Harmonization rule engine | Data Harmonization REST API | — (no ORD ID) | — | Yes | No standard product covers custom harmonization logic; custom agent rules required |
| Audit trail & compliance logging | SAP S/4HANA Cloud + SAP Data Protection | `sap.s4:apiResource:API_CRDTMBUSINESSPARTNER:v1` | — | Maybe | Logging via S/4HANA standard; custom audit records may be needed |

### Key findings

- An MCP server exists for the Business Partner (A2X) API — the agent can leverage it directly for read/write operations on Business Partners.
- Duplicate check APIs (Contact, Account, Individual Customer) exist in S/4HANA but lack ORD IDs and MCP servers; the agent must call them directly or implement its own fuzzy-matching logic.
- The Business Partner Merge API is the standard SAP mechanism for deduplication; the agent orchestrates merge decisions on top of it.
- Product Master harmonization has no MCP coverage; OData calls to `API_PRODUCT_SRV` are the integration path.
- Custom harmonization rule logic (golden record selection, attribute conflict resolution) has no standard SAP product coverage and must be implemented in the agent.
- Data Profiling and Maturity Assessment REST APIs provide quality scoring inputs to the agent's analysis loop.

## Recommendations

### AI Agent for Master Data Harmonization and Deduplication

#### Executive Summary

Python AI agent using SAP APIs to detect, harmonize, and merge duplicates.

#### Recommended Solution

A pro-code Python AI agent (A2A protocol) deployed on SAP BTP that autonomously:
1. Queries Business Partner, Customer, and Product master data via SAP S/4HANA APIs (Business Partner MCP server + OData).
2. Runs duplicate detection using fuzzy name/address/tax ID matching with configurable confidence thresholds.
3. Applies golden record rules (most-complete, most-recent, authoritative-source) to resolve attribute conflicts.
4. Surfaces a ranked merge candidate list; supports both human-in-the-loop approval and auto-merge modes.
5. Executes approved merges via the Business Partner Merge and Product Master APIs.
6. Generates a harmonization audit report with before/after states for compliance.

SAP components leveraged: SAP S/4HANA Cloud (Business Partner A2X MCP, Product Master OData, BP Merge OData), SAP BTP AI Core for LLM-assisted conflict resolution.

#### Recommended solution category

AI Agent

#### Intent fit
88%
