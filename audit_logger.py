"""
audit_logger.py
----------------
Records all contract lifecycle events to an immutable audit trail.
Tracks who did what, when, and on which contract — for compliance
and dispute resolution purposes.
"""

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

log = logging.getLogger(__name__)


class AuditAction(Enum):
    CREATED       = "created"
    VIEWED        = "viewed"
    MODIFIED      = "modified"
    APPROVED      = "approved"
    REJECTED      = "rejected"
    SIGNED        = "signed"
    EXPIRED       = "expired"
    RENEWED       = "renewed"
    TERMINATED    = "terminated"
    NOTIFICATION  = "notification_sent"


@dataclass
class AuditEntry:
    event_id: str
    contract_id: str
    action: AuditAction
    performed_by: str
    timestamp: datetime
    details: Optional[dict] = None
    ip_address: Optional[str] = None


@dataclass
class AuditLog:
    contract_id: str
    entries: list[AuditEntry]

    def latest(self) -> Optional[AuditEntry]:
        """Return the most recent audit entry, or None if the log is empty."""
        return self.entries[-1] if self.entries else None

    def by_action(self, action: AuditAction) -> list[AuditEntry]:
        """Return all entries matching a specific action type."""
        return [e for e in self.entries if e.action == action]

    def by_user(self, user: str) -> list[AuditEntry]:
        """Return all entries performed by a specific user."""
        return [e for e in self.entries if e.performed_by == user]


# ── Storage backend (file-based stub) ─────────────────────────────────────────

AUDIT_DIR = os.environ.get("AUDIT_LOG_DIR", "./audit_logs")


def _ensure_audit_dir() -> None:
    os.makedirs(AUDIT_DIR, exist_ok=True)


def _log_path(contract_id: str) -> str:
    return os.path.join(AUDIT_DIR, f"{contract_id}.jsonl")


def append_entry(entry: AuditEntry) -> None:
    """
    Append a single AuditEntry to the contract's JSONL audit file.
    Each line is one JSON record — append-only, never overwritten.
    """
    _ensure_audit_dir()
    path = _log_path(entry.contract_id)

    record = {
        "event_id":    entry.event_id,
        "contract_id": entry.contract_id,
        "action":      entry.action.value,
        "performed_by": entry.performed_by,
        "timestamp":   entry.timestamp.isoformat(),
        "details":     entry.details,
        "ip_address":  entry.ip_address,
    }

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    log.info(
        "AUDIT [%s] %s → %s by %s",
        entry.contract_id, entry.action.value,
        entry.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        entry.performed_by,
    )


def load_log(contract_id: str) -> AuditLog:
    """
    Load all audit entries for a contract from its JSONL file.
    Returns an empty AuditLog if no file exists yet.
    """
    path = _log_path(contract_id)

    if not os.path.exists(path):
        return AuditLog(contract_id=contract_id, entries=[])

    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                entries.append(AuditEntry(
                    event_id=rec["event_id"],
                    contract_id=rec["contract_id"],
                    action=AuditAction(rec["action"]),
                    performed_by=rec["performed_by"],
                    timestamp=datetime.fromisoformat(rec["timestamp"]),
                    details=rec.get("details"),
                    ip_address=rec.get("ip_address"),
                ))
            except (KeyError, ValueError) as exc:
                log.warning("Skipping malformed audit record: %s — %s", line[:80], exc)

    return AuditLog(contract_id=contract_id, entries=entries)


# ── Convenience recorders ──────────────────────────────────────────────────────

def record(
    contract_id: str,
    action: AuditAction,
    performed_by: str,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> AuditEntry:
    """
    Create and immediately persist an audit entry.
    Returns the created AuditEntry.
    """
    import uuid
    entry = AuditEntry(
        event_id=str(uuid.uuid4()),
        contract_id=contract_id,
        action=action,
        performed_by=performed_by,
        timestamp=datetime.now(timezone.utc),
        details=details,
        ip_address=ip_address,
    )
    append_entry(entry)
    return entry
