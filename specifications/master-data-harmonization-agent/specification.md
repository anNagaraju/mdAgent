# Specification: master-data-harmonization-agent

> **Guidelines**: Read [guidelines.md](../guidelines.md) and [guidelines-agent.md](../guidelines-agent.md) before executing ANY tasks below. Follow all constraints described there throughout execution.

## Basic Setup

- [x] Read the project input (`product-requirements-document.md`, `intent.md`)
- [x] Bootstrap agent code in `assets/master-data-harmonization-agent/` using skill `sap-agent-bootstrap` (invoke from inside `assets/master-data-harmonization-agent/`, use copy commands — do NOT create files manually)
- [x] Install dependencies, validate the agent starts and responds at `/.well-known/agent.json`

## MCP Server Integration (Path B — Existing MCP Server)

- [ ] MCP server ORD ID: `sap.mcpbuilder:apiResource:business_partner_mcp_demo:v1`
- [ ] MCP spec files are at `specification/master-data-harmonization-agent/mcp-specs/`:
  - `mcp-spec-business-partner-list_business_partner.json` — list Business Partners with filtering
  - `mcp-spec-business-partner-get_business_partner.json` — retrieve a single Business Partner by key
  - `mcp-spec-business-partner-list_customer.json` — list Customer records
  - `mcp-spec-business-partner-list_supplier.json` — list Supplier records
- [ ] Wire MCP tool loading in `agent.py` using `get_mcp_tools()` from `mcp_tools.py` (canonical pattern from guidelines)
- [ ] NEVER create direct HTTP clients (`requests`, `httpx`, OData clients) — all SAP API interactions go through MCP tools
- [ ] Add MCP server dependency to `asset.yaml` under `requires`:
  ```yaml
  requires:
    - name: business-partner-mcp-demo
      kind: mcp-server
      ordId: sap.mcpbuilder:apiResource:business_partner_mcp_demo:v1
  ```
- [ ] Generate `mcp-mock.json` using the `mcp-mock-config` skill (required before tests can run)

## Agent Tools Implementation

### Tool: profile_master_data
- [ ] Implement `profile_master_data(entity_type: str, top: int = 100) -> dict` tool
  - Calls `list_business_partner` (with `top=100`) or `list_customer`/`list_supplier` based on `entity_type`
  - Computes completeness score: count non-null fields / total fields per record, aggregate as percentage
  - Returns `{"entity_type": str, "total_records": int, "completeness_score": float, "field_scores": dict}`
  - Emits M1 milestone log on completion

### Tool: detect_duplicates
- [ ] Implement `detect_duplicates(entity_type: str, confidence_threshold: float = 0.7, top: int = 100) -> list` tool
  - Fetches records via `list_business_partner` or `list_customer` (always pass `top=100` or less)
  - Applies fuzzy matching on name fields (`BusinessPartnerFullName`, `OrganizationBPName1`, `FirstName`+`LastName`) using `rapidfuzz` library
  - Applies address similarity using `BusinessPartnerAddress` expand when available
  - Applies tax ID matching via `to_BusinessPartnerTax` expand
  - Returns list of `{"source_id": str, "target_id": str, "confidence": float, "match_reasons": list}`
  - Only includes pairs with `confidence >= confidence_threshold`
  - Emits M2 milestone log on completion

### Tool: compute_golden_record
- [ ] Implement `compute_golden_record(source_id: str, target_id: str) -> dict` tool
  - Fetches full records for both IDs using `get_business_partner` with `expand=to_BusinessPartnerAddress,to_BusinessPartnerTax`
  - Applies golden record rules in order: (1) prefer most-complete record for each field, (2) prefer most-recently changed value, (3) combine unique address/tax entries
  - Returns `{"proposed_golden_record": dict, "source_record": dict, "target_record": dict, "conflicts": list}`
  - `conflicts` lists each field where source and target disagreed, with both values
  - Emits M3 milestone log on completion

### Tool: submit_merge_for_approval
- [ ] Implement `submit_merge_for_approval(source_id: str, target_id: str, golden_record: dict) -> dict` tool
  - Stores the merge proposal in-memory (dict keyed by a generated proposal ID)
  - Returns `{"proposal_id": str, "source_id": str, "target_id": str, "golden_record": dict, "status": "pending_approval"}`
  - Agent instructs user to confirm the merge using the proposal ID

### Tool: approve_and_execute_merge
- [ ] Implement `approve_and_execute_merge(proposal_id: str, approver_id: str) -> dict` tool
  - Retrieves the pending proposal from in-memory store
  - **NOTE**: Actual BP Merge API is not covered by the existing MCP server — simulate the merge execution by logging the action and returning a success response with audit details
  - Creates audit record: `{"proposal_id", "source_id", "target_id", "approver_id", "timestamp", "action": "merged", "before_state", "after_state"}`
  - Returns `{"status": "completed", "audit_record": dict}`
  - Emits M4 and M5 milestone logs
  - Human approval is MANDATORY — agent must never call this tool without explicit user confirmation

### Tool: generate_harmonization_report
- [ ] Implement `generate_harmonization_report() -> dict` tool
  - Returns all audit records from the in-memory store
  - Returns `{"total_merges": int, "audit_records": list, "generated_at": str}`

## Agent System Prompt

