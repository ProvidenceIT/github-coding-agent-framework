"""
Session State Tracking
======================

Lightweight checkpoint system to reduce redundant exploration across sessions.
Saves minimal state between sessions to help agents orient faster.
"""
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, List, Optional


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
