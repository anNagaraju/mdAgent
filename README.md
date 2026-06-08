# mdAgent
AI Agent for Master Data Harmonization and Deduplication
Intent
AI-powered agent to detect, harmonize, and resolve duplicate master data records across SAP systems.
Problem Statement
Organizations running SAP S/4HANA struggle with fragmented and inconsistent master data — duplicate Business Partners, mismatched Customer/Vendor records, and inconsistent Product/Material masters — arising from migrations, integrations, and manual entry. This leads to erroneous transactions, compliance risks, reporting inaccuracies, and operational inefficiency. An autonomous agent is needed to continuously scan master data, detect duplicates using fuzzy matching and business rules, harmonize attributes to a golden record standard, and trigger merge/update actions via SAP APIs.
Goals and Metrics
1.	Master Data Profiling — Agent scans Business Partner, Customer, and Product entities; profiles completeness and quality scores.
2.	Duplicate Detection — Agent identifies candidate duplicate pairs using name/address/tax ID similarity and confidence scoring.
3.	Harmonization Analysis — Agent applies golden record rules to resolve attribute conflicts and determine the surviving record.
4.	Merge/Update Recommendation — Agent presents a ranked list of merge candidates with proposed master record values for human review or auto-approval.
5.	SAP System Update — Agent executes approved merges/updates via Business Partner Merge and Product Master APIs and confirms completion.

A pro-code Python AI agent (A2A protocol) deployed on SAP BTP that autonomously:
1.	Queries Business Partner, Customer, and Product master data via SAP S/4HANA APIs (Business Partner MCP server + OData).
2.	Runs duplicate detection using fuzzy name/address/tax ID matching with configurable confidence thresholds.
3.	Applies golden record rules (most-complete, most-recent, authoritative-source) to resolve attribute conflicts.
4.	Surfaces a ranked merge candidate list; supports both human-in-the-loop approval and auto-merge modes.
5.	Executes approved merges via the Business Partner Merge and Product Master APIs.
6.	Generates a harmonization audit report with before/after states for compliance. SAP components leveraged: SAP S/4HANA Cloud (Business Partner A2X MCP, Product Master OData, BP Merge OData), SAP BTP AI Core for LLM-assisted conflict resolution.
   
What was built?
A Python AI Agent (A2A protocol, deployed on SAP BTP) that autonomously detects, harmonizes, and resolves duplicate master data records across SAP S/4HANA systems.

Solution structure
solution.yaml                                  # Solution manifest
assets/master-data-harmonization-agent/
├── asset.yaml                                 # Agent asset definition
├── mcp-mock.json                              # Mock MCP responses for testing
├── requirements.txt                           # incl. rapidfuzz for fuzzy matching
├── app/
│   ├── agent.py                               # Agent with 6 harmonization tools + MCP wiring
│   ├── harmonization_tools.py                 # Core logic: profiling, dedup, golden record, merge
│   ├── main.py                                # A2A server
│   ├── mcp_tools.py                           # MCP tool loader (mock/prod)
│   └── util.py                               # Retry + tool name utilities
├── tests/ (7 test files)                      # 56 tests, 72% coverage
└── test_report.json                           # Test execution report
Key capabilities:
Tool	Purpose
profile_master_data	Score BP/Customer/Supplier completeness
detect_duplicates	Fuzzy name + tax ID matching (rapidfuzz)
compute_golden_record	Resolve attribute conflicts, pick best values
submit_merge_for_approval	Stage merge for human review
approve_and_execute_merge	Execute approved merge via SAP API
generate_harmonization_report	Audit trail of all merges
Integrations:
Business Partner MCP Server (sap.mcpbuilder:apiResource:business_partner_mcp_demo:v1) — list/get Business Partners, Customers, Suppliers from SAP S/4HANA
Guardrail: Merges are never executed autonomously — explicit human approval always required
Milestones instrumented (M1–M5)
All 5 business steps emit [M#.achieved|missed] structured logs + OpenTelemetry spans for full observability.
