"""Unit tests for submit_merge_proposal."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from harmonization_tools import submit_merge_proposal, reset_state_for_testing


def setup_function():
    reset_state_for_testing()


def test_submit_merge_returns_proposal():
    """submit_merge_proposal returns a proposal with pending_approval status."""
    golden = {"BusinessPartner": "1000001", "BusinessPartnerFullName": "Acme Corporation"}
    proposal = submit_merge_proposal("1000002", "1000001", golden)

    assert proposal["status"] == "pending_approval"
    assert "proposal_id" in proposal
    assert proposal["proposal_id"].startswith("PROP-")
    assert proposal["source_id"] == "1000002"
    assert proposal["target_id"] == "1000001"
    assert "created_at" in proposal


def test_submit_merge_stores_golden_record():
    """submit_merge_proposal stores the golden record in the proposal."""
    golden = {"BusinessPartner": "1000001", "BusinessPartnerFullName": "Acme Corporation"}
    proposal = submit_merge_proposal("1000002", "1000001", golden)
    assert proposal["golden_record"] == golden


def test_submit_multiple_proposals_have_unique_ids():
    """Multiple proposals should have distinct IDs."""
    golden = {"BusinessPartner": "1000001"}
    p1 = submit_merge_proposal("1000002", "1000001", golden)
    p2 = submit_merge_proposal("1000003", "1000001", golden)
    assert p1["proposal_id"] != p2["proposal_id"]
