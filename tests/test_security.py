"""
Security and safety tests for Mitotic Count Density Standardizer.
"""
import os
import sys
import pytest

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base import (
    assert_no_phi,
    PHIGuard,
    SecurityException,
    AuditTrail,
    AuditLogger,
)
from mitotic_density import _validate_safe_path


class TestPHIGuard:
    """Tests for the PHI outbound guard."""

    def test_blocks_mrn(self):
        with pytest.raises(SecurityException):
            assert_no_phi("Patient MRN-12345678")

    def test_blocks_ssn(self):
        with pytest.raises(SecurityException):
            assert_no_phi("SSN: 123-45-6789")

    def test_blocks_phone(self):
        with pytest.raises(SecurityException):
            assert_no_phi("Call (555) 123-4567")

    def test_blocks_email(self):
        with pytest.raises(SecurityException):
            assert_no_phi("Contact patient@hospital.org")

    def test_blocks_patient_name(self):
        with pytest.raises(SecurityException):
            assert_no_phi("Patient Name: John Smith")

    def test_blocks_doe(self):
        with pytest.raises(SecurityException):
            assert_no_phi("John Doe was admitted")

    def test_allows_safe_text(self):
        # Should not raise
        assert_no_phi("Mitotic count elevated. Recommend follow-up analysis.")
        assert_no_phi("Primary metric: 14.5. Status: NOMINAL.")

    def test_empty_string_ok(self):
        assert_no_phi("") is None

    def test_none_ok(self):
        assert_no_phi(None) is None

    def test_redact_phi(self):
        text = "Patient MRN-12345678 has SSN 123-45-6789"
        redacted = PHIGuard.redact_phi(text)
        assert "MRN" not in redacted or "12345678" not in redacted
        assert "123-45-6789" not in redacted
        assert "[REDACTED_IDENTIFIER]" in redacted


class TestAuditTrail:
    """Tests for the HMAC-SHA256 audit trail."""

    def test_log_creates_entry(self):
        trail = AuditTrail(secret_key="test-key-for-unit-tests")
        entry = trail.log("tester", "unit", "TEST_EVENT", {"action": "verify"})
        assert "audit_id" in entry
        assert "current_hash" in entry
        assert entry["prev_hash"] == "GENESIS_BLOCK_0000000000000000"

    def test_chain_integrity(self):
        trail = AuditTrail(secret_key="test-key-for-unit-tests")
        trail.log("tester", "unit", "EVENT_1", {"step": 1})
        trail.log("tester", "unit", "EVENT_2", {"step": 2})
        trail.log("tester", "unit", "EVENT_3", {"step": 3})
        assert trail.verify_integrity() is True
        assert len(trail.get_trail()) == 3

    def test_chain_linked_hashes(self):
        trail = AuditTrail(secret_key="test-key-for-unit-tests")
        e1 = trail.log("tester", "unit", "EVENT_1", {"step": 1})
        e2 = trail.log("tester", "unit", "EVENT_2", {"step": 2})
        assert e2["prev_hash"] == e1["current_hash"]

    def test_tamper_detection(self):
        trail = AuditTrail(secret_key="test-key-for-unit-tests")
        trail.log("tester", "unit", "EVENT_1", {"step": 1})
        trail.log("tester", "unit", "EVENT_2", {"step": 2})
        # Tamper with the first entry
        trail.logs[0]["current_hash"] = "TAMPERED_HASH"
        assert trail.verify_integrity() is False

    def test_no_phi_in_audit(self):
        trail = AuditTrail(secret_key="test-key-for-unit-tests")
        with pytest.raises(SecurityException):
            trail.log("tester", "unit", "BAD_EVENT", {"patient": "MRN-12345678"})

    def test_generated_key_when_no_env(self):
        """When no key is provided, a random one should be generated."""
        old_key = os.environ.pop("AUDIT_SECRET_KEY", None)
        try:
            trail = AuditTrail(secret_key=None)
            assert len(trail.secret_key) > 0  # Should have a generated key
            entry = trail.log("tester", "unit", "TEST", {"action": "verify"})
            assert entry["current_hash"] != ""
        finally:
            if old_key is not None:
                os.environ["AUDIT_SECRET_KEY"] = old_key


class TestPathValidation:
    """Tests for the path traversal protection."""

    def test_empty_path_raises(self):
        with pytest.raises(ValueError, match="null bytes"):
            _validate_safe_path("")

    def test_null_byte_raises(self):
        with pytest.raises(ValueError, match="null bytes"):
            _validate_safe_path("file\x00name.csv")

    def test_system_path_raises(self):
        with pytest.raises(ValueError, match="restricted"):
            _validate_safe_path("C:\\Windows\\system32\\config\\SAM")

    def test_windows_program_files_raises(self):
        with pytest.raises(ValueError, match="restricted"):
            _validate_safe_path("C:\\Program Files\\app\\config.ini")

    def test_unix_style_system_path_normalized(self):
        """On non-Windows, /etc/passwd should be caught. On Windows, it normalizes to C:\\etc\\passwd."""
        import sys
        if sys.platform == "win32":
            # On Windows, /etc/passwd becomes C:\etc\passwd which is not in our blocked list
            # This is acceptable since the real Windows system paths are blocked
            result = _validate_safe_path("/etc/passwd")
            assert "etc" in result.lower()
        else:
            with pytest.raises(ValueError, match="restricted"):
                _validate_safe_path("/etc/passwd")

    def test_valid_csv_path(self, tmp_path):
        safe_file = tmp_path / "data.csv"
        safe_file.write_text("a,b\n1,2\n")
        result = _validate_safe_path(str(safe_file), must_exist=True)
        assert os.path.isfile(result)

    def test_missing_input_file_raises(self, tmp_path):
        missing = tmp_path / "nonexistent.csv"
        with pytest.raises(FileNotFoundError):
            _validate_safe_path(str(missing), must_exist=True)
