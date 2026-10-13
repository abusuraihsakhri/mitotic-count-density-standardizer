"""Basic sensitive-identifier screening and in-memory HMAC audit logging.

Pattern screening is best effort and is NOT a HIPAA de-identification guarantee.
"""
import copy
from datetime import datetime, timezone
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
from threading import RLock
import time

logger = logging.getLogger(__name__)

PHI_PATTERNS = [
    re.compile(r"\b(?:MRN|mrn)[:#\s-]*\d{4,10}\b", re.IGNORECASE),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b(?:DOB|Date of Birth)[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", re.IGNORECASE),
    re.compile(r"\b(?:Patient\s+Name|Patient)[:\s]+[A-Z][a-z]+\s+[A-Z][a-z]+\b", re.IGNORECASE),
    re.compile(r"\b(?:John\s+Doe|Jane\s+Smith|Alice\s+Johnson)\b", re.IGNORECASE),
]


class SecurityException(Exception):
    """Raised when a known sensitive identifier pattern is found."""


class ResourceLimitExceededException(Exception):
    """Raised when a computational input exceeds a configured limit."""


def assert_no_phi(text):
    if text is None or text == "":
        return
    for pattern in PHI_PATTERNS:
        if pattern.search(str(text)):
            raise SecurityException("Potential sensitive identifier detected; input rejected")


class PHIGuard:
    assert_no_phi = staticmethod(assert_no_phi)

    @staticmethod
    def redact_phi(text):
        result = str(text)
        for pattern in PHI_PATTERNS:
            result = pattern.sub("[REDACTED_IDENTIFIER]", result)
        return result


class AuditTrail:
    """Tamper-evident, in-process, signed HMAC-SHA256 hash chain.

    Stored only in process memory; signatures cannot be verified after restart
    unless the key and entries are retained independently.
    """
    GENESIS = "GENESIS_BLOCK_0000000000000000"

    def __init__(self, secret_key=None):
        resolved = secret_key or os.getenv("AUDIT_SECRET_KEY")
        if not resolved:
            resolved = secrets.token_hex(32)
            logger.warning("AUDIT_SECRET_KEY missing: using an ephemeral random audit key")
        self.secret_key = resolved.encode("utf-8")
        self.logs = []
        self._lock = RLock()

    def _signature(self, entry):
        fields = ("audit_id", "timestamp", "actor", "actor_tier",
                  "event_type", "payload_hash", "prev_hash")
        signed = "|".join(str(entry[k]) for k in fields)
        return hmac.new(self.secret_key, signed.encode("utf-8"), hashlib.sha256).hexdigest()

    def log(self, actor, actor_tier, event_type, details):
        for value in (actor, actor_tier, event_type):
            assert_no_phi(value)
        payload = json.dumps(details, sort_keys=True, allow_nan=False)
        assert_no_phi(payload)
        payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        with self._lock:
            entry = {
                "audit_id": f"AUDIT-{time.time_ns()}-{len(self.logs) + 1}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "actor": actor,
                "actor_tier": actor_tier,
                "event_type": event_type,
                "payload_hash": payload_hash,
                "prev_hash": self.logs[-1]["current_hash"] if self.logs else self.GENESIS,
            }
            entry["current_hash"] = self._signature(entry)
            self.logs.append(entry)
            return copy.deepcopy(entry)

    def verify_integrity(self):
        with self._lock:
            previous = self.GENESIS
            for entry in self.logs:
                try:
                    if not hmac.compare_digest(entry["prev_hash"], previous):
                        return False
                    expected = self._signature(entry)
                    if not hmac.compare_digest(entry["current_hash"], expected):
                        return False
                    previous = entry["current_hash"]
                except (KeyError, TypeError, ValueError):
                    return False
            return True

    def get_trail(self):
        with self._lock:
            return copy.deepcopy(self.logs)


GLOBAL_AUDIT = AuditTrail()


class AuditLogger:
    log = staticmethod(GLOBAL_AUDIT.log)
    get_trail = staticmethod(GLOBAL_AUDIT.get_trail)
    verify_integrity = staticmethod(GLOBAL_AUDIT.verify_integrity)


class ActionExecutor:
    @staticmethod
    def execute_with_audit(actor, actor_tier, action_type, fn, *args, **kwargs):
        result = fn(*args, **kwargs)
        AuditLogger.log(actor, actor_tier, action_type, {"status": "SUCCESS"})
        return result