- [ ] Write system prompt that:
  - Identifies the agent as a Master Data Harmonization assistant
  - Lists the available tools and their purpose
  - Instructs the agent: "Always set `top` to a maximum of 100 on every tool call that accepts it. Inform the user when this limit is applied."
  - Instructs the agent: "NEVER hallucinate Business Partner IDs, names, or tax numbers. Only use data returned by tools."
  - Instructs the agent: "NEVER execute a merge without explicit user confirmation. Always present merge proposals for review first."
  - Defines the agent workflow: profile → detect → propose → await approval → execute → report

## Business Step Instrumentation

- [ ] Implement structured logging and OpenTelemetry spans for each milestone:

  **M1 — Master Data Profiling Complete**
  - `logger.info("M1.achieved: master data profiling complete — %d records scanned, quality scores computed", entity_count)`
  - `logger.warning("M1.missed: master data profiling did not complete — API access failure or no records returned")`
  - OTel span: `@tracer.start_as_current_span("m1_master_data_profiling")` on `profile_master_data`

  **M2 — Duplicate Candidates Identified**
  - `logger.info("M2.achieved: duplicate detection complete — %d candidate pairs identified", candidate_count)`
  - `logger.warning("M2.missed: duplicate detection returned no candidates or failed to execute")`
  - OTel span: `@tracer.start_as_current_span("m2_duplicate_detection")` on `detect_duplicates`

  **M3 — Golden Record Computed**
  - `logger.info("M3.achieved: harmonization analysis complete — %d merge proposals generated", proposal_count)`
  - `logger.warning("M3.missed: golden record computation failed or no proposals could be generated")`
  - OTel span: `@tracer.start_as_current_span("m3_golden_record_computation")` on `compute_golden_record`

  **M4 — Human Approval Received**
  - `logger.info("M4.achieved: merge proposal approved by %s for %s", approver_id, record_id)`
  - `logger.warning("M4.missed: no approval received or all proposals rejected")`

  **M5 — SAP Master Data Updated**
  - `logger.info("M5.achieved: master data updated in SAP — merged %s into %s, audit record created", source_id, target_id)`
  - `logger.warning("M5.missed: SAP API call failed for merge %s → %s — %s", source_id, target_id, error_message)`
  - OTel span: `@tracer.start_as_current_span("m5_master_data_update")` on `approve_and_execute_merge`

- [ ] Verify `auto_instrument()` is called at top of `main.py` before any AI framework imports
- [ ] Extract all business logic from `stream()` into `_run_agent()` async helper; instrument `_run_agent()` — never wrap `yield` inside `with tracer.start_as_current_span(...)`

## Dependencies

- [ ] Add to `requirements.txt`:
  - `rapidfuzz>=3.0.0` (fuzzy string matching for duplicate detection)
  - `opentelemetry-api` (already included via bootstrap — verify)
- [ ] Run `pip install -r requirements.txt` and confirm no errors

## Testing

- [ ] `conftest.py` only sets `IBD_TESTING=true` — patch `mcp_tools.get_mcp_tools` to return mock tools built from `mcp-mock.json`
- [ ] Write unit test: `test_profile_master_data.py` — mock `list_business_partner` returns 5 sample BP records; assert completeness score is a float between 0 and 1
- [ ] Write unit test: `test_detect_duplicates.py` — mock `list_business_partner` returns 2 records with near-identical names; assert at least one duplicate pair is returned with confidence > 0.7
- [ ] Write unit test: `test_compute_golden_record.py` — mock `get_business_partner` returns two BP records with conflicting fields; assert golden record is returned with `conflicts` list populated
- [ ] Write unit test: `test_submit_merge_for_approval.py` — call `submit_merge_for_approval`; assert returned proposal has `status = "pending_approval"` and valid `proposal_id`
- [ ] Write unit test: `test_approve_and_execute_merge.py` — submit a proposal first, then approve it; assert returned status is `"completed"` and audit record is present
- [ ] Write unit test: `test_generate_harmonization_report.py` — after approving one merge, call `generate_harmonization_report`; assert `total_merges >= 1`
- [ ] Write integration test: `test_integration_full_flow.py` — mock LLM and MCP tools; simulate agent receiving "Find and harmonize duplicate business partners", verify agent calls profiling, detection, and proposal tools in sequence
- [ ] Run each unit test immediately after writing: `pytest tests/test_<name>.py`
- [ ] Run `pytest` from `assets/master-data-harmonization-agent/` (no args) — coverage must be ≥ 70%
- [ ] Verify `assets/master-data-harmonization-agent/app/agent.py` has exactly 3 decorated functions: run `grep -c "^@agent_model\|^@agent_config\|^@prompt_section" assets/master-data-harmonization-agent/app/agent.py` → must return 3
- [ ] Run final `pytest` (no args) to generate `test_report.json`
- [ ] Verify `test_report.json` exists in `assets/master-data-harmonization-agent/`

## Agent Evaluation (Post-Testing)

- [ ] Invoke `sap-aeval-generate-tool-schema` skill from `assets/master-data-harmonization-agent/` → writes `tools.json`
- [ ] Invoke `sap-aeval-generate-testcase` skill passing `tools.json` and PRD path → writes `aeval/eval.yaml` and `aeval/testcases/`
- [ ] Review generated test cases; replace placeholder values with realistic BP IDs and names
