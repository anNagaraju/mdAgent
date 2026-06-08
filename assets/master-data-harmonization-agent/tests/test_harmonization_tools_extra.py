"""Additional coverage tests for harmonization_tools edge cases and utility functions."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from harmonization_tools import (
    _fuzzy_similarity,
    _get_bp_name,
    _compute_pair_confidence,
    _compute_completeness_score,
    reset_state_for_testing,
)


def setup_function():
    reset_state_for_testing()


def test_fuzzy_similarity_identical():
    """Identical strings should return 1.0."""
    assert _fuzzy_similarity("Acme Corporation", "Acme Corporation") == 1.0


def test_fuzzy_similarity_empty():
    """Empty string inputs should return 0.0."""
    assert _fuzzy_similarity("", "Acme") == 0.0
    assert _fuzzy_similarity(None, "Acme") == 0.0
    assert _fuzzy_similarity("Acme", None) == 0.0


def test_fuzzy_similarity_different():
    """Very different strings should have low similarity."""
    score = _fuzzy_similarity("Acme Corporation", "Global Supplies GmbH")
    assert score < 0.5


def test_get_bp_name_from_full_name():
    """Should return BusinessPartnerFullName when available."""
    record = {"BusinessPartnerFullName": "Acme Corp", "OrganizationBPName1": "Other"}
    assert _get_bp_name(record) == "Acme Corp"


def test_get_bp_name_from_org_name():
    """Should fall back to OrganizationBPName1 when FullName is absent."""
    record = {"OrganizationBPName1": "Acme Org"}
    assert _get_bp_name(record) == "Acme Org"


def test_get_bp_name_from_person_name():
    """Should compose first + last name for person records."""
    record = {"FirstName": "John", "LastName": "Doe"}
    assert "John" in _get_bp_name(record) and "Doe" in _get_bp_name(record)


def test_get_bp_name_empty():
    """Should return empty string when no name fields are present."""
    assert _get_bp_name({}) == ""


def test_compute_pair_confidence_identical_names():
    """Identical names should yield high confidence."""
    rec_a = {"BusinessPartner": "A", "BusinessPartnerFullName": "Acme Corporation", "SearchTerm1": "ACME"}
    rec_b = {"BusinessPartner": "B", "BusinessPartnerFullName": "Acme Corporation", "SearchTerm1": "ACME"}
    confidence, reasons = _compute_pair_confidence(rec_a, rec_b)
    assert confidence >= 0.7
    assert len(reasons) > 0


def test_compute_pair_confidence_same_tax_id():
    """Same tax ID should boost confidence."""
    rec_a = {"BusinessPartner": "A", "BusinessPartnerFullName": "Company A", "TaxNumber1": "DE123456789"}
    rec_b = {"BusinessPartner": "B", "BusinessPartnerFullName": "Company B", "TaxNumber1": "DE123456789"}
    confidence, reasons = _compute_pair_confidence(rec_a, rec_b)
    # Tax ID match adds 0.3
    assert confidence >= 0.3
    tax_reasons = [r for r in reasons if "tax" in r.lower()]
    assert len(tax_reasons) > 0


def test_compute_completeness_score_all_filled():
    """Fully populated record should score 1.0."""
    record = {f: "value_{f}" for f in ["a", "b", "c"]}
    score = _compute_completeness_score(record, ["a", "b", "c"])
    assert score == 1.0


def test_compute_completeness_score_all_null():
    """Record with all null values should score 0.0."""
    record = {"a": None, "b": None, "c": None}
    score = _compute_completeness_score(record, ["a", "b", "c"])
    assert score == 0.0


def test_compute_completeness_score_empty_fields():
    """Empty fields list should return 0.0."""
    score = _compute_completeness_score({"a": "value"}, [])
    assert score == 0.0
