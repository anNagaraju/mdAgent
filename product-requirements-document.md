# Product Requirements Document (PRD)

**Title:** Master Data Harmonization & Deduplication Agent  
**Date:** 2026-06-08  
**Owner:** Data Governance Team  
**Solution Category:** AI Agent

---

## Product Purpose & Value Proposition

**Elevator Pitch:**  
Organizations accumulate duplicate and inconsistent master data across SAP systems over time — leading to billing errors, compliance failures, and broken analytics. This AI agent continuously scans Business Partner, Customer, and Product records, detects duplicates using intelligent matching, applies golden record logic, and executes approved merges via SAP APIs.

**Business Need:**  
Master data fragmentation — caused by migrations, integrations, and manual entry — results in duplicate Business Partners, mismatched customer/vendor records, and inconsistent Product/Material masters. Current processes rely on manual identification and remediation, which is error-prone, slow, and non-scalable.

**Expected Value:**  
- Reduction in duplicate master data records across SAP S/4HANA  
- Improved transactional accuracy in procurement, sales, and finance  
- Reduced compliance risk through consistent data quality and audit trails

**Product Objectives (Prioritized):**
1. Detect duplicate master data records (Business Partners, Customers, Products) with high recall and precision
2. Harmonize master data attributes to a defined golden record standard
3. Execute approved merge/update actions via SAP APIs with a full audit trail

---

## Requirements

### Must-Have Requirements

**R1: Master Data Profiling**
- **User Story**: As a data steward, I need the agent to profile Business Partner and Product records so that I understand data completeness and quality before harmonization.
- **Acceptance Criteria**:
  - Given access to SAP S/4HANA APIs, when the agent runs a profiling scan, then it returns completeness scores per entity type.
- **Priority Rank**: 1

**R2: Duplicate Detection**
- **User Story**: As a data steward, I need the agent to identify duplicate Business Partner and Product records using fuzzy matching so that I can review and resolve them.
- **Acceptance Criteria**:
  - Given master data records, when the agent applies matching rules (name, address, tax ID similarity), then it returns a ranked list of duplicate candidate pairs with confidence scores.
- **Priority Rank**: 2

**R3: Golden Record Harmonization**
- **User Story**: As a data steward, I need the agent to resolve attribute conflicts between duplicate records so that a single authoritative master record can be identified.
- **Acceptance Criteria**:
  - Given a duplicate pair, when the agent applies golden record rules (most-complete, most-recent, authoritative-source), then it produces a proposed merged record.
- **Priority Rank**: 3

**R4: Human-in-the-Loop Approval**
- **User Story**: As a data steward, I need to review and approve or reject merge proposals before they are applied to SAP so that I maintain control over master data changes.
- **Acceptance Criteria**:
  - Given a merge proposal, when a steward reviews it, then they can approve, reject, or modify the proposed golden record.
- **Priority Rank**: 4

**R5: SAP Master Data Update**
- **User Story**: As a data steward, I need approved merges to be written back to SAP S/4HANA automatically so that the system reflects the harmonized data without manual effort.
- **Acceptance Criteria**:
  - Given an approved merge decision, when the agent calls the Business Partner Merge API or Product Master OData, then the record is updated in SAP and confirmation is returned.
- **Priority Rank**: 5

**R6: Harmonization Audit Report**
- **User Story**: As a compliance officer, I need a report of all merge actions performed so that I can demonstrate data governance compliance.
- **Acceptance Criteria**:
  - Given completed merge operations, when the agent generates an audit report, then it contains before/after states, decision timestamps, and approver identity.
- **Priority Rank**: 6

---

## Solution Architecture

**Architecture Overview:**  
A Python AI agent (A2A protocol) deployed on SAP BTP, integrated with SAP S/4HANA Cloud via Business Partner MCP server and OData APIs. The agent operates in a detect → analyze → propose → approve → execute loop.

**Key Components:**
- **Master Data Agent (Python/A2A)**: Core reasoning and orchestration logic running on SAP BTP AI Core
- **Business Partner MCP Server**: `sap.mcpbuilder:apiResource:business_partner_mcp_demo:v1` — read/write Business Partner records
- **S/4HANA OData APIs**: Business Partner Merge, Product Master (A2X), Contact/Account Duplicate Check
- **Approval Interface**: Lightweight review UI or structured output for human-in-the-loop decisions
- **Audit Log Store**: Persistent record of all agent actions and merge decisions

