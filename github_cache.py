"""
GitHub API Caching Layer
========================

Intelligent caching system to reduce GitHub API calls.

Key Features:
- Issue descriptions cached (immutable data)
- Session-level status cache (invalidated on updates)
- Rate limit tracking (5000/hour for authenticated requests)
- Parse gh CLI JSON output for caching
- Error classification for GitHub API failures (T045-T050)
"""

import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from github_config import GITHUB_RATE_LIMIT_HOURLY, GITHUB_RATE_LIMIT_WARNING_THRESHOLD
from api_error_handler import (
    APISource, RecoveryAction, APIError,
    create_api_error, is_rate_limit,
)


# =============================================================================
# GITHUB API ERROR HANDLING (T045-T050)
# =============================================================================

class GitHubAPIError(Exception):
    """
    Exception for classified GitHub API errors (T045).

    Provides structured error information for recovery handling.
    """

    def __init__(
        self,
        status_code: int,
        message: str,
        recoverable: bool = False,
        action: str = "abort",
        raw_output: str = ""
    ):
        self.status_code = status_code
        self.message = message
        self.recoverable = recoverable
        self.action = action
        self.raw_output = raw_output
        super().__init__(f"GitHub API {status_code}: {message}")

    def to_api_error(self) -> APIError:
        """Convert to standard APIError for unified handling."""
        return create_api_error(APISource.GITHUB, self.status_code, self.raw_output)

    def to_dict(self) -> dict:
        """Serialize for logging."""
        return {
            "status_code": self.status_code,
            "message": self.message,
            "recoverable": self.recoverable,
            "action": self.action,
        }


