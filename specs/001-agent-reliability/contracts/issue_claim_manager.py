"""
Issue Claim Manager Contract
============================

Interface contract for the enhanced issue claiming system with TTL support.

This is a contract/interface definition - not the implementation.
Implementation goes in the root-level issue_claim_manager.py module.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple


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
    failure_reasons: List[str] = None
    expires_at: Optional[datetime] = None

    def __post_init__(self):
        if self.failure_reasons is None:
            self.failure_reasons = []

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
        return cls(
            issue_number=issue_number,
            session_id=data["session_id"],
            claimed_at=datetime.fromisoformat(data["claimed_at"]),
            title=data.get("title", ""),
            status=ClaimStatus(data.get("status", "claimed")),
            failure_count=data.get("failure_count", 0),
            last_failure_at=datetime.fromisoformat(data["last_failure_at"]) if data.get("last_failure_at") else None,
            failure_reasons=data.get("failure_reasons", []),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
        )


class IIssueClaimManager(ABC):
    """
    Interface for issue claim management with TTL support.

    Implementations must handle:
    - Atomic claim acquisition (prevent race conditions)
    - TTL-based expiration (30 minute default)
    - Failure tracking (count, reasons, timestamps)
    - Stale claim cleanup (lazy evaluation on claim attempt)
    - Deprioritization of repeatedly failing issues
    """

    # Configuration
    CLAIM_TTL_MINUTES: int = 30
    FAILURE_DEPRIORITIZE_THRESHOLD: int = 3

    @abstractmethod
    def claim_issue(self, session_id: str) -> Optional[int]:
        """
        Atomically claim the next available issue.

        Steps:
        1. Acquire file lock
        2. Cleanup stale claims (TTL expired)
        3. Get open issues from GitHub
        4. Filter out claimed and META issues
        5. Sort by priority (deprioritize high-failure issues)
        6. Claim first available
        7. Save claims and release lock

        Args:
            session_id: Unique identifier for claiming session

        Returns:
            Issue number if claimed, None if no issues available
        """
        pass

    @abstractmethod
    def release_issue(self, issue_num: int, session_id: str) -> bool:
        """
        Release claim on an issue (successful completion).

        Args:
            issue_num: Issue number to release
            session_id: Session releasing the claim

        Returns:
            True if released, False if not found or wrong session
        """
        pass

    @abstractmethod
    def mark_failed(
        self,
        issue_num: int,
        session_id: str,
        reason: str
    ) -> bool:
        """
        Mark issue claim as failed (increment failure counter).

        The claim is NOT released - it stays in failed state until TTL expires.
        This prevents immediate re-claiming that could cause infinite loops.

        Args:
            issue_num: Issue number
            session_id: Session marking failure
            reason: Short failure reason (e.g., "content_filter", "timeout")

        Returns:
            True if marked, False if not found or wrong session
        """
        pass

    @abstractmethod
    def get_claim(self, issue_num: int) -> Optional[IssueClaim]:
        """
        Get current claim for an issue.

        Args:
            issue_num: Issue number

        Returns:
            IssueClaim if claimed, None if not claimed or expired
        """
        pass

    @abstractmethod
    def get_active_claims(self) -> Dict[int, IssueClaim]:
        """
        Get all active (non-expired) claims.

        Returns:
            Dictionary of issue_number -> IssueClaim
        """
        pass

    @abstractmethod
    def cleanup_stale_claims(self) -> List[int]:
        """
        Remove all expired claims.

        Called automatically by claim_issue(), but can be called manually.

        Returns:
            List of issue numbers that were cleaned up
        """
        pass

    @abstractmethod
    def get_failure_history(self, issue_num: int) -> Tuple[int, List[str]]:
        """
        Get failure history for an issue.

        Args:
            issue_num: Issue number

        Returns:
            Tuple of (failure_count, failure_reasons)
        """
        pass

    @abstractmethod
    def is_deprioritized(self, issue_num: int) -> bool:
        """
        Check if issue should be deprioritized due to failures.

        Args:
            issue_num: Issue number

        Returns:
            True if failure_count >= FAILURE_DEPRIORITIZE_THRESHOLD
        """
        pass


# Type alias for JSON storage format
ClaimsJson = Dict[str, Dict]  # {"42": {"session_id": "...", ...}}
