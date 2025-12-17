"""
GitHub Configuration
====================

Configuration constants for GitHub Issues and GitHub Projects integration.
These values are used in prompts and for project state management.
"""

# Default number of issues to create (can be overridden via command line)
DEFAULT_ISSUE_COUNT = 50

# Issue workflow states (GitHub Project v2 column names)
# These match the default columns in a GitHub Project
STATUS_TODO = "Todo"
STATUS_IN_PROGRESS = "In Progress"
STATUS_DONE = "Done"

# Priority labels (GitHub doesn't have native priority, so we use labels)
# Format: "priority:level"
PRIORITY_URGENT = "priority:urgent"
PRIORITY_HIGH = "priority:high"
PRIORITY_MEDIUM = "priority:medium"
PRIORITY_LOW = "priority:low"

# Priority label list (for creating labels)
PRIORITY_LABELS = [
    {"name": "priority:urgent", "color": "B60205", "description": "Urgent - must be done immediately"},
    {"name": "priority:high", "color": "D93F0B", "description": "High priority"},
    {"name": "priority:medium", "color": "FBCA04", "description": "Medium priority"},
    {"name": "priority:low", "color": "0E8A16", "description": "Low priority - nice to have"},
]

# Category labels (for organizing issues)
CATEGORY_LABELS = [
    {"name": "functional", "color": "1D76DB", "description": "Functional feature"},
    {"name": "style", "color": "5319E7", "description": "Styling/UI feature"},
    {"name": "infrastructure", "color": "006B75", "description": "Infrastructure/DevOps"},
]

# Label categories (map to feature types)
LABEL_FUNCTIONAL = "functional"
LABEL_STYLE = "style"
LABEL_INFRASTRUCTURE = "infrastructure"

# Local marker file to track GitHub project initialization
GITHUB_PROJECT_MARKER = ".github_project.json"

# Meta issue title for project tracking and session handoff
META_ISSUE_TITLE = "[META] Project Progress Tracker"

# GitHub API rate limit (more generous than Linear)
GITHUB_RATE_LIMIT_HOURLY = 5000
GITHUB_RATE_LIMIT_WARNING_THRESHOLD = 0.8  # Warn at 80%

# Default limit for gh issue list commands
# The default gh limit is 30, which is too low for larger projects
# Use 10000 to effectively get all issues (most projects have < 1000)
GITHUB_ISSUE_LIST_LIMIT = 10000

# ============================================================================
# Agent Reliability Configuration
# ============================================================================

# Issue claim TTL in minutes - claims older than this are considered stale
# and will be cleaned up automatically to prevent deadlocks
CLAIM_TTL_MINUTES = 30

# Maximum consecutive rounds with no issues available before terminating
# Used for graceful termination when all issues are complete
MAX_NO_ISSUES_ROUNDS = 3

# Productivity score threshold - sessions with score below this after
# 30+ tool calls are flagged as potentially stuck/unproductive
# Formula: (files_changed * 2 + issues_closed * 5) / max(tool_count, 1)
PRODUCTIVITY_THRESHOLD = 0.1

# Number of failures before deprioritizing an issue in claim selection
FAILURE_DEPRIORITIZE_THRESHOLD = 3

# Default GitHub organization for new repos
DEFAULT_GITHUB_ORG = "ProvidenceIT"


def get_repo_info(project_dir) -> dict:
    """
    Get GitHub repo info from project's .github_project.json.

    Returns:
        dict with 'repo' (owner/name) and 'org' keys, or empty dict if not found
    """
    import json
    from pathlib import Path

    project_file = Path(project_dir) / GITHUB_PROJECT_MARKER
    if project_file.exists():
        try:
            with open(project_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {
                    'repo': data.get('repo', ''),
                    'org': data.get('org', DEFAULT_GITHUB_ORG),
                    'repo_url': data.get('repo_url', '')
                }
        except Exception:
            pass
    return {}


def save_repo_info(project_dir, repo: str, org: str = None):
    """
    Save GitHub repo info to project's .github_project.json.

    Args:
        project_dir: Project directory path
        repo: Full repo name (org/repo-name)
        org: Organization name (extracted from repo if not provided)
    """
    import json
    from pathlib import Path
    from datetime import datetime

    project_file = Path(project_dir) / GITHUB_PROJECT_MARKER

    # Load existing data or create new
    data = {}
    if project_file.exists():
        try:
            with open(project_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            pass

    # Extract org from repo if not provided
    if not org and '/' in repo:
        org = repo.split('/')[0]

    # Update repo info
    data['repo'] = repo
    data['org'] = org or DEFAULT_GITHUB_ORG
    data['repo_url'] = f"https://github.com/{repo}"
    data['repo_updated_at'] = datetime.now().isoformat()

    # Save
    with open(project_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
