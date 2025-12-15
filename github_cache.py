"""
GitHub API Caching Layer
========================

Intelligent caching system to reduce GitHub API calls.

Key Features:
- Issue descriptions cached (immutable data)
- Session-level status cache (invalidated on updates)
- Rate limit tracking (5000/hour for authenticated requests)
- Parse gh CLI JSON output for caching
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from github_config import GITHUB_RATE_LIMIT_HOURLY, GITHUB_RATE_LIMIT_WARNING_THRESHOLD


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
