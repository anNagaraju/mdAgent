"""Unit tests for detect_duplicates_sync."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from harmonization_tools import detect_duplicates_sync


RECORD_A = {
    "BusinessPartner": "1000001",
    "BusinessPartnerFullName": "Acme Corporation",
    "OrganizationBPName1": "Acme Corporation",
    "SearchTerm1": "ACME",
}

RECORD_B = {
    "BusinessPartner": "1000002",
    "BusinessPartnerFullName": "Acme Corp.",
    "OrganizationBPName1": "Acme Corp.",
    "SearchTerm1": "ACME",
}

RECORD_C = {
    "BusinessPartner": "1000003",
    "BusinessPartnerFullName": "Totally Different Company",
    "OrganizationBPName1": "Totally Different Company",
    "SearchTerm1": "DIFF",
}


def test_detect_duplicates_finds_similar_names():
    """Should detect Acme Corporation vs Acme Corp. as duplicates."""
    candidates = detect_duplicates_sync([RECORD_A, RECORD_B, RECORD_C], confidence_threshold=0.5)
    assert len(candidates) >= 1
    pair_ids = {(c["source_id"], c["target_id"]) for c in candidates}
    assert ("1000001", "1000002") in pair_ids or ("1000002", "1000001") in pair_ids


def test_detect_duplicates_confidence_scores_in_range():
    """Confidence scores must be between 0 and 1."""
    candidates = detect_duplicates_sync([RECORD_A, RECORD_B], confidence_threshold=0.0)
    for c in candidates:
        assert 0.0 <= c["confidence"] <= 1.0


def test_detect_duplicates_threshold_filters_low_confidence():
    """High threshold should filter out low-confidence pairs."""
    candidates = detect_duplicates_sync([RECORD_A, RECORD_C], confidence_threshold=0.95)
    assert len(candidates) == 0


def test_detect_duplicates_empty_records():
    """Empty input returns empty list."""
    result = detect_duplicates_sync([], confidence_threshold=0.7)
    assert result == []


def test_detect_duplicates_single_record():
    """Single record can't form a pair."""
    result = detect_duplicates_sync([RECORD_A], confidence_threshold=0.7)
    assert result == []


def test_detect_duplicates_sorted_by_confidence():
    """Results should be sorted descending by confidence."""
    candidates = detect_duplicates_sync([RECORD_A, RECORD_B, RECORD_C], confidence_threshold=0.0)
    if len(candidates) >= 2:
        for i in range(len(candidates) - 1):
            assert candidates[i]["confidence"] >= candidates[i + 1]["confidence"]
