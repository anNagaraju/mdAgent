"""Unit tests for get_harmonization_report."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from harmonization_tools import (
    submit_merge_proposal,
    execute_merge_sync,
    get_harmonization_report,
    reset_state_for_testing,
)


def setup_function():
    reset_state_for_testing()


def test_report_is_empty_when_no_merges():
    """Report should show zero merges when nothing has been processed."""
    report = get_harmonization_report()
    assert report["total_merges"] == 0
    assert report["audit_records"] == []
    assert "generated_at" in report


def test_report_shows_completed_merges():
    """After executing a merge, report should contain at least one audit record."""
    golden = {"BusinessPartner": "1000001", "BusinessPartnerFullName": "Acme Corporation"}
    proposal = submit_merge_proposal("1000002", "1000001", golden)
    execute_merge_sync(proposal["proposal_id"], "steward@corp.com")

    report = get_harmonization_report()
    assert report["total_merges"] >= 1
    assert len(report["audit_records"]) >= 1


def test_report_shows_pending_proposals():
    """Unexecuted proposals should appear in pending_proposals."""
    golden = {"BusinessPartner": "1000001"}
    submit_merge_proposal("1000002", "1000001", golden)

    report = get_harmonization_report()
    assert len(report["pending_proposals"]) >= 1
    assert report["pending_proposals"][0]["status"] == "pending_approval"


def test_report_audit_record_contains_required_fields():
    """Audit records in the report should have all required fields."""
    golden = {"BusinessPartner": "1000001"}
    proposal = submit_merge_proposal("1000002", "1000001", golden)
    execute_merge_sync(proposal["proposal_id"], "approver@corp.com")

    report = get_harmonization_report()
    audit = report["audit_records"][0]
    for field in ["proposal_id", "source_id", "target_id", "approver_id", "timestamp", "action"]:
        assert field in audit
