"""
Progress Tracking Utilities
===========================

Functions for tracking and displaying progress of the autonomous coding agent.
Progress is tracked via GitHub Issues, with local state cached in .github_project.json.
"""

import json
from pathlib import Path

from github_config import GITHUB_PROJECT_MARKER


def load_github_project_state(project_dir: Path) -> dict | None:
    """
    Load the GitHub project state from the marker file.

    Args:
        project_dir: Directory containing .github_project.json

    Returns:
        Project state dict or None if not initialized
    """
    marker_file = project_dir / GITHUB_PROJECT_MARKER

    if not marker_file.exists():
        return None

    try:
        with open(marker_file, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def is_github_initialized(project_dir: Path) -> bool:
    """
    Check if GitHub project has been initialized.

    Args:
        project_dir: Directory to check

    Returns:
        True if .github_project.json exists and is valid
    """
    state = load_github_project_state(project_dir)
    return state is not None and state.get("initialized", False)


def print_session_header(session_num: int, is_initializer: bool) -> None:
    """Print a formatted header for the session."""
    session_type = "INITIALIZER" if is_initializer else "CODING AGENT"

    print("\n" + "=" * 70)
    print(f"  SESSION {session_num}: {session_type}")
    print("=" * 70)
    print()


def print_progress_summary(project_dir: Path) -> None:
    """
    Print a summary of current progress.

    Since actual progress is tracked in GitHub Issues, this reads the local
    state file for cached information. The agent updates GitHub directly
    and reports progress in session comments.
    """
    state = load_github_project_state(project_dir)

    if state is None:
        print("\nProgress: GitHub project not yet initialized")
        return

    total = state.get("total_issues", 0)
    meta_issue = state.get("meta_issue_number", "unknown")
    repo = state.get("repo", "unknown")

    print(f"\nGitHub Project Status:")
    print(f"  Repository: {repo}")
    print(f"  Total issues created: {total}")
    print(f"  META issue: #{meta_issue}")
    print(f"  (Check GitHub for current open/closed counts)")
