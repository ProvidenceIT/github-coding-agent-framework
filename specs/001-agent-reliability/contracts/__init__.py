"""
Agent Reliability Contracts
===========================

Interface contracts for the agent reliability feature.
These define the APIs that must be implemented.

Contracts:
- issue_claim_manager: TTL-based claim lifecycle
- api_error_handler: Classified error handling
- session_outcome: Accurate outcome validation
- github_projects: Projects v2 integration
"""

from .issue_claim_manager import (
    IssueClaim,
    ClaimStatus,
    IIssueClaimManager,
)

from .api_error_handler import (
    APIError,
    APISource,
    RecoveryAction,
    IAPIErrorHandler,
    create_api_error,
    ERROR_CLASSIFICATION,
)

from .session_outcome import (
    SessionOutcome,
    OutcomeStatus,
    ProductivityMetrics,
    BacklogState,
    ISessionOutcomeTracker,
)

from .github_projects import (
    GitHubProjectItem,
    ProjectStatus,
    ProjectMetadata,
    IGitHubProjectsManager,
)

__all__ = [
    # Issue Claims
    "IssueClaim",
    "ClaimStatus",
    "IIssueClaimManager",

    # API Errors
    "APIError",
    "APISource",
    "RecoveryAction",
    "IAPIErrorHandler",
    "create_api_error",
    "ERROR_CLASSIFICATION",

    # Session Outcomes
    "SessionOutcome",
    "OutcomeStatus",
    "ProductivityMetrics",
    "BacklogState",
    "ISessionOutcomeTracker",

    # GitHub Projects
    "GitHubProjectItem",
    "ProjectStatus",
    "ProjectMetadata",
    "IGitHubProjectsManager",
]
