"""
Session Outcome Contract
========================

Interface contract for tracking session outcomes with accurate validation.

This is a contract/interface definition - not the implementation.
Implementation integrates with existing session_state.py module.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class OutcomeStatus(Enum):
    """Overall session outcome status."""
    SUCCESS = "success"              # Closed issues, made changes
    PARTIAL = "partial"              # Some work done, not all closed
    NO_WORK = "no_work"              # No issues available
    FAILED = "failed"                # Errors prevented completion
    UNHEALTHY = "unhealthy"          # Session health check failed


@dataclass
class ProductivityMetrics:
    """
    Metrics for calculating session productivity.

    Used to detect "busy but unproductive" sessions.
    """
    tool_count: int                      # Total tool invocations
    files_changed: int                   # Files with modifications
    issues_closed: int                   # Issues successfully closed
    response_length: int = 0             # Total response text length

    @property
    def score(self) -> float:
        """
        Calculate productivity score.

        Formula: (files_changed * 2 + issues_closed * 5) / max(tool_count, 1)

        Interpretation:
        - < 0.1: Very low productivity (many tools, no output)
        - 0.1-0.5: Low productivity
        - 0.5-1.0: Normal productivity
        - > 1.0: High productivity
        """
        outcomes = self.files_changed * 2 + self.issues_closed * 5
        return outcomes / max(self.tool_count, 1)

    @property
    def is_low_productivity(self) -> bool:
        """Check if productivity is below warning threshold."""
        return self.tool_count >= 30 and self.score < 0.1

    def get_warnings(self) -> List[str]:
        """Generate productivity warnings if applicable."""
        warnings = []

        if self.tool_count >= 30 and self.files_changed == 0:
            warnings.append(
                f"Low productivity: {self.tool_count} tool calls but 0 files changed"
            )

        if self.tool_count >= 30 and self.score < 0.1:
            warnings.append(
                f"Productivity score {self.score:.3f} below threshold 0.1"
            )

        return warnings


@dataclass
class SessionOutcome:
    """
    Represents the result of a coding session.

    Key improvement: tracks SPECIFIC issues worked on,
    not time-based queries that count other sessions' work.
    """
    session_id: str                      # Session identifier
    issues_worked: List[int]             # Issues THIS session claimed
    issues_closed: List[int]             # Issues THIS session closed
    files_changed: int                   # Number of files modified
    tool_count: int                      # Total tool invocations
    duration_seconds: float              # Session duration
    started_at: datetime                 # Session start time
    ended_at: Optional[datetime] = None  # Session end time
    status: OutcomeStatus = OutcomeStatus.PARTIAL
    warnings: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Percentage of worked issues that were closed."""
        if not self.issues_worked:
            return 0.0
        return len(self.issues_closed) / len(self.issues_worked)

    @property
    def is_successful(self) -> bool:
        """True if at least one issue closed and code changed."""
        return len(self.issues_closed) >= 1 and self.files_changed > 0

    @property
    def productivity_score(self) -> float:
        """Calculate productivity score."""
        metrics = ProductivityMetrics(
            tool_count=self.tool_count,
            files_changed=self.files_changed,
            issues_closed=len(self.issues_closed),
        )
        return metrics.score

    def to_metrics(self) -> ProductivityMetrics:
        """Convert to ProductivityMetrics for analysis."""
        return ProductivityMetrics(
            tool_count=self.tool_count,
            files_changed=self.files_changed,
            issues_closed=len(self.issues_closed),
        )

    def to_dict(self) -> Dict:
        """Serialize for logging."""
        return {
            "session_id": self.session_id,
            "issues_worked": self.issues_worked,
            "issues_closed": self.issues_closed,
            "files_changed": self.files_changed,
            "tool_count": self.tool_count,
            "duration_seconds": self.duration_seconds,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "status": self.status.value,
            "success_rate": self.success_rate,
            "productivity_score": self.productivity_score,
            "warnings": self.warnings,
        }


class ISessionOutcomeTracker(ABC):
    """
    Interface for tracking session outcomes accurately.

    Key improvement: validates outcomes by checking
    SPECIFIC issues worked on by this session.
    """

    @abstractmethod
    def start_session(self, session_id: str) -> None:
        """
        Start tracking a new session.

        Args:
            session_id: Unique session identifier
        """
        pass

    @abstractmethod
    def record_issue_claimed(self, issue_num: int) -> None:
        """
        Record that this session claimed an issue.

        Args:
            issue_num: GitHub issue number
        """
        pass

    @abstractmethod
    def record_issue_closed(self, issue_num: int) -> None:
        """
        Record that this session closed an issue.

        Args:
            issue_num: GitHub issue number
        """
        pass

    @abstractmethod
    def record_file_change(self, file_path: str) -> None:
        """
        Record that this session modified a file.

        Args:
            file_path: Path to modified file
        """
        pass

    @abstractmethod
    def record_tool_use(self, tool_name: str) -> None:
        """
        Record tool invocation.

        Args:
            tool_name: Name of tool used
        """
        pass

    @abstractmethod
    def end_session(self) -> SessionOutcome:
        """
        End session tracking and return outcome.

        Validates outcomes by checking GitHub state
        for SPECIFIC issues this session worked on.

        Returns:
            SessionOutcome with validated metrics
        """
        pass

    @abstractmethod
    def validate_outcomes(self, repo: str) -> SessionOutcome:
        """
        Validate outcomes against actual GitHub state.

        For each issue in issues_worked:
        - Query GitHub for current state
        - If state is CLOSED, add to issues_closed

        Args:
            repo: GitHub repo in owner/name format

        Returns:
            SessionOutcome with validated metrics
        """
        pass

    @abstractmethod
    def get_productivity_warnings(self) -> List[str]:
        """
        Get productivity warnings for current session.

        Returns:
            List of warning messages (empty if healthy)
        """
        pass


@dataclass
class BacklogState:
    """
    Tracks empty backlog rounds for graceful termination.
    """
    consecutive_no_issues: int = 0       # Rounds with no work
    threshold: int = 3                   # Rounds before termination
    last_check: Optional[datetime] = None

    def record_round(self, session_results: List[str]) -> bool:
        """
        Record round results and check if should terminate.

        Args:
            session_results: List of session result strings

        Returns:
            True if agent should stop (threshold reached)
        """
        self.last_check = datetime.now()

        all_no_issues = all(
            "No unclaimed issues" in result or "NO_ISSUES" in result
            for result in session_results
        )

        if all_no_issues:
            self.consecutive_no_issues += 1
            return self.consecutive_no_issues >= self.threshold
        else:
            self.consecutive_no_issues = 0
            return False

    def should_terminate(self) -> bool:
        """Check if termination threshold reached."""
        return self.consecutive_no_issues >= self.threshold

    def reset(self) -> None:
        """Reset counter (called when new issues appear)."""
        self.consecutive_no_issues = 0
