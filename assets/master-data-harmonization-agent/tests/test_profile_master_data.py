"""Unit tests for profile_master_data_sync."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from harmonization_tools import profile_master_data_sync


def test_profile_master_data_basic():
    """Profile returns completeness score between 0 and 1 for valid records."""
    records = [
        {
            "BusinessPartner": "1000001",
            "BusinessPartnerFullName": "Acme Corp",
            "BusinessPartnerName": "Acme Corp",
            "OrganizationBPName1": "Acme Corp",
            "SearchTerm1": "ACME",
            "BusinessPartnerCategory": "2",
            "CreationDate": "2021-01-01",
            "LastChangeDate": "2025-01-01",
        },
        {
            "BusinessPartner": "1000002",
            "BusinessPartnerFullName": None,
            "BusinessPartnerName": "Partial Corp",
        },
    ]
    result = profile_master_data_sync(records, "BusinessPartner")

    assert result["entity_type"] == "BusinessPartner"
    assert result["total_records"] == 2
    assert 0.0 <= result["completeness_score"] <= 1.0
    assert isinstance(result["field_scores"], dict)
    assert "BusinessPartner" in result["field_scores"]


def test_profile_master_data_empty_records():
    """Profile returns zeroed result for empty records list."""
    result = profile_master_data_sync([], "BusinessPartner")
    assert result["total_records"] == 0
    assert result["completeness_score"] == 0.0


def test_profile_master_data_fully_complete():
    """Completeness score is high for fully populated records."""
    records = [
        {
            "BusinessPartner": "1000001",
            "BusinessPartnerFullName": "Full Corp",
            "BusinessPartnerName": "Full Corp",
            "OrganizationBPName1": "Full Corp",
            "FirstName": None,
            "LastName": None,
            "SearchTerm1": "FULL",
            "BusinessPartnerCategory": "2",
            "CreationDate": "2021-01-01",
            "LastChangeDate": "2025-01-01",
        }
    ]
    result = profile_master_data_sync(records, "BusinessPartner")
    assert result["completeness_score"] > 0.5
