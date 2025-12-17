"""
Test API Error Handler
======================

Unit tests for API error classification and recovery.

Tests:
- Claude API error codes (400, 401, 429, 500, 529)
- GitHub API error codes (401, 403, 404, 409, 422, 429)
- Recovery action determination
- Retry delay calculations
- GitHub CLI error wrapper
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import subprocess

from api_error_handler import (
    APIError, APISource, RecoveryAction,
    classify_error, create_api_error, is_rate_limit, get_retry_delay,
    classify_from_exception, MAX_RETRY_DELAY_SECONDS,
)
from github_cache import GitHubAPIError, execute_gh_command


class TestClaudeErrorClassification:
    """Tests for Claude API error classification."""

    def test_classify_400_bad_request(self):
        """400 errors should suggest manual review (content filtered)."""
        error = create_api_error(APISource.CLAUDE, 400, "Content filtered")
        assert error.code == 400
        assert error.source == APISource.CLAUDE
        assert error.recoverable is False
        assert error.suggested_action == RecoveryAction.MANUAL_REVIEW

    def test_classify_401_auth_failed(self):
        """401 errors should suggest token rotation."""
        error = create_api_error(APISource.CLAUDE, 401, "Invalid API key")
        assert error.code == 401
        assert error.recoverable is True
        assert error.suggested_action == RecoveryAction.ROTATE_TOKEN

    def test_classify_429_rate_limited(self):
        """429 errors should suggest wait and retry."""
        error = create_api_error(APISource.CLAUDE, 429, "Rate limited")
        assert error.code == 429
        assert error.recoverable is True
        assert error.suggested_action == RecoveryAction.WAIT_AND_RETRY
        assert error.retry_after_seconds == 60

    def test_classify_500_server_error(self):
        """500 errors should suggest wait and retry."""
        error = create_api_error(APISource.CLAUDE, 500, "Server error")
        assert error.code == 500
        assert error.recoverable is True
        assert error.suggested_action == RecoveryAction.WAIT_AND_RETRY

    def test_classify_529_overloaded(self):
        """529 (overloaded) should suggest longer retry delay."""
        error = create_api_error(APISource.CLAUDE, 529, "Overloaded")
        assert error.code == 529
        assert error.recoverable is True
        assert error.retry_after_seconds == 120


class TestGitHubErrorClassification:
    """Tests for GitHub API error classification."""

    def test_classify_401_auth_failed(self):
        """401 errors should suggest token rotation."""
        error = create_api_error(APISource.GITHUB, 401, "Bad credentials")
        assert error.code == 401
        assert error.recoverable is True
        assert error.suggested_action == RecoveryAction.ROTATE_TOKEN

    def test_classify_403_forbidden(self):
        """403 errors (rate limit) should wait and retry."""
        error = create_api_error(APISource.GITHUB, 403, "API rate limit exceeded")
        assert error.code == 403
        assert error.suggested_action == RecoveryAction.WAIT_AND_RETRY

    def test_classify_404_not_found(self):
        """404 errors should abort (resource deleted)."""
        error = create_api_error(APISource.GITHUB, 404, "Not Found")
        assert error.code == 404
        assert error.recoverable is False
        assert error.suggested_action == RecoveryAction.ABORT

    def test_classify_409_conflict(self):
        """409 errors should suggest pull and retry."""
        error = create_api_error(APISource.GITHUB, 409, "Merge conflict")
        assert error.code == 409
        assert error.recoverable is True
        assert error.suggested_action == RecoveryAction.PULL_AND_RETRY

    def test_classify_422_validation_failed(self):
        """422 errors should abort (bad request format)."""
        error = create_api_error(APISource.GITHUB, 422, "Validation failed")
        assert error.code == 422
        assert error.recoverable is False
        assert error.suggested_action == RecoveryAction.ABORT

    def test_classify_429_rate_limited(self):
        """429 errors should wait and retry."""
        error = create_api_error(APISource.GITHUB, 429, "Rate limited")
        assert error.code == 429
        assert error.suggested_action == RecoveryAction.WAIT_AND_RETRY


class TestRecoveryActions:
    """Tests for recovery action determination."""

    def test_should_retry_for_recoverable(self):
        """Recoverable errors should return True from should_retry()."""
        error = create_api_error(APISource.CLAUDE, 429, "Rate limited")
        assert error.should_retry() is True

    def test_should_not_retry_for_abort(self):
        """ABORT action should return False from should_retry()."""
        error = create_api_error(APISource.GITHUB, 404, "Not found")
        assert error.suggested_action == RecoveryAction.ABORT
        assert error.should_retry() is False

    def test_should_not_retry_for_manual_review(self):
        """MANUAL_REVIEW action should return False from should_retry()."""
        error = create_api_error(APISource.CLAUDE, 400, "Content filtered")
        assert error.suggested_action == RecoveryAction.MANUAL_REVIEW
        assert error.should_retry() is False

    def test_should_retry_for_rotate_token(self):
        """ROTATE_TOKEN action should return True from should_retry()."""
        error = create_api_error(APISource.CLAUDE, 401, "Invalid key")
        assert error.suggested_action == RecoveryAction.ROTATE_TOKEN
        assert error.should_retry() is True

    def test_should_retry_for_pull_and_retry(self):
        """PULL_AND_RETRY action should return True from should_retry()."""
        error = create_api_error(APISource.GITHUB, 409, "Conflict")
        assert error.suggested_action == RecoveryAction.PULL_AND_RETRY
        assert error.should_retry() is True


class TestRetryDelay:
    """Tests for retry delay calculations."""

    def test_exponential_backoff(self):
        """Retry delay should increase exponentially."""
        error = create_api_error(APISource.CLAUDE, 429, "Rate limited")

        delay0 = get_retry_delay(error, 0)
        delay1 = get_retry_delay(error, 1)
        delay2 = get_retry_delay(error, 2)

        # Base delay of 60, so expect 60, 120, 240
        assert delay0 == 60  # base * 2^0
        assert delay1 == 120  # base * 2^1
        assert delay2 == 240  # base * 2^2

    def test_respects_retry_after_header(self):
        """Delay should respect retry_after_seconds minimum."""
        error = create_api_error(APISource.CLAUDE, 429, "Rate limited")
        # Error has retry_after_seconds=60
        delay = get_retry_delay(error, 0)
        assert delay >= 60

    def test_max_delay_capped(self):
        """Delay should be capped at reasonable maximum."""
        error = create_api_error(APISource.CLAUDE, 429, "Rate limited")
        # High attempt number would exceed cap
        delay = get_retry_delay(error, 10)
        assert delay <= MAX_RETRY_DELAY_SECONDS

    def test_minimum_base_delay(self):
        """Minimum base delay should be 5 seconds."""
        # Create error with retry_after_seconds=0
        error = APIError(
            source=APISource.GITHUB,
            code=500,
            message="Server error",
            recoverable=True,
            suggested_action=RecoveryAction.WAIT_AND_RETRY,
            retry_after_seconds=0,
        )
        delay = get_retry_delay(error, 0)
        assert delay >= 5  # Minimum base delay


class TestRateLimitDetection:
    """Tests for rate limit detection."""

    def test_is_rate_limit_429(self):
        """429 status code should be detected as rate limit."""
        error = create_api_error(APISource.CLAUDE, 429, "Rate limited")
        assert is_rate_limit(error) is True

    def test_is_rate_limit_message(self):
        """Rate limit keywords in message should be detected."""
        error = APIError(
            source=APISource.GITHUB,
            code=403,
            message="API rate limit exceeded",
            recoverable=True,
            suggested_action=RecoveryAction.WAIT_AND_RETRY,
            retry_after_seconds=60,
            raw_error="API rate limit exceeded for user",
        )
        assert is_rate_limit(error) is True

    def test_not_rate_limit_for_other_errors(self):
        """Non-rate-limit errors should return False."""
        error = create_api_error(APISource.CLAUDE, 400, "Bad request")
        assert is_rate_limit(error) is False

    def test_rate_limit_keyword_quota(self):
        """'quota' keyword should be detected as rate limit."""
        error = APIError(
            source=APISource.CLAUDE,
            code=403,
            message="Quota exceeded",
            recoverable=True,
            suggested_action=RecoveryAction.WAIT_AND_RETRY,
            raw_error="Usage quota exceeded",
        )
        assert is_rate_limit(error) is True


class TestErrorCreation:
    """Tests for error factory function."""

    def test_create_known_error(self):
        """Known error codes should get proper classification."""
        error = create_api_error(APISource.CLAUDE, 429, "Rate limited")
        assert error.message == "Rate limited"
        assert error.recoverable is True

    def test_create_unknown_error(self):
        """Unknown error codes should get sensible defaults."""
        error = create_api_error(APISource.CLAUDE, 418, "I'm a teapot")
        # Unknown client error - should not be recoverable
        assert error.recoverable is False
        assert "Unknown error" in error.message

    def test_create_unknown_server_error(self):
        """Unknown 5xx errors should be treated as recoverable."""
        error = create_api_error(APISource.GITHUB, 599, "Unknown server error")
        # 5xx errors should be recoverable by default
        assert error.recoverable is True

    def test_raw_error_preserved(self):
        """Original error string should be preserved."""
        raw = "Original error message with details"
        error = create_api_error(APISource.CLAUDE, 500, raw)
        assert error.raw_error == raw

    def test_error_to_dict(self):
        """Error should serialize to dict properly."""
        error = create_api_error(APISource.GITHUB, 404, "Not found")
        d = error.to_dict()
        assert d['source'] == 'github'
        assert d['code'] == 404
        assert d['recoverable'] is False


class TestClassifyFromException:
    """Tests for exception-to-error classification."""

    def test_classify_exception_with_status_code(self):
        """Exception with status_code attribute should be classified."""
        exc = Exception("Rate limited")
        exc.status_code = 429
        error = classify_from_exception(APISource.CLAUDE, exc)
        assert error.code == 429

    def test_classify_exception_parse_message(self):
        """Exception message with status code should be parsed."""
        exc = Exception("Request failed with HTTP 401")
        error = classify_from_exception(APISource.CLAUDE, exc)
        assert error.code == 401

    def test_classify_exception_keywords_rate_limit(self):
        """Rate limit keywords in message should be detected."""
        exc = Exception("Too many requests, please slow down")
        error = classify_from_exception(APISource.GITHUB, exc)
        assert error.code == 429

    def test_classify_exception_keywords_auth(self):
        """Authentication keywords should map to 401."""
        exc = Exception("Unauthorized access denied")
        error = classify_from_exception(APISource.CLAUDE, exc)
        assert error.code == 401

    def test_classify_exception_fallback(self):
        """Unknown exceptions should fallback to 500."""
        exc = Exception("Something unexpected happened")
        error = classify_from_exception(APISource.GITHUB, exc)
        assert error.code == 500


class TestGitHubAPIError:
    """Tests for GitHubAPIError exception class."""

    def test_github_api_error_creation(self):
        """GitHubAPIError should store all attributes."""
        error = GitHubAPIError(
            status_code=404,
            message="Not found",
            recoverable=False,
            action="abort",
            raw_output="gh: Not found"
        )
        assert error.status_code == 404
        assert error.message == "Not found"
        assert error.recoverable is False
        assert error.action == "abort"
        assert error.raw_output == "gh: Not found"

    def test_github_api_error_str(self):
        """GitHubAPIError should have informative string representation."""
        error = GitHubAPIError(
            status_code=429,
            message="Rate limited",
            recoverable=True,
            action="wait_retry"
        )
        assert "429" in str(error)
        assert "Rate limited" in str(error)

    def test_github_api_error_to_api_error(self):
        """GitHubAPIError.to_api_error() should create APIError."""
        gh_error = GitHubAPIError(
            status_code=401,
            message="Unauthorized",
            recoverable=True,
            action="rotate_token",
            raw_output="gh: authentication failed"
        )
        api_error = gh_error.to_api_error()
        assert api_error.source == APISource.GITHUB
        assert api_error.code == 401

    def test_github_api_error_to_dict(self):
        """GitHubAPIError.to_dict() should serialize properly."""
        error = GitHubAPIError(
            status_code=403,
            message="Forbidden",
            recoverable=False,
            action="abort"
        )
        d = error.to_dict()
        assert d['status_code'] == 403
        assert d['message'] == "Forbidden"
        assert d['recoverable'] is False
        assert d['action'] == "abort"


class TestExecuteGhCommand:
    """Tests for execute_gh_command wrapper."""

    @patch('github_cache.subprocess.run')
    def test_successful_command(self, mock_run):
        """Successful command should return success tuple."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"issues": []}',
            stderr=''
        )

        success, stdout, stderr = execute_gh_command(
            cmd=['gh', 'issue', 'list'],
            cwd=Path('.'),
            timeout=30
        )

        assert success is True
        assert stdout == '{"issues": []}'
        assert stderr == ''

    @patch('github_cache.subprocess.run')
    def test_401_error_classification(self, mock_run):
        """401 error should raise GitHubAPIError with rotate_token action."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout='',
            stderr='HTTP 401: authentication required'
        )

        with pytest.raises(GitHubAPIError) as exc_info:
            execute_gh_command(
                cmd=['gh', 'issue', 'list'],
                cwd=Path('.'),
                timeout=30
            )

        error = exc_info.value
        assert error.status_code == 401
        assert error.action == "rotate_token"

    @patch('github_cache.subprocess.run')
    def test_rate_limit_error_classification(self, mock_run):
        """Rate limit error should be classified with wait_retry action."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout='',
            stderr='API rate limit exceeded'
        )

        with pytest.raises(GitHubAPIError) as exc_info:
            execute_gh_command(
                cmd=['gh', 'issue', 'list'],
                cwd=Path('.'),
                timeout=30
            )

        error = exc_info.value
        assert error.status_code == 429
        assert error.action == "wait_retry"
        assert error.recoverable is True

    @patch('github_cache.subprocess.run')
    def test_404_error_classification(self, mock_run):
        """404 error should be non-recoverable abort."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout='',
            stderr='could not find issue #999'
        )

        with pytest.raises(GitHubAPIError) as exc_info:
            execute_gh_command(
                cmd=['gh', 'issue', 'view', '999'],
                cwd=Path('.'),
                timeout=30
            )

        error = exc_info.value
        assert error.status_code == 404
        assert error.recoverable is False

    @patch('github_cache.subprocess.run')
    def test_timeout_error(self, mock_run):
        """Timeout should raise GitHubAPIError with recoverable status."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=['gh'], timeout=30)

        with pytest.raises(GitHubAPIError) as exc_info:
            execute_gh_command(
                cmd=['gh', 'issue', 'list'],
                cwd=Path('.'),
                timeout=30
            )

        error = exc_info.value
        assert error.status_code == 504
        assert error.recoverable is True

    @patch('github_cache.subprocess.run')
    def test_conflict_error_classification(self, mock_run):
        """409 conflict should suggest pull_retry action."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout='',
            stderr='409 conflict: reference already exists'
        )

        with pytest.raises(GitHubAPIError) as exc_info:
            execute_gh_command(
                cmd=['gh', 'pr', 'create'],
                cwd=Path('.'),
                timeout=30
            )

        error = exc_info.value
        assert error.status_code == 409
        assert error.action == "pull_retry"
