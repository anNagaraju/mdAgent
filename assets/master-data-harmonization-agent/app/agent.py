import logging
import time
from dataclasses import dataclass
from typing import AsyncGenerator, Literal, Sequence

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool, StructuredTool
from langchain_litellm import ChatLiteLLM
from langgraph.checkpoint.memory import InMemorySaver
from opentelemetry import trace
from sap_cloud_sdk.agent_decorators import agent_config, agent_model, prompt_section

from harmonization_tools import (
    profile_master_data_sync,
    detect_duplicates_sync,
    compute_golden_record_sync,
    submit_merge_proposal,
    execute_merge_sync,
    get_harmonization_report,
)
from mcp_tools import get_mcp_tools

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Matching constants
DEFAULT_CONFIDENCE_THRESHOLD = 0.7
DEFAULT_TOP = 100


@agent_model(
    key="config.model",
    label="LLM Model",
    description="The language model powering this agent",
)
def get_model_name() -> str:
    return "sap/anthropic--claude-4.5-sonnet"


@agent_config(
    key="config.temperature",
    label="LLM Temperature",
    description="Controls randomness of responses (0.0 = deterministic, 1.0 = creative)",
)
def get_temperature() -> float:
    return 0.0


@prompt_section(
    key="prompts.system",
    label="System Prompt",
    description="The full system prompt defining the agent's role and behavior",
    validation={"format": "markdown", "max_length": 5000},
)
def get_system_prompt() -> str:
    return """You are a Master Data Harmonization Agent. You help data stewards identify, analyze, and resolve duplicate master data records in SAP S/4HANA systems.

Your capabilities:
- Profile master data quality (Business Partners, Customers, Suppliers) to compute completeness scores
- Detect duplicate records using fuzzy name, address, and tax ID matching
- Compute golden records by resolving attribute conflicts using completeness and recency rules
- Submit merge proposals for human review and execute approved merges
- Generate harmonization audit reports

Available tools:
- profile_master_data: Profile and score master data completeness for a given entity type
- detect_duplicates: Detect duplicate pairs in retrieved records using fuzzy matching
- compute_golden_record: Compute proposed golden record from two duplicate records
- submit_merge_for_approval: Store a merge proposal for human review
- approve_and_execute_merge: Execute an approved merge (requires explicit user confirmation)
- generate_harmonization_report: Return audit report of all completed merges
- MCP tools (prefixed): Use list_business_partner, list_customer, list_supplier to fetch records from SAP S/4HANA

Rules:
- NEVER hallucinate Business Partner IDs, names, tax numbers, or addresses. Only use data returned by tools.
- Always set `top` to a maximum of 100 on every tool call that accepts it. Inform the user when this limit is applied.
- NEVER execute a merge without explicit user confirmation. Always present the merge proposal and wait for approval.
- When presenting duplicate candidates, always show the confidence score and the matching criteria.
- Merges are irreversible — always confirm the source and target records with the user before proceeding.

Standard workflow:
1. Fetch records using MCP tools (list_business_partner, list_customer, or list_supplier)
2. Call profile_master_data with the fetched records
3. Call detect_duplicates to find candidate pairs
4. For each pair, call compute_golden_record and submit_merge_for_approval
5. Present proposals to the user for review
6. Only after explicit user approval, call approve_and_execute_merge
7. Call generate_harmonization_report to confirm completion"""


