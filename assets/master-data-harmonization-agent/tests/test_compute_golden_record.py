"""Unit tests for compute_golden_record_sync."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from harmonization_tools import compute_golden_record_sync


SOURCE = {
    "BusinessPartner": "1000001",
    "BusinessPartnerFullName": "Acme Corporation",
    "OrganizationBPName1": "Acme Corporation",
    "SearchTerm1": "ACME",
    "LastChangeDate": "2025-01-01",
    "CreationDate": "2021-01-01",
}

TARGET = {
    "BusinessPartner": "1000002",
    "BusinessPartnerFullName": "Acme Corp.",
    "OrganizationBPName1": "Acme Corp.",
    "SearchTerm1": None,
    "LastChangeDate": "2024-06-01",
    "CreationDate": "2022-01-01",
}


def test_compute_golden_record_returns_structure():
    """Result must contain proposed_golden_record, source, target, and conflicts."""
    result = compute_golden_record_sync(SOURCE, TARGET)
    assert "proposed_golden_record" in result
    assert "source_record" in result
    assert "target_record" in result
    assert "conflicts" in result
    assert "conflict_count" in result


def test_compute_golden_record_prefers_filled_field():
    """SearchTerm1 is filled in source and null in target — should pick source value."""
    result = compute_golden_record_sync(SOURCE, TARGET)
    golden = result["proposed_golden_record"]
    assert golden.get("SearchTerm1") == "ACME"


def test_compute_golden_record_conflict_list():
    """Conflicts should be populated when both records have differing non-null values."""
    result = compute_golden_record_sync(SOURCE, TARGET)
    conflict_fields = [c["field"] for c in result["conflicts"]]
    # BusinessPartnerFullName differs between records
    assert "BusinessPartnerFullName" in conflict_fields or "OrganizationBPName1" in conflict_fields


def test_compute_golden_record_identical_values():
    """Fields with identical values should NOT appear in conflicts."""
    identical_source = {"BusinessPartner": "1000001", "SearchTerm1": "ACME"}
    identical_target = {"BusinessPartner": "1000001", "SearchTerm1": "ACME"}
    result = compute_golden_record_sync(identical_source, identical_target)
    assert result["conflict_count"] == 0
