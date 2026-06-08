"""Unit tests for execute_merge_sync."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from harmonization_tools import submit_merge_proposal, execute_merge_sync, reset_state_for_testing


def setup_function():
    reset_state_for_testing()


def test_approve_merge_completes_successfully():
    """Approving a pending proposal returns completed status with audit record."""
    golden = {"BusinessPartner": "1000001", "BusinessPartnerFullName": "Acme Corporation"}
    proposal = submit_merge_proposal("1000002", "1000001", golden)

    result = execute_merge_sync(proposal["proposal_id"], "data.steward@corp.com")

    assert result["status"] == "completed"
    assert result["proposal_id"] == proposal["proposal_id"]
    assert result["source_id"] == "1000002"
    assert result["target_id"] == "1000001"
    assert "audit_record" in result


def test_approve_merge_audit_record_structure():
    """Audit record should contain required fields."""
    golden = {"BusinessPartner": "1000001"}
    proposal = submit_merge_proposal("1000002", "1000001", golden)
    result = execute_merge_sync(proposal["proposal_id"], "approver@corp.com")

    audit = result["audit_record"]
    assert audit["approver_id"] == "approver@corp.com"
    assert audit["action"] == "merged"
    assert "timestamp" in audit


def test_approve_nonexistent_proposal_returns_error():
    """Approving a non-existent proposal ID returns an error."""
    result = execute_merge_sync("PROP-NONEXISTENT", "approver@corp.com")
    assert result["status"] == "error"
    assert "not found" in result["message"].lower()


def test_approve_already_completed_proposal_returns_error():
    """Cannot approve a proposal that was already completed."""
    golden = {"BusinessPartner": "1000001"}
    proposal = submit_merge_proposal("1000002", "1000001", golden)
    execute_merge_sync(proposal["proposal_id"], "approver1@corp.com")

    result = execute_merge_sync(proposal["proposal_id"], "approver2@corp.com")
    assert result["status"] == "error"
