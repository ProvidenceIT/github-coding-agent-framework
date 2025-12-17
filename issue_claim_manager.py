"""
Issue Claim Manager
===================

Enhanced issue claiming system with TTL support and failure tracking.

Features:
- TTL-based claim expiration (30 minute default)
- Failure tracking with deprioritization
- Stale claim cleanup
- Atomic claiming with file locking
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import logging

from github_config import (
    CLAIM_TTL_MINUTES,
    FAILURE_DEPRIORITIZE_THRESHOLD,
)


class ClaimStatus(Enum):
    """Status of an issue claim."""
    CLAIMED = "claimed"          # Actively being worked on
    FAILED = "failed"            # Session failed without closing
    RELEASED = "released"        # Explicitly released
    EXPIRED = "expired"          # TTL exceeded, auto-released


@dataclass
class IssueClaim:
    """
    Represents a session's claim on a GitHub issue.

    Attributes:
        issue_number: GitHub issue number
        session_id: Claiming session identifier
        claimed_at: When claim was acquired
        title: Issue title for display
        status: Current claim status
        failure_count: Number of failed attempts on this issue
        last_failure_at: When last failure occurred
        failure_reasons: List of failure reason strings
        expires_at: When claim will auto-expire (TTL)
    """
    issue_number: int
    session_id: str
    claimed_at: datetime
    title: str
    status: ClaimStatus = ClaimStatus.CLAIMED
    failure_count: int = 0
    last_failure_at: Optional[datetime] = None
    failure_reasons: List[str] = field(default_factory=list)
    expires_at: Optional[datetime] = None

    def __post_init__(self):
        """Initialize default values and set TTL expiration."""
        if self.failure_reasons is None:
            self.failure_reasons = []

        # Set expiration if not already set
        if self.expires_at is None:
            self.expires_at = self.claimed_at + timedelta(minutes=CLAIM_TTL_MINUTES)

    @property
    def is_expired(self) -> bool:
        """Check if claim has exceeded TTL."""
        if self.expires_at is None:
            return False
        return datetime.now() >= self.expires_at

    @property
    def age_minutes(self) -> float:
        """Return claim age in minutes."""
        return (datetime.now() - self.claimed_at).total_seconds() / 60

    @property
    def is_deprioritized(self) -> bool:
        """Check if issue should be deprioritized due to failures."""
        return self.failure_count >= FAILURE_DEPRIORITIZE_THRESHOLD

    def mark_failed(self, reason: str) -> None:
        """
        Mark the claim as failed with a reason.

        Args:
            reason: Short failure reason (e.g., "content_filter", "timeout")
        """
        self.status = ClaimStatus.FAILED
        self.failure_count += 1
        self.last_failure_at = datetime.now()
        self.failure_reasons.append(reason)

    def to_dict(self) -> Dict:
        """Serialize to dictionary for JSON storage."""
        return {
            "issue_number": self.issue_number,
            "session_id": self.session_id,
            "claimed_at": self.claimed_at.isoformat(),
            "title": self.title,
            "status": self.status.value,
            "failure_count": self.failure_count,
            "last_failure_at": self.last_failure_at.isoformat() if self.last_failure_at else None,
            "failure_reasons": self.failure_reasons,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @classmethod
    def from_dict(cls, issue_number: int, data: Dict) -> "IssueClaim":
        """Deserialize from dictionary."""
        # Parse claimed_at
        claimed_at = datetime.fromisoformat(data["claimed_at"])

        # Parse expires_at, defaulting to claimed_at + TTL if not present
        expires_at = None
        if data.get("expires_at"):
            expires_at = datetime.fromisoformat(data["expires_at"])
        else:
            expires_at = claimed_at + timedelta(minutes=CLAIM_TTL_MINUTES)

        return cls(
            issue_number=issue_number,
            session_id=data["session_id"],
            claimed_at=claimed_at,
            title=data.get("title", ""),
            status=ClaimStatus(data.get("status", "claimed")),
            failure_count=data.get("failure_count", 0),
            last_failure_at=datetime.fromisoformat(data["last_failure_at"]) if data.get("last_failure_at") else None,
            failure_reasons=data.get("failure_reasons", []),
            expires_at=expires_at,
        )


# Type alias for JSON storage format
ClaimsJson = Dict[str, Dict]  # {"42": {"session_id": "...", ...}}
