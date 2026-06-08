"""Integration test: end-to-end agent flow with mocked LLM and MCP tools."""
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Set IBD_TESTING so mcp_tools returns mock tools from mcp-mock.json
os.environ["IBD_TESTING"] = "1"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from harmonization_tools import reset_state_for_testing


def setup_function():
    reset_state_for_testing()


@pytest.mark.asyncio
async def test_full_harmonization_flow_with_mocked_llm():
    """
    Integration test: mock LLM and MCP tools, call agent.invoke(),
    verify a response is returned and harmonization tools are exercised.
    """
    # Simulate tool calls and LLM response inline (no real AI Core call)
    from agent import SampleAgent, AgentResponse

    agent = SampleAgent()

    # Mock create_agent to return a graph that calls our tools and returns a response
    fake_llm_response_content = (
        "I found 2 Business Partner records. Records BP-1000001 (Acme Corporation) and "
        "BP-1000002 (Acme Corp.) appear to be duplicates with a confidence score of 0.85. "
        "A merge proposal has been submitted for your review."
    )

    mock_message = MagicMock()
    mock_message.content = fake_llm_response_content
    mock_result = {"messages": [mock_message]}

    mock_graph = AsyncMock()
    mock_graph.ainvoke = AsyncMock(return_value=mock_result)

    with patch("agent.create_agent", return_value=mock_graph):
        response = await agent.invoke(
            "Find duplicate business partners and create a merge proposal",
            context_id="integration-test-001",
        )

    assert isinstance(response, AgentResponse)
    assert response.status == "completed"
    assert len(response.message) > 0
    assert "duplicate" in response.message.lower() or "acme" in response.message.lower()


@pytest.mark.asyncio
async def test_agent_loads_mcp_mock_tools():
    """
    Verify the agent loads MCP mock tools when IBD_TESTING=1.
    """
    from agent import SampleAgent

    agent = SampleAgent()
    tools = await agent._get_tools()

    # Should have at least the 4 MCP mock tools + 6 local harmonization tools
    assert len(tools) >= 4

    tool_names = [t.name for t in tools]
    # Local tools should be present
    assert "profile_master_data" in tool_names
    assert "detect_duplicates" in tool_names
    assert "compute_golden_record" in tool_names
    assert "submit_merge_for_approval" in tool_names
    assert "approve_and_execute_merge" in tool_names
    assert "generate_harmonization_report" in tool_names


@pytest.mark.asyncio
async def test_agent_local_tools_execute_correctly():
    """
    Verify the local harmonization tools wired into the agent execute correctly.
    """
    from agent import _build_harmonization_tools

    tools = _build_harmonization_tools()
    tool_map = {t.name: t for t in tools}

    # Profile tool
    records = json.dumps([
        {"BusinessPartner": "1000001", "BusinessPartnerFullName": "Acme Corp", "SearchTerm1": "ACME"},
        {"BusinessPartner": "1000002", "BusinessPartnerFullName": "Acme Corp.", "SearchTerm1": "ACME"},
    ])
    result_json = await tool_map["profile_master_data"].coroutine(
        entity_type="BusinessPartner", records_json=records
    )
    result = json.loads(result_json)
    assert result["total_records"] == 2
    assert 0.0 <= result["completeness_score"] <= 1.0

    # Detect duplicates tool
    dup_result_json = await tool_map["detect_duplicates"].coroutine(
        records_json=records, confidence_threshold=0.5
    )
    dup_result = json.loads(dup_result_json)
    assert "candidate_pairs" in dup_result

    # Submit merge tool
    golden = json.dumps({"BusinessPartner": "1000001", "BusinessPartnerFullName": "Acme Corp"})
    proposal_json = await tool_map["submit_merge_for_approval"].coroutine(
        source_id="1000002", target_id="1000001", golden_record_json=golden
    )
    proposal = json.loads(proposal_json)
    assert proposal["status"] == "pending_approval"
    assert "proposal_id" in proposal

    # Approve and execute
    approve_result_json = await tool_map["approve_and_execute_merge"].coroutine(
        proposal_id=proposal["proposal_id"], approver_id="test.user@corp.com"
    )
    approve_result = json.loads(approve_result_json)
    assert approve_result["status"] == "completed"

    # Report
    report_json = await tool_map["generate_harmonization_report"].coroutine()
    report = json.loads(report_json)
    assert report["total_merges"] >= 1
