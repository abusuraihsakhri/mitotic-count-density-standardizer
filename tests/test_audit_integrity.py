"""Additional checks for cryptographic audit verification and API density."""
import pytest
from agents.base import AuditTrail
from mitotic_density import calculate_metrics


def test_last_block_signature_tampering_is_detected():
    trail = AuditTrail(secret_key="known-test-key")
    trail.log("worker", "unit", "EVALUATION", {"mitoses": 7})
    assert trail.verify_integrity()
    trail.logs[0]["current_hash"] = "0" * 64
    assert not trail.verify_integrity()


def test_non_hash_field_tampering_is_detected():
    trail = AuditTrail(secret_key="known-test-key")
    trail.log("worker", "unit", "EVALUATION", {"mitoses": 7})
    trail.logs[0]["event_type"] = "MODIFIED"
    assert not trail.verify_integrity()


def test_returned_audit_entries_are_defensive_copies():
    trail = AuditTrail(secret_key="known-test-key")
    trail.log("worker", "unit", "EVALUATION", {"mitoses": 7})
    exported = trail.get_trail()
    exported[0]["current_hash"] = "invalid"
    assert trail.verify_integrity()


def test_no_unjustified_grading_thresholds():
    result = calculate_metrics(100, measured_area_mm2=1)
    assert result["mitoses_per_mm2"] == 100
    assert result["classification"].startswith("Not assigned")
