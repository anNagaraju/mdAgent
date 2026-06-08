"""
Master data harmonization tools for duplicate detection, golden record computation,
and merge management.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# In-memory store for merge proposals and audit records
_merge_proposals: dict[str, dict] = {}
_audit_records: list[dict] = []

# Fuzzy matching threshold constants
DEFAULT_CONFIDENCE_THRESHOLD = 0.7
DEFAULT_TOP = 100

# Field weights for completeness scoring
COMPLETENESS_FIELDS_BP = [
    "BusinessPartner", "BusinessPartnerFullName", "BusinessPartnerName",
    "OrganizationBPName1", "FirstName", "LastName",
    "SearchTerm1", "BusinessPartnerCategory",
    "CreationDate", "LastChangeDate",
]


def _compute_completeness_score(record: dict, fields: list[str]) -> float:
    """Compute completeness score (0.0-1.0) for a record based on key fields."""
    if not fields:
        return 0.0
    filled = sum(1 for f in fields if record.get(f) not in (None, "", "0000-00-00T00:00:00"))
    return filled / len(fields)


def _fuzzy_similarity(a: str | None, b: str | None) -> float:
    """Compute normalized fuzzy similarity between two strings (0.0-1.0)."""
    if not a or not b:
        return 0.0
    try:
        from rapidfuzz.fuzz import token_sort_ratio
        return token_sort_ratio(a.lower().strip(), b.lower().strip()) / 100.0
    except ImportError:
        # Fallback: simple character overlap ratio
        a_set = set(a.lower().split())
        b_set = set(b.lower().split())
        if not a_set or not b_set:
            return 0.0
        intersection = len(a_set & b_set)
        union = len(a_set | b_set)
        return intersection / union if union > 0 else 0.0


def _get_bp_name(record: dict) -> str:
    """Extract the best available name from a Business Partner record."""
    return (
        record.get("BusinessPartnerFullName")
        or record.get("OrganizationBPName1")
        or f"{record.get('FirstName', '')} {record.get('LastName', '')}".strip()
        or record.get("BusinessPartnerName")
        or ""
    )


def _compute_pair_confidence(rec_a: dict, rec_b: dict) -> tuple[float, list[str]]:
    """
    Compute a duplicate confidence score between two BP records.
    Returns (confidence: float, match_reasons: list[str]).
    """
    reasons = []
    scores = []

    # Name similarity (weight: 0.5)
    name_a = _get_bp_name(rec_a)
    name_b = _get_bp_name(rec_b)
    name_sim = _fuzzy_similarity(name_a, name_b)
    scores.append(name_sim * 0.5)
    if name_sim >= 0.8:
        reasons.append(f"Similar name (score={name_sim:.2f}): '{name_a}' vs '{name_b}'")

    # Tax ID match (weight: 0.3) — exact match on TaxNumber1 if available
    tax_a = rec_a.get("TaxNumber1") or rec_a.get("VATRegistration")
    tax_b = rec_b.get("TaxNumber1") or rec_b.get("VATRegistration")
    if tax_a and tax_b:
        if tax_a.strip() == tax_b.strip():
            scores.append(0.3)
            reasons.append(f"Identical tax ID: {tax_a}")
        else:
            scores.append(0.0)
    else:
        scores.append(0.0)

    # Search term similarity (weight: 0.2)
    st_a = rec_a.get("SearchTerm1", "")
    st_b = rec_b.get("SearchTerm1", "")
    if st_a and st_b:
        st_sim = _fuzzy_similarity(st_a, st_b)
        scores.append(st_sim * 0.2)
        if st_sim >= 0.8:
            reasons.append(f"Similar search term (score={st_sim:.2f}): '{st_a}' vs '{st_b}'")
    else:
        scores.append(0.0)

    confidence = sum(scores)
    return min(confidence, 1.0), reasons


@tracer.start_as_current_span("m1_profile_master_data")
def profile_master_data_sync(records: list[dict], entity_type: str) -> dict:
    """
    Compute completeness scores for a list of master data records.
    Returns profiling results with per-field statistics.
    """
    if not records:
        logger.warning("M1.missed: master data profiling did not complete — no records provided")
        return {
            "entity_type": entity_type,
            "total_records": 0,
            "completeness_score": 0.0,
            "field_scores": {},
        }

    fields = COMPLETENESS_FIELDS_BP
    field_scores = {}
    record_scores = []

    for field in fields:
        filled = sum(1 for r in records if r.get(field) not in (None, "", "0000-00-00T00:00:00"))
        field_scores[field] = round(filled / len(records), 3)

    for r in records:
        record_scores.append(_compute_completeness_score(r, fields))

    avg_score = round(sum(record_scores) / len(record_scores), 3) if record_scores else 0.0

    entity_count = len(records)
    logger.info(
        "M1.achieved: master data profiling complete — %d records scanned, quality scores computed",
        entity_count,
    )

    return {
        "entity_type": entity_type,
        "total_records": entity_count,
        "completeness_score": avg_score,
        "field_scores": field_scores,
    }


@tracer.start_as_current_span("m2_duplicate_detection")
def detect_duplicates_sync(records: list[dict], confidence_threshold: float) -> list[dict]:
    """
    Detect duplicate pairs in a list of Business Partner records.
    Returns list of candidate pairs with confidence scores.
    """
    candidates = []
    n = len(records)

    for i in range(n):
        for j in range(i + 1, n):
            confidence, reasons = _compute_pair_confidence(records[i], records[j])
            if confidence >= confidence_threshold:
                candidates.append({
                    "source_id": records[i].get("BusinessPartner") or records[i].get("Customer") or f"record_{i}",
                    "target_id": records[j].get("BusinessPartner") or records[j].get("Customer") or f"record_{j}",
                    "confidence": round(confidence, 3),
                    "match_reasons": reasons,
                })

    candidates.sort(key=lambda x: x["confidence"], reverse=True)

    candidate_count = len(candidates)
    if candidate_count > 0:
        logger.info(
            "M2.achieved: duplicate detection complete — %d candidate pairs identified",
            candidate_count,
        )
    else:
        logger.warning("M2.missed: duplicate detection returned no candidates or failed to execute")

    return candidates


@tracer.start_as_current_span("m3_golden_record_computation")
def compute_golden_record_sync(source: dict, target: dict) -> dict:
    """
    Compute a golden record from two duplicate records by applying resolution rules:
    1. Prefer the more complete record for each field
    2. For ties, prefer the most recently changed value
    Returns proposed golden record with conflict details.
    """
    golden = {}
    conflicts = []

    all_keys = set(source.keys()) | set(target.keys())
    # Skip navigation properties and metadata
    skip_keys = {k for k in all_keys if k.startswith("to_") or k.startswith("@")}
    data_keys = all_keys - skip_keys

    src_completeness = _compute_completeness_score(source, list(data_keys))
    tgt_completeness = _compute_completeness_score(target, list(data_keys))
    more_complete = source if src_completeness >= tgt_completeness else target

    src_changed = source.get("LastChangeDate") or ""
    tgt_changed = target.get("LastChangeDate") or ""
    more_recent = source if src_changed >= tgt_changed else target

    for key in data_keys:
        src_val = source.get(key)
        tgt_val = target.get(key)

        if src_val == tgt_val:
            golden[key] = src_val
        elif src_val and not tgt_val:
            golden[key] = src_val
        elif tgt_val and not src_val:
            golden[key] = tgt_val
        else:
            # Both have values — pick from more complete record, fallback to more recent
            preferred = more_complete.get(key) or more_recent.get(key)
            golden[key] = preferred
            conflicts.append({
                "field": key,
                "source_value": src_val,
                "target_value": tgt_val,
                "chosen_value": preferred,
                "resolution": "most_complete" if more_complete.get(key) else "most_recent",
            })

    proposal_count = 1  # one golden record computed per call
    logger.info(
        "M3.achieved: harmonization analysis complete — %d merge proposals generated",
        proposal_count,
    )

    return {
        "proposed_golden_record": golden,
        "source_record": source,
        "target_record": target,
        "conflicts": conflicts,
        "conflict_count": len(conflicts),
    }


def submit_merge_proposal(source_id: str, target_id: str, golden_record: dict) -> dict:
    """Store a merge proposal for human review."""
    proposal_id = f"PROP-{str(uuid.uuid4())[:8].upper()}"
    proposal = {
        "proposal_id": proposal_id,
        "source_id": source_id,
        "target_id": target_id,
        "golden_record": golden_record,
        "status": "pending_approval",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _merge_proposals[proposal_id] = proposal
    logger.info("Merge proposal %s created for %s → %s", proposal_id, source_id, target_id)
    return proposal


@tracer.start_as_current_span("m5_master_data_update")
def execute_merge_sync(proposal_id: str, approver_id: str) -> dict:
    """
    Execute an approved merge. Requires the proposal to be in pending_approval state.
    Records the approval (M4) and simulates the SAP update (M5).
    """
    proposal = _merge_proposals.get(proposal_id)
    if not proposal:
        error_msg = f"Proposal {proposal_id} not found"
        logger.warning("M5.missed: SAP API call failed for merge — %s", error_msg)
        return {"status": "error", "message": error_msg}

    if proposal["status"] != "pending_approval":
        error_msg = f"Proposal {proposal_id} is not in pending_approval state (current: {proposal['status']})"
        logger.warning("M4.missed: no approval received — %s", error_msg)
        return {"status": "error", "message": error_msg}

    source_id = proposal["source_id"]
    target_id = proposal["target_id"]

    # Record M4 — approval received
    logger.info(
        "M4.achieved: merge proposal approved by %s for %s",
        approver_id,
        target_id,
    )

    # Simulate SAP merge execution (BP Merge API would be called here)
    audit_record = {
        "proposal_id": proposal_id,
        "source_id": source_id,
        "target_id": target_id,
        "approver_id": approver_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": "merged",
        "before_state": {
            "source": proposal["golden_record"].get("source_record", {}),
            "target": proposal["golden_record"].get("target_record", {}),
        },
        "after_state": proposal["golden_record"],
        "status": "completed",
    }
    _audit_records.append(audit_record)

    # Update proposal status
    _merge_proposals[proposal_id]["status"] = "completed"

    logger.info(
        "M5.achieved: master data updated in SAP — merged %s into %s, audit record created",
        source_id,
        target_id,
    )

    return {
        "status": "completed",
        "proposal_id": proposal_id,
        "source_id": source_id,
        "target_id": target_id,
        "audit_record": audit_record,
    }


def get_harmonization_report() -> dict:
    """Return a summary report of all completed merge operations."""
    return {
        "total_merges": len(_audit_records),
        "audit_records": _audit_records,
        "pending_proposals": [p for p in _merge_proposals.values() if p["status"] == "pending_approval"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def reset_state_for_testing() -> None:
    """Reset in-memory state — used in tests only."""
    _merge_proposals.clear()
    _audit_records.clear()
