"""
API Error Handler
=================

Classified error handling for Claude and GitHub APIs with recovery strategies.

Features:
- Error classification by source and status code
- Recovery action determination
- Retry delay calculation with exponential backoff
- Rate limit detection
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional
import logging


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
            "raw_error": self.raw_error,
        }


# Error classification table
# Format: (source, code) -> (message, recoverable, action, retry_seconds)
ERROR_CLASSIFICATION: Dict[tuple, tuple] = {
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

# Maximum retry delay cap (5 minutes)
MAX_RETRY_DELAY_SECONDS = 300


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


def classify_error(
    source: APISource,
    code: int,
    raw_error: str = ""
) -> APIError:
    """
    Classify an API error and determine recovery strategy.

    Alias for create_api_error for compatibility with interface.

    Args:
        source: Which API returned the error
        code: HTTP status code
        raw_error: Original error message/exception string

    Returns:
        APIError with classification and recovery info
    """
    return create_api_error(source, code, raw_error)


def is_rate_limit(error: APIError) -> bool:
    """
    Check if error is a rate limit error.

    Args:
        error: Classified error

    Returns:
        True if 429 or rate limit indicator in message
    """
    if error.code == 429:
        return True

    rate_limit_keywords = ["rate limit", "rate_limit", "too many requests", "quota"]
    raw_lower = (error.raw_error or "").lower()
    message_lower = error.message.lower()

    return any(kw in raw_lower or kw in message_lower for kw in rate_limit_keywords)


def get_retry_delay(error: APIError, attempt: int) -> float:
    """
    Calculate delay before next retry with exponential backoff.

    Formula: base_delay * (2 ** attempt), capped at MAX_RETRY_DELAY_SECONDS

    Args:
        error: Classified error (provides base delay)
        attempt: Current retry attempt (0-indexed)

    Returns:
        Seconds to wait before retry
    """
    base_delay = max(error.retry_after_seconds, 5)  # Minimum 5 second base
    calculated_delay = base_delay * (2 ** attempt)
    return min(calculated_delay, MAX_RETRY_DELAY_SECONDS)


def classify_from_exception(
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
    raw_error = str(exception)

    # Try to extract status code from exception
    code = 0

    # Check for status_code attribute
    if hasattr(exception, 'status_code'):
        code = exception.status_code
    elif hasattr(exception, 'code'):
        code = exception.code
    elif hasattr(exception, 'response') and hasattr(exception.response, 'status_code'):
        code = exception.response.status_code

    # If no code found, try to parse from message
    if code == 0:
        import re
        # Look for patterns like "status 429" or "HTTP 500" or just "429"
        match = re.search(r'(?:status|http)?\s*(\d{3})', raw_error.lower())
        if match:
            code = int(match.group(1))

    # If still no code, use heuristics
    if code == 0:
        raw_lower = raw_error.lower()
        if "rate limit" in raw_lower or "too many" in raw_lower:
            code = 429
        elif "unauthorized" in raw_lower or "authentication" in raw_lower:
            code = 401
        elif "not found" in raw_lower:
            code = 404
        elif "timeout" in raw_lower:
            code = 504
        else:
            code = 500  # Default to server error

    return create_api_error(source, code, raw_error)
