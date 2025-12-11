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
