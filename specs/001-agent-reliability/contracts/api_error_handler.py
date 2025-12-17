"""
API Error Handler Contract
==========================

Interface contract for classified API error handling with recovery strategies.

This is a contract/interface definition - not the implementation.
Implementation goes in the root-level api_error_handler.py module.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, Awaitable


class APISource(Enum):
    """Source of API error."""
    CLAUDE = "claude"
    GITHUB = "github"


class RecoveryAction(Enum):
    """Suggested recovery action for error."""
    ROTATE_TOKEN = "rotate_token"        # Try different auth token
    WAIT_AND_RETRY = "wait_and_retry"    # Exponential backoff
    PULL_AND_RETRY = "pull_and_retry"    # Git pull then retry
    MANUAL_REVIEW = "manual_review"      # Requires human intervention
    ABORT = "abort"                      # Cannot recover


@dataclass
class APIError:
    """
    Classified API error with recovery information.

    Attributes:
        source: Which API returned error (claude or github)
        code: HTTP status code
        message: Human-readable error description
        recoverable: Whether automated recovery is possible
        suggested_action: What recovery action to take
        retry_after_seconds: Wait time before retry (0 if no retry)
        raw_error: Original exception/error string
    """
    source: APISource
    code: int
    message: str
    recoverable: bool
    suggested_action: RecoveryAction
    retry_after_seconds: int = 0
    raw_error: Optional[str] = None

    def should_retry(self) -> bool:
        """Determine if error warrants retry."""
        return self.recoverable and self.suggested_action in (
            RecoveryAction.ROTATE_TOKEN,
            RecoveryAction.WAIT_AND_RETRY,
            RecoveryAction.PULL_AND_RETRY,
        )

    def to_dict(self) -> dict:
        """Serialize for logging."""
        return {
            "source": self.source.value,
            "code": self.code,
            "message": self.message,
            "recoverable": self.recoverable,
            "action": self.suggested_action.value,
            "retry_after": self.retry_after_seconds,
        }


# Error classification table
# Format: code -> (message, recoverable, action, retry_seconds)
ERROR_CLASSIFICATION = {
    # Claude API errors
    (APISource.CLAUDE, 400): ("Bad Request - content may have been filtered", False, RecoveryAction.MANUAL_REVIEW, 0),
    (APISource.CLAUDE, 401): ("Authentication failed", True, RecoveryAction.ROTATE_TOKEN, 0),
    (APISource.CLAUDE, 403): ("Forbidden - check API permissions", False, RecoveryAction.ABORT, 0),
    (APISource.CLAUDE, 429): ("Rate limited", True, RecoveryAction.WAIT_AND_RETRY, 60),
    (APISource.CLAUDE, 500): ("Server error", True, RecoveryAction.WAIT_AND_RETRY, 30),
    (APISource.CLAUDE, 529): ("Overloaded", True, RecoveryAction.WAIT_AND_RETRY, 120),

    # GitHub API errors
    (APISource.GITHUB, 401): ("Authentication failed - check gh auth status", True, RecoveryAction.ROTATE_TOKEN, 0),
    (APISource.GITHUB, 403): ("Forbidden - may be rate limited or insufficient permissions", True, RecoveryAction.WAIT_AND_RETRY, 60),
    (APISource.GITHUB, 404): ("Not found - resource may have been deleted", False, RecoveryAction.ABORT, 0),
    (APISource.GITHUB, 409): ("Conflict - may need to pull latest", True, RecoveryAction.PULL_AND_RETRY, 5),
    (APISource.GITHUB, 422): ("Validation failed - check request format", False, RecoveryAction.ABORT, 0),
    (APISource.GITHUB, 429): ("Rate limited", True, RecoveryAction.WAIT_AND_RETRY, 60),
    (APISource.GITHUB, 500): ("Server error", True, RecoveryAction.WAIT_AND_RETRY, 30),
    (APISource.GITHUB, 502): ("Bad gateway", True, RecoveryAction.WAIT_AND_RETRY, 30),
    (APISource.GITHUB, 503): ("Service unavailable", True, RecoveryAction.WAIT_AND_RETRY, 60),
}


class IAPIErrorHandler(ABC):
    """
    Interface for API error classification and recovery.

    Implementations must:
    - Classify errors from both Claude and GitHub APIs
    - Provide appropriate recovery actions
    - Handle retry logic with exponential backoff
    - Integrate with token rotation system
    """

    @abstractmethod
    def classify_error(
        self,
        source: APISource,
        code: int,
        raw_error: str = ""
    ) -> APIError:
        """
        Classify an API error and determine recovery strategy.

        Args:
            source: Which API returned the error
            code: HTTP status code
            raw_error: Original error message/exception string

        Returns:
            APIError with classification and recovery info
        """
        pass

    @abstractmethod
    async def handle_error(
        self,
        error: APIError,
        retry_callback: Callable[[], Awaitable[bool]],
        max_retries: int = 3
    ) -> bool:
        """
        Handle an API error with appropriate recovery strategy.

        Steps based on suggested_action:
        - ROTATE_TOKEN: Call token rotator, then retry
        - WAIT_AND_RETRY: Sleep for retry_after_seconds, then retry
        - PULL_AND_RETRY: Run git pull, then retry
        - MANUAL_REVIEW: Log and return False
        - ABORT: Log and return False

        Args:
            error: Classified API error
            retry_callback: Async function to retry the operation
            max_retries: Maximum retry attempts

        Returns:
            True if operation succeeded after recovery, False otherwise
        """
        pass

    @abstractmethod
    def classify_from_exception(
        self,
        source: APISource,
        exception: Exception
    ) -> APIError:
        """
        Classify error from an exception object.

        Extracts status code from exception if available,
        otherwise uses heuristics on error message.

        Args:
            source: Which API the exception came from
            exception: The exception object

        Returns:
            APIError with best-effort classification
        """
        pass

    @abstractmethod
    def is_rate_limit(self, error: APIError) -> bool:
        """
        Check if error is a rate limit error.

        Args:
            error: Classified error

        Returns:
            True if 429 or rate limit indicator in message
        """
        pass

    @abstractmethod
    def get_retry_delay(self, error: APIError, attempt: int) -> float:
        """
        Calculate delay before next retry with exponential backoff.

        Formula: base_delay * (2 ** attempt)

        Args:
            error: Classified error (provides base delay)
            attempt: Current retry attempt (0-indexed)

        Returns:
            Seconds to wait before retry
        """
        pass


# Helper function for creating errors
def create_api_error(
    source: APISource,
    code: int,
    raw_error: str = ""
) -> APIError:
    """
    Factory function to create classified APIError.

    Args:
        source: API source
        code: HTTP status code
        raw_error: Original error string

    Returns:
        APIError with appropriate classification
    """
    key = (source, code)

    if key in ERROR_CLASSIFICATION:
        message, recoverable, action, retry_after = ERROR_CLASSIFICATION[key]
    else:
        # Unknown error - default to non-recoverable
        message = f"Unknown error (code {code})"
        recoverable = code >= 500  # Server errors might be transient
        action = RecoveryAction.WAIT_AND_RETRY if recoverable else RecoveryAction.ABORT
        retry_after = 30 if recoverable else 0

    return APIError(
        source=source,
        code=code,
        message=message,
        recoverable=recoverable,
        suggested_action=action,
        retry_after_seconds=retry_after,
        raw_error=raw_error,
    )