def execute_gh_command(
    cmd: List[str],
    cwd: Path,
    timeout: int = 60,
    logger: logging.Logger = None
) -> Tuple[bool, str, str]:
    """
    Execute gh CLI command with error classification (T046).

    Wraps subprocess.run with comprehensive error detection and classification
    based on exit codes and stderr content.

    Args:
        cmd: Command list (e.g., ['gh', 'issue', 'list', ...])
        cwd: Working directory
        timeout: Command timeout in seconds
        logger: Optional logger for error details

    Returns:
        Tuple of (success: bool, stdout: str, stderr: str)

    Raises:
        GitHubAPIError: If command fails with classifiable error
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout
        )

        if result.returncode == 0:
            return True, result.stdout, result.stderr

        # T047: Classify error based on stderr content
        stderr_lower = result.stderr.lower()
        stdout_lower = result.stdout.lower()
        combined = stderr_lower + stdout_lower

        # Determine status code and classification
        status_code = 0
        message = "Unknown error"
        recoverable = False
        action = "abort"

        # 401 - Authentication failed
        if '401' in combined or 'unauthorized' in combined or 'authentication' in combined:
            status_code = 401
            message = "Authentication failed - run 'gh auth status' to check credentials"
            recoverable = True
            action = "rotate_token"

        # 403 - Forbidden (rate limit or permissions)
        elif '403' in combined or 'forbidden' in combined:
            if 'rate limit' in combined or 'rate_limit' in combined:
                status_code = 429  # Treat as rate limit
                message = "Rate limited"
                recoverable = True
                action = "wait_retry"
            else:
                status_code = 403
                message = "Permission denied - check repository access"
                recoverable = False
                action = "abort"

        # 404 - Not found
        elif '404' in combined or 'not found' in combined or 'could not find' in combined:
            status_code = 404
            message = "Resource not found - may have been deleted"
            recoverable = False
            action = "abort"

        # 409 - Conflict
        elif '409' in combined or 'conflict' in combined:
            status_code = 409
            message = "Conflict - may need to pull latest changes"
            recoverable = True
            action = "pull_retry"

        # 422 - Validation failed
        elif '422' in combined or 'validation' in combined or 'invalid' in combined:
            status_code = 422
            message = "Validation failed - check request format"
            recoverable = False
            action = "abort"

        # 429 - Rate limited
        elif '429' in combined or 'rate limit' in combined or 'too many requests' in combined:
            status_code = 429
            message = "Rate limited - wait before retrying"
            recoverable = True
            action = "wait_retry"

        # 5xx - Server errors
        elif '500' in combined or '502' in combined or '503' in combined or 'server error' in combined:
            status_code = 500
            message = "GitHub server error - retry later"
            recoverable = True
            action = "wait_retry"

        # Timeout
        elif 'timeout' in combined or 'timed out' in combined:
            status_code = 504
            message = "Request timed out"
            recoverable = True
            action = "wait_retry"

        # Generic error
        else:
            status_code = result.returncode if result.returncode > 0 else 500
            message = result.stderr.strip()[:200] if result.stderr else "Command failed"
            recoverable = False
            action = "abort"

        # T050: Log error with classification
        if logger:
            logger.warning(
                f"GitHub API error: {status_code} - {message}",
                extra={
                    'cmd': ' '.join(cmd),
                    'status_code': status_code,
                    'recoverable': recoverable,
                    'action': action,
                }
            )

        raise GitHubAPIError(
            status_code=status_code,
            message=message,
            recoverable=recoverable,
            action=action,
            raw_output=result.stderr or result.stdout
        )

    except subprocess.TimeoutExpired:
        if logger:
            logger.error(f"Command timed out after {timeout}s: {' '.join(cmd)}")
        raise GitHubAPIError(
            status_code=504,
            message=f"Command timed out after {timeout}s",
            recoverable=True,
            action="wait_retry",
            raw_output=""
        )

    except GitHubAPIError:
        raise  # Re-raise classified errors

    except Exception as e:
        if logger:
            logger.error(f"Unexpected error executing gh command: {e}")
        raise GitHubAPIError(
            status_code=500,
            message=str(e),
            recoverable=False,
            action="abort",
            raw_output=str(e)
        )


# =============================================================================
# GITHUB CACHE CLASS
# =============================================================================


class GitHubCache:
    """
    Smart caching layer for GitHub API operations via gh CLI.

    Caching Strategy:
    1. PERMANENT: Issue descriptions (never change after creation)
    2. SESSION: Issue statuses (invalidated on updates)
    3. SHORT-TERM: Project/repo metadata (5min TTL)
    """

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.cache_file = project_dir / ".github_cache.json"
        self.session_cache: Dict[str, Any] = {}
        self.api_call_count = 0
        self.api_call_timestamps: List[float] = []
        self.load_cache()

    def load_cache(self):
        """Load persistent cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.permanent_cache = data.get('permanent', {})
                    self.metadata_cache = data.get('metadata', {})
                    print(f"Loaded cache with {len(self.permanent_cache.get('issues', {}))} cached issues")
            except Exception as e:
                print(f"Failed to load cache: {e}")
                self.permanent_cache = {'issues': {}}
                self.metadata_cache = {}
        else:
            self.permanent_cache = {'issues': {}}
            self.metadata_cache = {}

    def save_cache(self):
        """Save persistent cache to disk."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'permanent': self.permanent_cache,
                    'metadata': self.metadata_cache,
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            print(f"Failed to save cache: {e}")

    def track_api_call(self):
        """Track API calls for rate limit monitoring."""
        now = time.time()
        self.api_call_count += 1
        self.api_call_timestamps.append(now)

        # Clean up old timestamps (older than 1 hour)
        one_hour_ago = now - 3600
        self.api_call_timestamps = [t for t in self.api_call_timestamps if t > one_hour_ago]

        # Warn if approaching rate limit
        warning_threshold = int(GITHUB_RATE_LIMIT_HOURLY * GITHUB_RATE_LIMIT_WARNING_THRESHOLD)
        if len(self.api_call_timestamps) > warning_threshold:
            print(f"WARNING: {len(self.api_call_timestamps)} API calls in last hour (limit: {GITHUB_RATE_LIMIT_HOURLY})")

        return len(self.api_call_timestamps)

    def get_cached_issue(self, issue_number: int) -> Optional[Dict]:
        """
        Get cached issue data.
        Returns full issue data if available, None otherwise.
        """
        return self.permanent_cache['issues'].get(str(issue_number))

    def cache_issue(self, issue_number: int, issue_data: Dict):
        """
        Cache issue data permanently.
        Only caches immutable fields (body, title).
        """
        issue_key = str(issue_number)
        if issue_key not in self.permanent_cache['issues']:
            self.permanent_cache['issues'][issue_key] = {
                'number': issue_number,
                'title': issue_data.get('title'),
                'body': issue_data.get('body'),
                'labels': issue_data.get('labels', []),
                'cached_at': datetime.now().isoformat()
            }
            self.save_cache()

    def get_session_issues(self, repo: str) -> Optional[List[Dict]]:
        """
        Get all issues for a repo from session cache.
        This cache is invalidated when any issue is updated.
        """
        cache_key = f"issues_{repo}"
        cached_data = self.session_cache.get(cache_key)

        if cached_data:
            # Check if cache is still fresh (< 5 minutes)
            cached_time = cached_data.get('timestamp', 0)
            if time.time() - cached_time < 300:  # 5 minutes
                print(f"Using cached issue list ({len(cached_data['issues'])} issues)")
                return cached_data['issues']

        return None

    def cache_session_issues(self, repo: str, issues: List[Dict]):
        """Cache issue list for current session."""
        cache_key = f"issues_{repo}"
        self.session_cache[cache_key] = {
            'issues': issues,
            'timestamp': time.time()
        }

        # Also cache individual issue descriptions
        for issue in issues:
            if issue.get('number'):
                self.cache_issue(issue['number'], issue)

    def invalidate_session_cache(self, repo: str):
        """Invalidate session cache after updates."""
        cache_key = f"issues_{repo}"
        if cache_key in self.session_cache:
            del self.session_cache[cache_key]
            print("Session cache invalidated")

    def get_cached_project(self, project_number: int) -> Optional[Dict]:
        """Get cached project metadata."""
        return self.metadata_cache.get(f"project_{project_number}")

    def cache_project(self, project_number: int, project_data: Dict):
        """Cache project metadata with TTL tracking."""
        self.metadata_cache[f"project_{project_number}"] = {
            **project_data,
            'cached_at': time.time()
        }
        self.save_cache()

    def get_api_stats(self) -> Dict:
        """Get API usage statistics."""
        calls_last_hour = len(self.api_call_timestamps)
        return {
            'total_calls_session': self.api_call_count,
            'calls_last_hour': calls_last_hour,
            'rate_limit': GITHUB_RATE_LIMIT_HOURLY,
            'percentage_used': (calls_last_hour / GITHUB_RATE_LIMIT_HOURLY) * 100,
            'cached_issues': len(self.permanent_cache['issues'])
        }


class CachedGitHubClient:
    """
    Wrapper for GitHub CLI operations with intelligent caching.

    Usage:
        cache = GitHubCache(project_dir)
        client = CachedGitHubClient(cache)

        # Check cache before running gh commands
        if not cache.get_session_issues(repo):
            # Run gh issue list and cache results
            pass
    """

    def __init__(self, cache: GitHubCache):
        self.cache = cache

    def should_fetch_issues(self, repo: str) -> bool:
        """Check if we need to fetch issues from GitHub."""
        cached = self.cache.get_session_issues(repo)
        if cached is not None:
            return False
        return True

    def cache_issues_from_gh_output(self, repo: str, gh_json_output: str):
        """
        Parse gh CLI JSON output and cache issues.

        Expected format from: gh issue list --json number,title,body,labels,state --limit 10000

        IMPORTANT: Always use --limit 10000 (or higher) when fetching issues to cache,
        as the default limit of 30 will miss issues in larger projects.
        """
        try:
            issues = json.loads(gh_json_output)
            self.cache.cache_session_issues(repo, issues)
            self.cache.track_api_call()
            return issues
        except json.JSONDecodeError as e:
            print(f"Failed to parse gh output: {e}")
            return []

    def get_cached_issue_body(self, issue_number: int) -> Optional[str]:
        """Get cached issue body to avoid re-fetching."""
        cached = self.cache.get_cached_issue(issue_number)
        if cached:
            return cached.get('body')
        return None

    def on_issue_updated(self, repo: str):
        """Call this after updating an issue to invalidate cache."""
        self.cache.invalidate_session_cache(repo)
        self.cache.track_api_call()


def create_cached_github_helper(project_dir: Path) -> GitHubCache:
    """
    Factory function to create GitHubCache instance.

    Usage in agent code:
        cache = create_cached_github_helper(project_dir)
        stats = cache.get_api_stats()
        print(f"API calls this hour: {stats['calls_last_hour']}/{GITHUB_RATE_LIMIT_HOURLY}")
    """
    return GitHubCache(project_dir)
