# mdAgent
AI Agent for Master Data Harmonization and Deduplication
A pro-code Python AI agent (A2A protocol) deployed on SAP BTP that autonomously:
1.	Queries Business Partner, Customer, and Product master data via SAP S/4HANA APIs (Business Partner MCP server + OData).
2.	Runs duplicate detection using fuzzy name/address/tax ID matching with configurable confidence thresholds.
3.	Applies golden record rules (most-complete, most-recent, authoritative-source) to resolve attribute conflicts.
4.	Surfaces a ranked merge candidate list; supports both human-in-the-loop approval and auto-merge modes.
5.	Executes approved merges via the Business Partner Merge and Product Master APIs.
6.	Generates a harmonization audit report with before/after states for compliance. SAP components leveraged: SAP S/4HANA Cloud (Business Partner A2X MCP, Product Master OData, BP Merge OData), SAP BTP AI Core for LLM-assisted conflict resolution.