def _build_harmonization_tools() -> list[BaseTool]:
    """Build local harmonization tools as LangChain StructuredTools."""

    async def profile_master_data(entity_type: str, records_json: str) -> str:
        """Profile completeness of master data records. entity_type: 'BusinessPartner', 'Customer', or 'Supplier'. records_json: JSON array of records fetched from SAP."""
        import json
        try:
            records = json.loads(records_json) if isinstance(records_json, str) else records_json
        except Exception:
            return '{"error": "Invalid records_json — expected a JSON array"}'
        result = profile_master_data_sync(records, entity_type)
        return json.dumps(result)

    async def detect_duplicates(records_json: str, confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD) -> str:
        """Detect duplicate pairs in master data records. records_json: JSON array of Business Partner records. confidence_threshold: minimum score to include (default 0.7)."""
        import json
        try:
            records = json.loads(records_json) if isinstance(records_json, str) else records_json
        except Exception:
            return '{"error": "Invalid records_json"}'
        candidates = detect_duplicates_sync(records, confidence_threshold)
        return json.dumps({"candidate_pairs": candidates, "total": len(candidates)})

    async def compute_golden_record(source_json: str, target_json: str) -> str:
        """Compute a proposed golden record from two duplicate records. source_json: JSON of the source Business Partner record. target_json: JSON of the target Business Partner record."""
        import json
        try:
            source = json.loads(source_json) if isinstance(source_json, str) else source_json
            target = json.loads(target_json) if isinstance(target_json, str) else target_json
        except Exception:
            return '{"error": "Invalid source_json or target_json"}'
        result = compute_golden_record_sync(source, target)
        return json.dumps(result)

    async def submit_merge_for_approval(source_id: str, target_id: str, golden_record_json: str) -> str:
        """Store a merge proposal for human review. source_id: BP ID to be merged (will be deactivated). target_id: surviving BP ID. golden_record_json: JSON of the proposed merged record."""
        import json
        try:
            golden = json.loads(golden_record_json) if isinstance(golden_record_json, str) else golden_record_json
        except Exception:
            return '{"error": "Invalid golden_record_json"}'
        proposal = submit_merge_proposal(source_id, target_id, golden)
        return json.dumps(proposal)

    async def approve_and_execute_merge(proposal_id: str, approver_id: str) -> str:
        """Execute an approved merge. REQUIRES explicit user confirmation before calling. proposal_id: ID from submit_merge_for_approval. approver_id: identity of the approving user."""
        import json
        result = execute_merge_sync(proposal_id, approver_id)
        return json.dumps(result)

    async def generate_harmonization_report() -> str:
        """Generate a report of all completed merges and pending proposals."""
        import json
        report = get_harmonization_report()
        return json.dumps(report)

    return [
        StructuredTool.from_function(coroutine=profile_master_data, name="profile_master_data",
            description="Profile completeness of master data records. entity_type: 'BusinessPartner', 'Customer', or 'Supplier'. records_json: JSON array of records fetched from SAP."),
        StructuredTool.from_function(coroutine=detect_duplicates, name="detect_duplicates",
            description="Detect duplicate pairs in master data records using fuzzy matching. records_json: JSON array of Business Partner records. confidence_threshold: minimum score (default 0.7)."),
        StructuredTool.from_function(coroutine=compute_golden_record, name="compute_golden_record",
            description="Compute a proposed golden record from two duplicate records. source_json and target_json: full Business Partner record JSON objects."),
        StructuredTool.from_function(coroutine=submit_merge_for_approval, name="submit_merge_for_approval",
            description="Store a merge proposal for human review. Returns a proposal_id to use when approving."),
        StructuredTool.from_function(coroutine=approve_and_execute_merge, name="approve_and_execute_merge",
            description="Execute an approved merge. REQUIRES explicit user confirmation before calling."),
        StructuredTool.from_function(coroutine=generate_harmonization_report, name="generate_harmonization_report",
            description="Generate a report of all completed merges and pending proposals."),
    ]


@dataclass
class AgentResponse:
    status: Literal["input_required", "completed", "error"]
    message: str


THREAD_TTL_SECONDS = 3600


class SampleAgent:
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        self.llm = ChatLiteLLM(model=get_model_name(), temperature=get_temperature())
        self._checkpointer = InMemorySaver()
        self._last_active: dict[str, float] = {}
        self._summarization_middleware = SummarizationMiddleware(
            model=self.llm,
            trigger=("tokens", 100_000),
        )
        self._tools: list[BaseTool] | None = None

    def _touch(self, thread_id: str) -> None:
        now = time.monotonic()
        expired = [tid for tid, ts in list(self._last_active.items()) if now - ts > THREAD_TTL_SECONDS]
        for tid in expired:
            self._checkpointer.delete_thread(tid)
            del self._last_active[tid]
            logger.info("Evicted inactive thread: %s", tid)
        self._last_active[thread_id] = now

    async def _get_tools(self) -> list[BaseTool]:
        """Lazily load all tools (MCP + harmonization). Cached after first load."""
        if self._tools is None:
            mcp_tools = await get_mcp_tools()
            local_tools = _build_harmonization_tools()
            self._tools = mcp_tools + local_tools
            logger.info("Loaded %d total tools (%d MCP + %d local)", len(self._tools), len(mcp_tools), len(local_tools))
        return self._tools

    async def _run_agent(self, query: str, context_id: str) -> str:
        """Core agent execution logic — instrumented with OTel spans."""
        tools = await self._get_tools()
        graph = create_agent(
            self.llm,
            tools=tools,
            system_prompt=get_system_prompt(),
            checkpointer=self._checkpointer,
            middleware=[self._summarization_middleware],
        )
        config = {"configurable": {"thread_id": context_id}}
        result = await graph.ainvoke({"messages": [HumanMessage(content=query)]}, config)
        self._touch(context_id)
        return result["messages"][-1].content

    async def stream(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None = None,
    ) -> AsyncGenerator[dict, None]:
        self._touch(context_id)
        yield {
            "is_task_complete": False,
            "require_user_input": False,
            "content": "Processing...",
        }

        try:
            response = await self._run_agent(query, context_id)
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": response,
            }
        except Exception as e:
            logger.exception("Agent stream() failed")
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": f"I encountered an error while processing your request: {str(e)}. Please try again.",
            }

    async def invoke(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None = None,
    ) -> AgentResponse:
        last: dict = {}
        async for chunk in self.stream(query, context_id, tools=tools):
            last = chunk
        if last.get("is_task_complete"):
            return AgentResponse(status="completed", message=last["content"])
        if last.get("require_user_input"):
            return AgentResponse(status="input_required", message=last["content"])
        return AgentResponse(status="error", message=last.get("content", "Unknown error"))
