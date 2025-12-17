"""
Session State Tracking
======================

Lightweight checkpoint system to reduce redundant exploration across sessions.
Saves minimal state between sessions to help agents orient faster.

Also includes session outcome tracking with productivity metrics for the
agent reliability feature.
"""
from dataclasses import dataclass, field
from pathlib import Path
import json
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from github_config import PRODUCTIVITY_THRESHOLD


# =============================================================================
# Session Outcome Tracking (Agent Reliability Feature)
# =============================================================================

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
        return self.tool_count >= 30 and self.score < PRODUCTIVITY_THRESHOLD

    def get_warnings(self) -> List[str]:
        """Generate productivity warnings if applicable."""
        warnings = []

        if self.tool_count >= 30 and self.files_changed == 0:
            warnings.append(
                f"Low productivity: {self.tool_count} tool calls but 0 files changed"
            )

        if self.tool_count >= 30 and self.score < PRODUCTIVITY_THRESHOLD:
            warnings.append(
                f"Productivity score {self.score:.3f} below threshold {PRODUCTIVITY_THRESHOLD}"
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
            response_length=0,  # Not tracked at this level
        )

    def determine_status(self) -> OutcomeStatus:
        """Determine outcome status based on results."""
        if not self.issues_worked:
            return OutcomeStatus.NO_WORK

        if self.is_successful:
            return OutcomeStatus.SUCCESS

        if self.files_changed > 0 or len(self.issues_closed) > 0:
            return OutcomeStatus.PARTIAL

        return OutcomeStatus.FAILED

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


# =============================================================================
# Original Session Checkpoint Functions
# =============================================================================


def save_session_checkpoint(project_dir: Path, data: dict) -> None:
    """
    Save session checkpoint to track state between sessions.

    Args:
        project_dir: Project directory path
        data: Dictionary containing session state:
            - issues_closed: list of issue numbers closed
            - current_focus: string describing what was being worked on
            - modified_files: list of file paths modified
            - notes: any notes for next session
    """
    checkpoint_file = project_dir / ".session_checkpoint.json"
    data['timestamp'] = datetime.now().isoformat()
    data['checkpoint_version'] = '1.0'

    try:
        checkpoint_file.write_text(json.dumps(data, indent=2), encoding='utf-8')
    except Exception as e:
        print(f"⚠️  Warning: Could not save checkpoint: {e}")


def load_session_checkpoint(project_dir: Path) -> Dict:
    """
    Load last session checkpoint.

    Args:
        project_dir: Project directory path

    Returns:
        Dictionary with session state, or empty dict if no checkpoint exists
    """
    checkpoint_file = project_dir / ".session_checkpoint.json"

    if not checkpoint_file.exists():
        return {}

    try:
        content = checkpoint_file.read_text(encoding='utf-8')
        return json.loads(content)
    except Exception as e:
        print(f"⚠️  Warning: Could not load checkpoint: {e}")
        return {}


def get_orientation_summary(project_dir: Path) -> str:
    """
    Generate quick orientation summary for prompt injection.

    This helps the agent skip redundant exploration by providing context
    from the previous session.

    Args:
        project_dir: Project directory path

    Returns:
        Formatted string with previous session summary
    """
    checkpoint = load_session_checkpoint(project_dir)

    if not checkpoint:
        return ""

    timestamp = checkpoint.get('timestamp', 'unknown')
    issues_closed = checkpoint.get('issues_closed', [])
    current_focus = checkpoint.get('current_focus', 'unknown')
    modified_files = checkpoint.get('modified_files', [])
    notes = checkpoint.get('notes', '')

    summary_parts = [
        "\n## 📋 PREVIOUS SESSION SUMMARY",
        f"Last session: {timestamp}",
        f"Issues closed: {', '.join(f'#{n}' for n in issues_closed) if issues_closed else 'none'}",
        f"Files modified: {len(modified_files)}",
        f"Focus: {current_focus}",
    ]

    if notes:
        summary_parts.append(f"\n**Notes from previous session:**\n{notes}")

    summary_parts.append("\n**You can skip basic orientation and focus on checking GitHub status.**\n")

    return "\n".join(summary_parts)


def track_session_activity(
    project_dir: Path,
    issues_closed: Optional[List[int]] = None,
    current_focus: Optional[str] = None,
    modified_files: Optional[List[str]] = None,
    notes: Optional[str] = None
) -> None:
    """
    Update session checkpoint with current activity.

    This is a convenience function for updating the checkpoint incrementally
    during a session.

    Args:
        project_dir: Project directory path
        issues_closed: List of issue numbers closed this session
        current_focus: Description of current work
        modified_files: List of files modified
        notes: Notes for next session
    """
    # Load existing checkpoint
    checkpoint = load_session_checkpoint(project_dir)

    # Update with new data (only if provided)
    if issues_closed is not None:
        checkpoint['issues_closed'] = issues_closed

    if current_focus is not None:
        checkpoint['current_focus'] = current_focus

    if modified_files is not None:
        checkpoint['modified_files'] = modified_files

    if notes is not None:
        checkpoint['notes'] = notes

    # Save updated checkpoint
    save_session_checkpoint(project_dir, checkpoint)


def get_quick_status(project_dir: Path) -> Dict:
    """
    Get quick project status for agent orientation.

    Returns information about:
    - Whether project is initialized
    - Whether GitHub project exists
    - Number of files in project
    - Last session info

    Args:
        project_dir: Project directory path

    Returns:
        Dictionary with status information
    """
    status = {
        'initialized': (project_dir / ".initialized").exists(),
        'has_github_project': (project_dir / ".github_project.json").exists(),
        'has_app_spec': (project_dir / "app_spec.txt").exists(),
        'file_count': 0,
        'last_session': None
    }

    # Count project files (excluding node_modules, .git, etc.)
    try:
        exclude_dirs = {'.git', 'node_modules', '.next', 'dist', 'build', '__pycache__'}
        file_count = 0
        for item in project_dir.rglob('*'):
            if item.is_file() and not any(excluded in item.parts for excluded in exclude_dirs):
                file_count += 1
        status['file_count'] = file_count
    except Exception:
        pass

    # Get last session info
    checkpoint = load_session_checkpoint(project_dir)
    if checkpoint:
        status['last_session'] = {
            'timestamp': checkpoint.get('timestamp'),
            'focus': checkpoint.get('current_focus'),
            'issues_closed': len(checkpoint.get('issues_closed', []))
        }

    return status