**Integration Points:**
- SAP S/4HANA Cloud — Business Partner A2X API (`sap.s4:apiResource:API_BUSINESS_PARTNER:v1`) via MCP server
- SAP S/4HANA Cloud — Product Master OData (`sap.s4:apiResource:API_PRODUCT_SRV:v1`)
- SAP S/4HANA Cloud — Business Partner Merge OData (direct call)
- SAP S/4HANA Cloud — Duplicate Check APIs (Contact, Account, Individual Customer)

---

### Agent Extensibility & Instrumentation

**Agent Extensibility:**
- Matching rules (fuzzy thresholds, field weights) are configurable without code changes
- Golden record resolution strategy is pluggable (most-complete, most-recent, source-priority)
- New entity types (e.g., Vendor, Cost Center) can be added as additional tool connectors
- Approval workflow is decoupled from agent logic to allow future BTP Workflow integration

**Business Step Instrumentation:**
- All five key business milestones (see Milestones section) emit structured log statements
- Log pattern: `[MILESTONE_ID].[achieved|missed]: [description]`
- Logs are emitted to stdout and captured by SAP BTP Application Logging for observability

---

### Automation & Agent Behaviour

**Automation Level:** Hybrid (autonomous detection + human-approved execution)

**Actions the system performs without human approval:**
- Master data profiling and quality scoring
- Duplicate candidate pair identification and confidence scoring
- Golden record computation and conflict resolution analysis

**Actions that require human review or approval:**
- Merge execution in SAP S/4HANA
- Deletion or deactivation of duplicate records

**Model or engine used:** LLM via SAP Generative AI Hub (GPT-4o or equivalent) for conflict reasoning; rule-based fuzzy matching for duplicate detection

**Knowledge & data sources accessed:**
- SAP S/4HANA Business Partner records (via MCP server)
- SAP S/4HANA Product/Material master records (via OData)
- Duplicate Check API responses from S/4HANA

**Tools or connectors invoked:**
- `business_partner_mcp_demo`: read Business Partner data, write harmonized records (write — medium risk)
- `API_BUSINESS_PARTNER` OData: full CRUD on Business Partner (write — medium risk)
- `API_PRODUCT_SRV` OData: read/update Product master (write — medium risk)
- Business Partner Merge API: merge duplicate BP records (high risk — requires human approval)
- Duplicate Check APIs: detect candidate duplicates (read-only)

**Guardrails & fail-safes:**
- Merge actions are NEVER executed autonomously; always require explicit human approval
- Confidence score below 80% triggers mandatory human review before any action
- Agent never deletes records; only marks for review or merges with approval
- All API write failures are logged and surfaced to the steward; agent does not retry silently

---

## Milestones

### M1: Master Data Profiling Complete
- **Description**: Agent has scanned and profiled all target entity types
- **Achieved when**: Profiling scan returns completeness scores for Business Partner and Product entities
- **Log on achievement**: `M1.achieved: master data profiling complete — {entity_count} records scanned, quality scores computed`
- **Log on miss**: `M1.missed: master data profiling did not complete — API access failure or no records returned`

### M2: Duplicate Candidates Identified
- **Description**: Agent has produced a ranked list of duplicate candidate pairs with confidence scores
- **Achieved when**: At least one duplicate candidate pair is identified above the minimum confidence threshold
- **Log on achievement**: `M2.achieved: duplicate detection complete — {candidate_count} candidate pairs identified`
- **Log on miss**: `M2.missed: duplicate detection returned no candidates or failed to execute`

### M3: Golden Record Computed
- **Description**: Agent has resolved attribute conflicts and produced a proposed merged record for each candidate pair
- **Achieved when**: Golden record proposal generated for all candidate pairs above the approval threshold
- **Log on achievement**: `M3.achieved: harmonization analysis complete — {proposal_count} merge proposals generated`
- **Log on miss**: `M3.missed: golden record computation failed or no proposals could be generated`

### M4: Human Approval Received
- **Description**: Data steward has reviewed and approved at least one merge proposal
- **Achieved when**: Steward submits an approval decision for a merge candidate
- **Log on achievement**: `M4.achieved: merge proposal approved by {approver_id} for {record_id}`
- **Log on miss**: `M4.missed: no approval received within review window or all proposals rejected`

### M5: SAP Master Data Updated
- **Description**: Approved merge has been successfully written back to SAP S/4HANA
- **Achieved when**: Business Partner Merge or Product Master API returns success for approved merge
- **Log on achievement**: `M5.achieved: master data updated in SAP — merged {source_id} into {target_id}, audit record created`
- **Log on miss**: `M5.missed: SAP API call failed for merge {source_id} → {target_id} — {error_message}`
