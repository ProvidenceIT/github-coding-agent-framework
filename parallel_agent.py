#!/usr/bin/env python3
"""
Parallel Autonomous Agent (Enhanced)
=====================================

Runs multiple agent sessions concurrently for faster throughput.
Each session claims a unique issue and works on it independently.

Features:
- Atomic issue claiming to prevent conflicts
- Windows and Unix compatible file locking
- Serialized git push operations
- Session isolation (no os.chdir)
- Session health monitoring (ported from autonomous_agent_fixed.py)
- Outcome validation
- Comprehensive logging
- Retry mechanism for unhealthy sessions
- Constitution support for project governance

Usage:
    python parallel_agent.py --project-dir ./generations/my_project --concurrent 3
    python parallel_agent.py --project-dir ./generations/my_project --concurrent 2 --iterations 5
"""

import asyncio
import argparse
import json
import os
import sys
import subprocess
import time
import re
import traceback
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
import logging

# Windows console UTF-8 fix
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
from github_config import (
    get_repo_info, save_repo_info, DEFAULT_GITHUB_ORG, GITHUB_ISSUE_LIST_LIMIT,
    MAX_NO_ISSUES_ROUNDS, CLAIM_TTL_MINUTES, FAILURE_DEPRIORITIZE_THRESHOLD,
)
from prompts import set_project_context, copy_spec_to_project, get_constitution
from token_rotator import TokenRotator, get_rotator, set_rotator
from api_error_handler import (
    APISource, RecoveryAction, APIError,
    classify_from_exception, get_retry_delay, is_rate_limit,
)
from github_cache import GitHubAPIError, execute_gh_command
from github_projects import GitHubProjectsManager, create_projects_manager


# =============================================================================
# BACKLOG STATE (Agent Reliability Feature)
# =============================================================================

@dataclass
class BacklogState:
    """
    Tracks empty backlog rounds for graceful termination.

    Used to detect when all issues are complete and the agent should stop.
    """
    consecutive_no_issues: int = 0       # Rounds with no work
    threshold: int = MAX_NO_ISSUES_ROUNDS  # Rounds before termination
    last_check: Optional[datetime] = None

    def record_round(self, session_results: List[str]) -> bool:
        """
        Record round results and check if should terminate.

        Args:
            session_results: List of session result strings

        Returns:
            True if agent should stop (threshold reached)
        """
        self.last_check = datetime.now()

        all_no_issues = all(
            "No unclaimed issues" in result or "NO_ISSUES" in result
            for result in session_results
        )

        if all_no_issues:
            self.consecutive_no_issues += 1
            return self.consecutive_no_issues >= self.threshold
        else:
            self.consecutive_no_issues = 0
            return False

    def should_terminate(self) -> bool:
        """Check if termination threshold reached."""
        return self.consecutive_no_issues >= self.threshold

    def reset(self) -> None:
        """Reset counter (called when new issues appear)."""
        self.consecutive_no_issues = 0


# =============================================================================
# CROSS-PLATFORM FILE LOCKING
# =============================================================================

class FileLock:
    """
    Cross-platform file locking for Windows and Unix.
    Uses msvcrt on Windows, fcntl on Unix.
    """

    def __init__(self, lock_file: Path):
        self.lock_file = lock_file
        self._file = None

    def acquire(self):
        """Acquire exclusive lock on file."""
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self.lock_file, 'w')

        if sys.platform == 'win32':
            import msvcrt
            msvcrt.locking(self._file.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(self._file.fileno(), fcntl.LOCK_EX)

    def release(self):
        """Release lock on file."""
        if self._file:
            if sys.platform == 'win32':
                import msvcrt
                try:
                    msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
                except Exception:
                    pass
            else:
                import fcntl
                fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)

            self._file.close()
            self._file = None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args):
        self.release()


class AsyncFileLock:
    """Async wrapper around FileLock for use with asyncio."""

    def __init__(self, lock_file: Path):
        self.lock_file = lock_file
        self._lock = asyncio.Lock()
        self._file_lock = FileLock(lock_file)

    async def __aenter__(self):
        await self._lock.acquire()
        self._file_lock.acquire()
        return self

    async def __aexit__(self, *args):
        self._file_lock.release()
        self._lock.release()


# =============================================================================
# ISSUE LOCK MANAGER (Enhanced with TTL and Failure Tracking)
# =============================================================================

class IssueLockManager:
    """
    Manages atomic issue claiming to prevent multiple sessions
    from working on the same issue.

    Enhanced features (Agent Reliability):
    - TTL-based claim expiration (30 minute default)
    - Stale claim cleanup before claiming
    - Failure tracking with deprioritization
    """

    # Configuration constants (imported from github_config)
    CLAIM_TTL_MINUTES = CLAIM_TTL_MINUTES
    FAILURE_DEPRIORITIZE_THRESHOLD = FAILURE_DEPRIORITIZE_THRESHOLD

    def __init__(self, project_dir: Path, repo: str, logger: logging.Logger = None):
        self.project_dir = project_dir
        self.repo = repo
        self.claims_file = project_dir / ".issue_claims.json"
        self.lock = FileLock(project_dir / ".issue_claims.lock")
        self.logger = logger

    def _log(self, message: str, level: str = "info"):
        """Log message if logger available."""
        if self.logger:
            getattr(self.logger, level)(message, extra={'session_id': 'claim_manager'})
        else:
            print(f"[ClaimManager] {message}")

    def _load_claims(self) -> Dict[str, Dict]:
        """Load current issue claims."""
        if self.claims_file.exists():
            try:
                return json.loads(self.claims_file.read_text(encoding='utf-8'))
            except Exception:
                pass
        return {}

    def _save_claims(self, claims: Dict[str, Dict]):
        """Save issue claims."""
        self.claims_file.write_text(
            json.dumps(claims, indent=2),
            encoding='utf-8'
        )

    def _cleanup_stale_claims(self, claims: Dict[str, Dict]) -> Tuple[Dict[str, Dict], List[int]]:
        """
        Remove claims older than TTL (T012).

        Args:
            claims: Current claims dictionary

        Returns:
            Tuple of (cleaned claims dict, list of cleaned issue numbers)
        """
        now = datetime.now()
        ttl = timedelta(minutes=self.CLAIM_TTL_MINUTES)

        stale_keys = []
        for key, data in claims.items():
            claimed_at_str = data.get('claimed_at')
            if not claimed_at_str:
                continue

            try:
                claimed_at = datetime.fromisoformat(claimed_at_str)
                age = now - claimed_at

                # Check if claim has TTL override (expires_at field)
                expires_at_str = data.get('expires_at')
                if expires_at_str:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if now >= expires_at:
                        stale_keys.append(key)
                        self._log(f"Cleaning stale claim: #{key} (expired at {expires_at})")
                elif age > ttl:
                    stale_keys.append(key)
                    self._log(f"Cleaning stale claim: #{key} (age: {age.total_seconds()/60:.1f} min > TTL {self.CLAIM_TTL_MINUTES} min)")
            except (ValueError, TypeError) as e:
                # Invalid timestamp, treat as stale
                stale_keys.append(key)
                self._log(f"Cleaning claim #{key} with invalid timestamp: {e}", "warning")

        cleaned_issues = []
        for key in stale_keys:
            cleaned_issues.append(int(key))
            del claims[key]

        if stale_keys:
            self._save_claims(claims)
            self._log(f"Cleaned {len(stale_keys)} stale claim(s): {cleaned_issues}")

        return claims, cleaned_issues

    def _get_open_issues(self) -> List[Dict]:
        """
        Get open issues from GitHub, sorted by priority (T048).

        Uses execute_gh_command() for classified error handling.
        """
        try:
            cmd = [
                'gh', 'issue', 'list', '--repo', self.repo,
                '--state', 'open', '--json', 'number,title,labels',
                '--limit', str(GITHUB_ISSUE_LIST_LIMIT)
            ]

            success, stdout, stderr = execute_gh_command(
                cmd=cmd,
                cwd=self.project_dir,
                timeout=60,
                logger=self.logger
            )

            if not success:
                self._log(f"Failed to get issues: {stderr}", "error")
                return []

            issues = json.loads(stdout)

            # Sort by priority
            def priority_key(issue):
                labels = [l.get('name', '') for l in issue.get('labels', [])]
                if 'priority:urgent' in labels:
                    return 0
                elif 'priority:high' in labels:
                    return 1
                elif 'priority:medium' in labels:
                    return 2
                elif 'priority:low' in labels:
                    return 3
                return 4

            return sorted(issues, key=priority_key)

        except GitHubAPIError as e:
            # Classified error - log with details
            self._log(
                f"GitHub API error getting issues: {e.status_code} - {e.message}",
                "error"
            )
            return []
        except json.JSONDecodeError as e:
            self._log(f"Failed to parse issues JSON: {e}", "error")
            return []
        except Exception as e:
            self._log(f"Error getting issues: {e}", "error")
            return []

    def _is_deprioritized(self, claims: Dict[str, Dict], issue_num: int) -> bool:
        """
        Check if an issue should be deprioritized due to failures (T017).

        Args:
            claims: Current claims dictionary
            issue_num: Issue number to check

        Returns:
            True if issue has too many failures
        """
        key = str(issue_num)
        if key not in claims:
            return False

        failure_count = claims[key].get('failure_count', 0)
        return failure_count >= self.FAILURE_DEPRIORITIZE_THRESHOLD

    def claim_issue(self, session_id: str) -> Optional[int]:
        """
        Atomically claim the next available issue (T013).

        Steps:
        1. Acquire file lock
        2. Cleanup stale claims (TTL expired)
        3. Get open issues from GitHub
        4. Filter out claimed and META issues
        5. Sort by priority (deprioritize high-failure issues)
        6. Claim first available
        7. Save claims and release lock

        Returns:
            Issue number if claimed, None if no issues available
        """
        with self.lock:
            claims = self._load_claims()

            # T013: Cleanup stale claims before querying GitHub
            claims, cleaned = self._cleanup_stale_claims(claims)

            issues = self._get_open_issues()

            # Build list of available issues with priority adjustment
            available_issues = []
            for issue in issues:
                num = issue['number']
                title = issue.get('title', '')

                # Skip META issue
                if '[META]' in title.upper():
                    continue

                # Skip actively claimed (not stale, not failed)
                key = str(num)
                if key in claims:
                    claim_status = claims[key].get('status', 'claimed')
                    # Only skip if actively claimed (not failed/released)
                    if claim_status == 'claimed':
                        continue

                # T017: Deprioritize issues with high failure count
                is_deprioritized = self._is_deprioritized(claims, num)
                available_issues.append({
                    'issue': issue,
                    'deprioritized': is_deprioritized
                })

            # Sort: non-deprioritized first, then by original priority order
            available_issues.sort(key=lambda x: (x['deprioritized'], 0))

            # Claim first available
            for item in available_issues:
                issue = item['issue']
                num = issue['number']
                title = issue.get('title', '')

                # Calculate expiration time
                now = datetime.now()
                expires_at = now + timedelta(minutes=self.CLAIM_TTL_MINUTES)

                # T014: Add failure tracking fields
                claims[str(num)] = {
                    'session_id': session_id,
                    'claimed_at': now.isoformat(),
                    'expires_at': expires_at.isoformat(),
                    'title': title,
                    'status': 'claimed',
                    'failure_count': claims.get(str(num), {}).get('failure_count', 0),
                    'failed_at': claims.get(str(num), {}).get('failed_at'),
                    'failure_reasons': claims.get(str(num), {}).get('failure_reasons', []),
                }
                self._save_claims(claims)

                self._log(f"Claimed issue #{num}: {title[:50]}...")

                # Post claim comment on GitHub (T049)
                try:
                    cmd = [
                        'gh', 'issue', 'comment', str(num),
                        '--repo', self.repo,
                        '--body', f'🤖 **Claimed by parallel session:** `{session_id}`'
                    ]
                    execute_gh_command(
                        cmd=cmd,
                        cwd=self.project_dir,
                        timeout=30,
                        logger=self.logger
                    )
                except GitHubAPIError as e:
                    # Non-critical - log but don't fail the claim
                    self._log(f"Failed to post claim comment: {e.message}", "warning")
                except Exception:
                    pass

                return num

            return None

    def release_issue(self, issue_num: int, session_id: str, was_closed: bool = False):
        """
        Release claim on an issue (T015).

        Enhanced to handle success vs failure differently:
        - was_closed=True: Issue successfully closed, remove claim entirely
        - was_closed=False: Session ended without closing, track as failure

        Args:
            issue_num: Issue number to release
            session_id: Session releasing the claim
            was_closed: Whether the issue was successfully closed
        """
        with self.lock:
            claims = self._load_claims()
            key = str(issue_num)

            if key not in claims:
                return

            if claims[key].get('session_id') != session_id:
                self._log(f"Cannot release #{issue_num}: claimed by different session", "warning")
                return

            if was_closed:
                # T015: Success - remove claim entirely
                del claims[key]
                self._log(f"Released claim on #{issue_num} (successfully closed)")
            else:
                # T016: Failure - keep claim with failure metadata
                claims[key]['status'] = 'failed'
                claims[key]['failed_at'] = datetime.now().isoformat()
                claims[key]['failure_count'] = claims[key].get('failure_count', 0) + 1
                if 'failure_reasons' not in claims[key]:
                    claims[key]['failure_reasons'] = []
                claims[key]['failure_reasons'].append(f"Session {session_id} did not close issue")

                self._log(
                    f"Marked #{issue_num} as failed (failure_count: {claims[key]['failure_count']})",
                    "warning"
                )

            self._save_claims(claims)

    def mark_failed(self, issue_num: int, session_id: str, reason: str) -> bool:
        """
        Mark issue claim as failed with a specific reason (T016).

        Args:
            issue_num: Issue number
            session_id: Session marking the failure
            reason: Short failure reason (e.g., "content_filter", "timeout")

        Returns:
            True if marked, False if not found or wrong session
        """
        with self.lock:
            claims = self._load_claims()
            key = str(issue_num)

            if key not in claims:
                return False

            if claims[key].get('session_id') != session_id:
                return False

            claims[key]['status'] = 'failed'
            claims[key]['failed_at'] = datetime.now().isoformat()
            claims[key]['failure_count'] = claims[key].get('failure_count', 0) + 1
            if 'failure_reasons' not in claims[key]:
                claims[key]['failure_reasons'] = []
            claims[key]['failure_reasons'].append(reason)

            self._save_claims(claims)

            self._log(
                f"Marked #{issue_num} as failed: {reason} (count: {claims[key]['failure_count']})",
                "warning"
            )

            return True

    def get_active_claims(self) -> Dict[str, Dict]:
        """Get all active (non-expired) claims."""
        with self.lock:
            claims = self._load_claims()
            # Cleanup stale before returning
            claims, _ = self._cleanup_stale_claims(claims)
            return claims

    def get_failure_history(self, issue_num: int) -> Tuple[int, List[str]]:
        """
        Get failure history for an issue.

        Args:
            issue_num: Issue number

        Returns:
            Tuple of (failure_count, failure_reasons)
        """
        with self.lock:
            claims = self._load_claims()
            key = str(issue_num)

            if key not in claims:
                return (0, [])

            return (
                claims[key].get('failure_count', 0),
                claims[key].get('failure_reasons', [])
            )


# =============================================================================
# SESSION HEALTH MONITORING (Ported from autonomous_agent_fixed.py)
# =============================================================================

def calculate_productivity_score(
    tool_count: int,
    files_changed: int = 0,
    issues_closed: int = 0
) -> float:
    """
    Calculate productivity score based on session metrics (T056).

    Formula: (files_changed * 2 + issues_closed * 5) / max(tool_count, 1)

    Args:
        tool_count: Number of tool calls in session
        files_changed: Number of files created or modified
        issues_closed: Number of issues closed

    Returns:
        Productivity score (higher is better, 0.1 is minimum threshold)
    """
    if tool_count <= 0:
        return 0.0

    numerator = (files_changed * 2) + (issues_closed * 5)
    score = numerator / max(tool_count, 1)

    return round(score, 3)


def analyze_session_health(
    response: str,
    session_id: str,
    logger: logging.Logger = None,
    tool_count: int = None,
    files_changed: int = 0,  # T056: Add files_changed parameter
    issues_closed: int = 0    # T056: Add issues_closed parameter
) -> Dict[str, Any]:
    """
    Analyze the session response to detect if the agent is doing meaningful work.

    Enhanced with productivity scoring (T056) to detect sessions that run
    many tools but don't accomplish meaningful work.

    Args:
        response: The text response from the agent
        session_id: Session identifier for logging
        logger: Logger instance
        tool_count: Actual number of tool calls made (from SDK)
        files_changed: Number of files modified this session
        issues_closed: Number of issues closed this session

    Returns:
        dict with health status and metrics including productivity_score
    """
    health_status = {
        'is_healthy': True,
        'warnings': [],
        'tool_calls_count': tool_count or 0,
        'response_length': len(str(response)) if response else 0,
        'has_content': bool(response and str(response).strip()),
        'productivity_score': 0.0,  # T056
        'files_changed': files_changed,
        'issues_closed': issues_closed,
    }

    response_str = str(response) if response else ""

    # Check 1: Empty or near-empty response
    if not response_str or len(response_str.strip()) < 10:
        health_status['is_healthy'] = False
        health_status['warnings'].append("Response is empty or too short (< 10 chars)")
        return health_status

    # Check 2: Count tool usage if not provided
    if tool_count is None:
        tool_patterns = [
            r'<invoke name="(\w+)"',
            r'Tool:\s*(\w+)',
            r'Using tool:\s*(\w+)',
            r'<invoke',
            r'<function_calls>',
        ]
        tool_matches = []
        for pattern in tool_patterns:
            matches = re.findall(pattern, response_str, re.IGNORECASE)
            tool_matches.extend(matches)
        health_status['tool_calls_count'] = len(tool_matches)

    # Check 3: No tool usage detected
    if health_status['tool_calls_count'] == 0:
        health_status['is_healthy'] = False
        health_status['warnings'].append("No tool usage detected - agent may not be doing work")

    # T056: Calculate and check productivity score
    productivity_score = calculate_productivity_score(
        tool_count=health_status['tool_calls_count'],
        files_changed=files_changed,
        issues_closed=issues_closed
    )
    health_status['productivity_score'] = productivity_score

    # T056: Productivity warning check (high tool count but low productivity)
    PRODUCTIVITY_TOOL_THRESHOLD = 30
    PRODUCTIVITY_SCORE_THRESHOLD = 0.1

    if health_status['tool_calls_count'] >= PRODUCTIVITY_TOOL_THRESHOLD and productivity_score < PRODUCTIVITY_SCORE_THRESHOLD:
        health_status['warnings'].append(
            f"Low productivity: {health_status['tool_calls_count']} tool calls but score={productivity_score:.3f} "
            f"(files_changed={files_changed}, issues_closed={issues_closed})"
        )
        if logger:
            logger.warning(
                f"Productivity warning: {health_status['tool_calls_count']} tools, "
                f"score={productivity_score:.3f}, files={files_changed}, issues={issues_closed}"
            )

    # Check 4: Very short response with few tool calls
    if health_status['response_length'] < 200 and health_status['tool_calls_count'] < 2:
        health_status['is_healthy'] = False
        health_status['warnings'].append(
            f"Response too short ({health_status['response_length']} chars) with minimal tool usage"
        )

    # Check 5: Look for error indicators
    error_patterns = [
        r'(?i)error:?\s*unable to',
        r'(?i)failed to',
        r'(?i)permission denied',
        r'(?i)access denied',
    ]
    for pattern in error_patterns:
        if re.search(pattern, response_str):
            health_status['warnings'].append(f"Potential error detected: {pattern}")
            break

    # Check 6: Look for stall indicators
    stall_patterns = [
        r'(?i)i cannot proceed',
        r'(?i)unable to continue',
        r'(?i)nothing (more )?to do',
    ]
    for pattern in stall_patterns:
        if re.search(pattern, response_str):
            health_status['warnings'].append(f"Agent may have stalled: {pattern}")
            break

    # Check 7: Look for rate limit indicators
    rate_limit_patterns = [
        r'(?i)rate.?limit',
        r'(?i)\b429\b',
        r'(?i)too many requests',
        r'(?i)quota.*exceeded',
        r'(?i)exceeded.*quota',
        r'(?i)usage.?limit',
        r'(?i)capacity',
        r'(?i)overloaded',
        r'(?i)approaching.*limit',
        r'(?i)limit.*reached',
    ]

    health_status['rate_limit_detected'] = False
    for pattern in rate_limit_patterns:
        if re.search(pattern, response_str):
            health_status['rate_limit_detected'] = True
            health_status['warnings'].append(f"Rate limit detected in response: {pattern}")
            if logger:
                logger.warning(f"Rate limit indicator detected matching pattern: {pattern}")

            # Trigger token rotation
            try:
                from token_rotator import get_rotator
                rotator = get_rotator()
                old_token = rotator.current_name
                rotator.rotate(reason="rate limit detected in response text")
                if logger:
                    logger.warning(f"Token rotated: {old_token} -> {rotator.current_name}")
                print(f"\n⚠️  Rate limit detected! Switched token: {old_token} -> {rotator.current_name}")
            except Exception as e:
                if logger:
                    logger.error(f"Failed to rotate token after rate limit detection: {e}")
            break

    return health_status


def check_session_outcomes(
    project_dir: Path,
    repo: str,
    logger: logging.Logger = None,
    issues_worked: List[int] = None  # T031: Add issues_worked parameter
) -> Dict[str, Any]:
    """
    Check if session achieved mandatory outcomes (T031-T032).

    Enhanced to check SPECIFIC issues worked on by this session,
    not time-based queries that count other sessions' work.

    Args:
        project_dir: Project directory path
        repo: GitHub repository in owner/name format
        logger: Optional logger instance
        issues_worked: List of issue numbers THIS session worked on (T031)

    Returns:
        dict with outcome status including:
        - issues_worked: List of issues this session worked on
        - issues_closed_list: List of issues successfully closed
        - issues_closed: Count of closed issues
        - success: True if at least one issue closed
    """
    result = {
        'success': False,
        'issues_worked': issues_worked or [],  # T033: Include issues_worked
        'issues_closed': 0,
        'issues_closed_list': [],  # T033: Include list of closed issues
        'meta_updated': False,
        'git_pushed': False,
        'failures': []
    }

    try:
        # T032: Check SPECIFIC issues worked on, not time-based
        # T049: Use execute_gh_command for classified error handling
        if issues_worked:
            for issue_num in issues_worked:
                try:
                    # Check if this specific issue is now closed
                    cmd = [
                        'gh', 'issue', 'view', str(issue_num), '--repo', repo,
                        '--json', 'state', '-q', '.state'
                    ]
                    success, stdout, stderr = execute_gh_command(
                        cmd=cmd,
                        cwd=project_dir,
                        timeout=30,
                        logger=logger
                    )
                    if success and stdout.strip().upper() == 'CLOSED':
                        result['issues_closed'] += 1
                        result['issues_closed_list'].append(issue_num)
                        # T035: Log specific issue closure
                        if logger:
                            logger.info(f"Issue #{issue_num} confirmed closed",
                                       extra={'session_id': 'outcome_check'})
                except GitHubAPIError as e:
                    if logger:
                        logger.warning(
                            f"GitHub API error checking issue #{issue_num}: {e.status_code} - {e.message}",
                            extra={'session_id': 'outcome_check'}
                        )
                except Exception as e:
                    if logger:
                        logger.warning(f"Failed to check issue #{issue_num}: {e}",
                                      extra={'session_id': 'outcome_check'})
        else:
            # Fallback to time-based check if issues_worked not provided
            try:
                cmd = [
                    'gh', 'issue', 'list', '--repo', repo, '--state', 'closed',
                    '--json', 'number,closedAt', '--limit', str(GITHUB_ISSUE_LIST_LIMIT)
                ]
                success, stdout, stderr = execute_gh_command(
                    cmd=cmd,
                    cwd=project_dir,
                    timeout=30,
                    logger=logger
                )

                if success:
                    issues = json.loads(stdout)
                    now = datetime.now()
                    for issue in issues:
                        closed_at = issue.get('closedAt', '')
                        if closed_at:
                            try:
                                closed_time = datetime.fromisoformat(closed_at.replace('Z', '+00:00'))
                                # Check if closed within last hour
                                if (now.timestamp() - closed_time.timestamp()) < 3600:
                                    result['issues_closed'] += 1
                                    result['issues_closed_list'].append(issue['number'])
                            except Exception:
                                pass
            except GitHubAPIError as e:
                if logger:
                    logger.warning(
                        f"GitHub API error listing closed issues: {e.status_code} - {e.message}",
                        extra={'session_id': 'outcome_check'}
                    )

        # T035: Log outcome summary
        if logger:
            logger.info(
                f"Outcome validation: worked={result['issues_worked']}, "
                f"closed={result['issues_closed_list']}",
                extra={'session_id': 'outcome_check'}
            )

        if result['issues_closed'] == 0:
            if issues_worked:
                result['failures'].append(
                    f"Worked on {len(issues_worked)} issue(s) but none closed: {issues_worked}"
                )
            else:
                result['failures'].append("No issues closed in this session")

        # Check git status
        git_status = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=project_dir, capture_output=True, text=True, timeout=30
        )

        if git_status.returncode == 0:
            if not git_status.stdout.strip():
                result['git_pushed'] = True
            else:
                result['failures'].append("Uncommitted changes remain")

        # Overall success
        result['success'] = result['issues_closed'] >= 1 and result['git_pushed']

    except Exception as e:
        result['failures'].append(f"Error checking outcomes: {str(e)}")

    return result


# =============================================================================
# PARALLEL AGENT MANAGER
# =============================================================================

class ParallelAgentManager:
    """
    Manages multiple concurrent agent sessions.

    Each session:
    1. Claims a unique issue atomically
    2. Runs a full coding session on that issue
    3. Commits and pushes changes (serialized)
    4. Releases the issue claim
    """

    def __init__(
        self,
        project_dir: Path,
        max_concurrent: int = 3,
        model: str = "claude-sonnet-4-20250514"
    ):
        self.project_dir = project_dir.resolve()
        self.max_concurrent = max_concurrent
        self.model = model

        # Get repo info
        repo_info = get_repo_info(project_dir)
        self.repo = repo_info.get('repo', '')

        if not self.repo:
            raise ValueError(
                f"No repo info found in {project_dir / '.github_project.json'}. "
                "Run the regular agent first to initialize the project."
            )

        # Set project context for prompts
        set_project_context(
            project_dir=project_dir,
            repo=self.repo,
            repo_url=repo_info.get('repo_url')
        )

        # Setup logging first so we can pass to managers
        self.logger = self._setup_logger()

        # Initialize managers (T019: pass logger for claim logging)
        self.issue_lock = IssueLockManager(project_dir, self.repo, logger=self.logger)
        self.git_lock = AsyncFileLock(project_dir / ".git_push.lock")

        # T066-T067: Initialize GitHub Projects manager for Kanban tracking
        self.projects_manager = create_projects_manager(
            project_dir=project_dir,
            repo=self.repo,
            logger=self.logger
        )
        # Try to get or create project board (non-blocking)
        try:
            self.projects_manager.get_or_create_project()
        except Exception as e:
            self._log("init", f"Projects manager init warning: {e}", "warning")

        # Shared client options
        self.client_options = ClaudeCodeOptions(
            model=model,
            system_prompt=f"You are an expert full-stack developer. Working on repo: {self.repo}. Use --repo {self.repo} with ALL gh commands.",
            allowed_tools=["Read", "Write", "Edit", "Glob", "Grep", "Bash"],
            max_turns=50
        )

    def _setup_logger(self) -> logging.Logger:
        """Setup session logger."""
        log_dir = self.project_dir / "logs"
        log_dir.mkdir(exist_ok=True)

        logger = logging.getLogger(f"parallel_agent_{id(self)}")
        logger.setLevel(logging.INFO)

        # File handler
        log_file = log_dir / f"parallel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(session_id)s] %(message)s'
        ))
        logger.addHandler(fh)

        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter(
            '%(asctime)s - [%(session_id)s] %(message)s'
        ))
        logger.addHandler(ch)

        return logger

    def _log(self, session_id: str, message: str, level: str = "info"):
        """Log with session context."""
        extra = {'session_id': session_id}
        getattr(self.logger, level)(message, extra=extra)

    async def run_parallel(self, num_iterations: int = 1):
        """
        Run multiple parallel iteration rounds with graceful termination (US2).

        Terminates early if all sessions report no issues for MAX_NO_ISSUES_ROUNDS
        consecutive rounds.

        Args:
            num_iterations: Number of rounds of parallel sessions
        """
        print(f"\n{'='*70}")
        print(f"  PARALLEL AUTONOMOUS AGENT")
        print(f"{'='*70}")
        print(f"  Project: {self.project_dir.name}")
        print(f"  Repository: {self.repo}")
        print(f"  Concurrent Sessions: {self.max_concurrent}")
        print(f"  Iterations: {num_iterations}")
        print(f"  Model: {self.model}")
        print(f"{'='*70}\n")

        total_completed = 0
        total_failed = 0

        # T023: Add backlog state tracking for graceful termination
        backlog_state = BacklogState()

        for iteration in range(1, num_iterations + 1):
            print(f"\n{'='*60}")
            print(f"  ITERATION {iteration}/{num_iterations}")
            print(f"  Spawning {self.max_concurrent} concurrent sessions")
            print(f"{'='*60}\n")

            # Create tasks for concurrent execution
            tasks = [
                self._run_single_session(iteration, i)
                for i in range(self.max_concurrent)
            ]

            # Run all sessions concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Report results and collect status strings
            result_strings = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"  Session {i}: FAILED - {result}")
                    total_failed += 1
                    result_strings.append(f"ERROR: {result}")
                else:
                    print(f"  Session {i}: {result}")
                    result_strings.append(str(result))
                    if "Completed" in str(result):
                        total_completed += 1

            # T025: Check for graceful termination (all sessions report no issues)
            should_terminate = backlog_state.record_round(result_strings)

            if should_terminate:
                # T026: Print termination message
                print(f"\n{'='*70}")
                print(f"  ALL ISSUES COMPLETE - Stopping agent")
                print(f"  ({backlog_state.consecutive_no_issues} consecutive rounds with no issues)")
                print(f"{'='*70}\n")
                break

            # T027: Log if some sessions found work (counter was reset)
            if backlog_state.consecutive_no_issues == 0 and any("Completed" in r for r in result_strings):
                self._log("run", f"Work found - backlog state reset")

            # Brief delay between iterations
            if iteration < num_iterations:
                print(f"\n  Waiting 5s before next iteration...")
                await asyncio.sleep(5)

        # Final summary
        print(f"\n{'='*70}")
        print(f"  PARALLEL RUN COMPLETE")
        print(f"{'='*70}")
        print(f"  Total sessions completed: {total_completed}")
        print(f"  Total sessions failed: {total_failed}")
        if backlog_state.should_terminate():
            print(f"  Stopped: All issues complete")
        print(f"{'='*70}\n")

    async def _run_single_session(
        self,
        iteration: int,
        session_num: int,
        retry_attempt: int = 0
    ) -> str:
        """
        Run one isolated agent session with health monitoring and retry.

        Returns:
            Status message describing outcome
        """
        session_id = f"parallel_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{iteration:02d}_{session_num:02d}"
        if retry_attempt > 0:
            session_id += f"_retry{retry_attempt}"

        self._log(session_id, f"Starting session (attempt {retry_attempt + 1})")

        # 1. Claim an issue atomically
        issue_num = self.issue_lock.claim_issue(session_id)
        if not issue_num:
            self._log(session_id, "No unclaimed issues available")
            # T024: Return "NO_ISSUES" for graceful termination detection
            return "NO_ISSUES"

        self._log(session_id, f"Claimed issue #{issue_num}")
        print(f"  [{session_id}] Claimed issue #{issue_num}")

        # T066: Move issue to In Progress on project board
        try:
            self.projects_manager.move_to_in_progress(issue_num)
        except Exception as e:
            self._log(session_id, f"Projects board update warning: {e}", "warning")

        try:
            # 2. Sync token and create fresh client for this session
            try:
                rotator = get_rotator()
                rotator.sync_env()
                token_suffix = rotator.current.value[-5:] if len(rotator.current.value) >= 5 else rotator.current.value
                self._log(session_id, f"Using token: {rotator.current_name} [...{token_suffix}]")
            except Exception as e:
                self._log(session_id, f"Token sync warning: {e}", "warning")

            client = ClaudeSDKClient(options=self.client_options)

            # 3. Generate issue-specific prompt (with constitution if available)
            prompt = self._generate_issue_prompt(issue_num, session_id, retry_attempt > 0)

            # 4. Run session
            self._log(session_id, f"Running agent session for issue #{issue_num}")
            session_start = time.time()

            async with client:
                await client.query(prompt, session_id=session_id)

                messages = []
                tool_count = 0
                response_text = []

                async for msg in client.receive_response():
                    messages.append(msg)

                    # Count tools and extract text
                    if hasattr(msg, 'content') and hasattr(msg.content, '__iter__'):
                        for block in msg.content:
                            if hasattr(block, 'name'):
                                tool_count += 1
                            elif hasattr(block, 'text'):
                                response_text.append(block.text)

            session_duration = time.time() - session_start
            full_response = "\n".join(response_text)

            # 5. Analyze session health
            health_status = analyze_session_health(
                response=full_response,
                session_id=session_id,
                logger=self.logger,
                tool_count=tool_count
            )

            self._log(
                session_id,
                f"Session complete: {tool_count} tools, {len(messages)} messages, "
                f"{health_status['response_length']} chars, {session_duration:.1f}s"
            )

            # Log health warnings
            if not health_status['is_healthy']:
                for warning in health_status['warnings']:
                    self._log(session_id, f"Health warning: {warning}", level="warning")

                # Retry once if unhealthy and haven't retried yet
                if retry_attempt == 0:
                    self._log(session_id, "Session unhealthy, attempting retry...", level="warning")
                    # Don't mark as failed on retry - just release for retry
                    self.issue_lock.release_issue(issue_num, session_id, was_closed=False)
                    return await self._run_single_session(iteration, session_num, retry_attempt=1)

            # 6. Commit and push (serialized)
            async with self.git_lock:
                await self._commit_and_push(session_id, issue_num)

            # 7. Check outcomes (T018, T029-T030: check specific issues worked on)
            was_closed = self._check_issue_closed(issue_num)
            # T029-T030: Track issues_worked for this session
            issues_worked = [issue_num]
            outcomes = check_session_outcomes(
                self.project_dir, self.repo, self.logger,
                issues_worked=issues_worked  # T031: Pass issues_worked
            )

            if was_closed:
                self._log(session_id, f"Issue #{issue_num} successfully closed")
                # T067: Move issue to Done on project board
                try:
                    self.projects_manager.move_to_done(issue_num)
                except Exception as e:
                    self._log(session_id, f"Projects board update warning: {e}", "warning")
            else:
                self._log(session_id, f"Issue #{issue_num} NOT closed", level="warning")

            if not outcomes['success']:
                for failure in outcomes['failures']:
                    self._log(session_id, f"Outcome failure: {failure}", level="warning")

            # 8. Release claim (T018: pass was_closed to track success/failure)
            self.issue_lock.release_issue(issue_num, session_id, was_closed=was_closed)

            status = "healthy" if health_status['is_healthy'] else "unhealthy"
            closed_status = "closed" if was_closed else "not closed"
            return f"Completed issue #{issue_num} ({tool_count} tools, {status}, {closed_status})"

        except Exception as e:
            # T039: Classify and handle Claude API errors
            self._log(session_id, f"Error: {e}\n{traceback.format_exc()}", level="error")

            # Classify the error
            api_error = classify_from_exception(APISource.CLAUDE, e)
            self._log(session_id, f"Classified error: code={api_error.code}, action={api_error.suggested_action.value}")

            # T039-T042: Handle error based on classification
            recovery_result = await self._handle_api_error(
                session_id, issue_num, api_error, iteration, session_num, retry_attempt
            )

            if recovery_result:
                return recovery_result

            # T018: Mark as failed if no recovery
            self.issue_lock.release_issue(issue_num, session_id, was_closed=False)

            # Don't re-raise, return error status instead (prevents crashing entire run)
            return f"Error on issue #{issue_num}: {api_error.message} [{api_error.code}]"

    async def _handle_api_error(
        self,
        session_id: str,
        issue_num: int,
        api_error: APIError,
        iteration: int,
        session_num: int,
        retry_attempt: int
    ) -> Optional[str]:
        """
        Handle classified API error with appropriate recovery action (T039-T042).

        Args:
            session_id: Current session identifier
            issue_num: Issue being worked on
            api_error: Classified error
            iteration: Current iteration number
            session_num: Session number in iteration
            retry_attempt: Current retry attempt count

        Returns:
            Result string if recovery was attempted, None if no recovery possible
        """
        action = api_error.suggested_action

        # T040: Handle 401 errors - trigger token rotation
        if action == RecoveryAction.ROTATE_TOKEN:
            self._log(session_id, f"Auth error ({api_error.code}), attempting token rotation", "warning")
            try:
                rotator = get_rotator()
                old_token = rotator.current_name
                rotator.rotate(reason=f"API error {api_error.code}: {api_error.message}")
                self._log(session_id, f"Token rotated: {old_token} -> {rotator.current_name}")
                print(f"  [{session_id}] Token rotated: {old_token} -> {rotator.current_name}")

                # Retry with new token if not already retried
                if retry_attempt == 0:
                    self.issue_lock.release_issue(issue_num, session_id, was_closed=False)
                    await asyncio.sleep(2)  # Brief delay before retry
                    return await self._run_single_session(iteration, session_num, retry_attempt=1)
            except Exception as rotate_error:
                self._log(session_id, f"Token rotation failed: {rotate_error}", "error")

        # T041: Handle 429/529 errors - wait and retry
        elif action == RecoveryAction.WAIT_AND_RETRY:
            if retry_attempt < 2:  # Allow up to 2 retries for rate limits
                delay = get_retry_delay(api_error, retry_attempt)
                self._log(
                    session_id,
                    f"Rate limit/server error ({api_error.code}), waiting {delay:.0f}s before retry",
                    "warning"
                )
                print(f"  [{session_id}] Waiting {delay:.0f}s before retry (attempt {retry_attempt + 1})...")

                # Rotate token for rate limits
                if is_rate_limit(api_error):
                    try:
                        rotator = get_rotator()
                        old_token = rotator.current_name
                        rotator.rotate(reason=f"Rate limit {api_error.code}")
                        self._log(session_id, f"Rate limit! Rotated: {old_token} -> {rotator.current_name}")
                    except Exception:
                        pass

                self.issue_lock.release_issue(issue_num, session_id, was_closed=False)
                await asyncio.sleep(delay)
                return await self._run_single_session(iteration, session_num, retry_attempt=retry_attempt + 1)
            else:
                self._log(session_id, f"Max retries ({retry_attempt}) reached for {api_error.code}", "error")

        # T042: Handle 400 errors - mark issue for manual review
        elif action == RecoveryAction.MANUAL_REVIEW:
            self._log(session_id, f"Non-recoverable error ({api_error.code}), marking issue for manual review", "warning")
            self._mark_issue_blocked(issue_num, api_error.message)
            self.issue_lock.mark_failed(issue_num, session_id, f"manual_review:{api_error.code}")
            return f"Issue #{issue_num} blocked: {api_error.message} (requires manual review)"

        # Handle ABORT action
        elif action == RecoveryAction.ABORT:
            self._log(session_id, f"Unrecoverable error ({api_error.code}), aborting", "error")
            self.issue_lock.mark_failed(issue_num, session_id, f"abort:{api_error.code}")

        return None

    def _mark_issue_blocked(self, issue_num: int, reason: str) -> bool:
        """
        Mark an issue as blocked requiring manual review (T043, T049).

        Adds a comment to the issue and applies a 'blocked' label.
        Uses execute_gh_command() for classified error handling.

        Args:
            issue_num: GitHub issue number
            reason: Reason for blocking

        Returns:
            True if marking succeeded
        """
        try:
            # Add comment explaining the block
            comment = f"🚫 **Issue Blocked - Manual Review Required**\n\n" \
                      f"Reason: {reason}\n\n" \
                      f"The automated agent encountered an error that cannot be recovered automatically. " \
                      f"Please review the issue and resolve manually."

            cmd_comment = [
                'gh', 'issue', 'comment', str(issue_num),
                '--repo', self.repo, '--body', comment
            ]
            execute_gh_command(
                cmd=cmd_comment,
                cwd=self.project_dir,
                timeout=30,
                logger=self.logger
            )

            # Try to add a 'blocked' label (create if doesn't exist)
            cmd_label = [
                'gh', 'issue', 'edit', str(issue_num),
                '--repo', self.repo, '--add-label', 'blocked'
            ]
            execute_gh_command(
                cmd=cmd_label,
                cwd=self.project_dir,
                timeout=30,
                logger=self.logger
            )

            self._log("blocked", f"Issue #{issue_num} marked as blocked: {reason}")
            return True

        except GitHubAPIError as e:
            self._log(
                "blocked",
                f"GitHub API error marking issue #{issue_num} as blocked: {e.status_code} - {e.message}",
                "warning"
            )
            return False
        except Exception as e:
            self._log("blocked", f"Failed to mark issue #{issue_num} as blocked: {e}", "warning")
            return False

    def _generate_issue_prompt(
        self,
        issue_num: int,
        session_id: str,
        is_retry: bool = False
    ) -> str:
        """Generate prompt focused on specific issue with constitution support."""

        # Get constitution context if available
        constitution_section = ""
        constitution = get_constitution()
        if constitution and constitution.exists():
            constitution_section = constitution.get_prompt_context() + "\n---\n\n"

        # Add emphatic retry instruction if this is a retry attempt
        retry_section = ""
        if is_retry:
            retry_section = """
## RETRY ATTEMPT - TAKE ACTION NOW!

This is a RETRY because the previous attempt did not do meaningful work.
You MUST use tools immediately and make real progress on this issue.

**DO NOT:**
- Just describe what you would do
- Ask clarifying questions
- Say you cannot proceed

**DO:**
- Read the issue immediately
- Start implementing immediately
- Use tools to read files, write code, run commands
- Close the issue when done

---

"""

        return f"""## CRITICAL: PROJECT CONTEXT

**Working Directory:** `{self.project_dir}`
**GitHub Repository:** `{self.repo}`

**IMPORTANT:** For ALL `gh` commands, use the `--repo` flag:
```bash
gh issue list --repo {self.repo} --state open
gh issue view {issue_num} --repo {self.repo}
gh issue close {issue_num} --repo {self.repo}
gh issue comment {issue_num} --repo {self.repo} --body "..."
```

---

{constitution_section}{retry_section}## YOUR TASK - PARALLEL SESSION

You are session `{session_id}` in a parallel agent run.
You have been assigned to work on **GitHub Issue #{issue_num}** ONLY.

**DO NOT work on any other issue. Focus solely on issue #{issue_num}.**

### Steps:

1. **View your assigned issue:**
   ```bash
   gh issue view {issue_num} --repo {self.repo}
   ```

2. **Implement the feature/fix** described in the issue

3. **Test your changes** work correctly (run tests if available)

4. **Close the issue with a comment:**
   ```bash
   gh issue comment {issue_num} --repo {self.repo} --body "Implementation complete by {session_id}"
   gh issue close {issue_num} --repo {self.repo}
   ```

### Rules:
- Work ONLY on issue #{issue_num}
- Use `--repo {self.repo}` with ALL gh commands
- Close the issue when done
- Keep your implementation focused and minimal
- Commit and push changes before session ends

### Mandatory Outcomes:
1. CLOSE issue #{issue_num}
2. COMMIT and PUSH all changes

Begin by reading issue #{issue_num}.
"""

    def _check_issue_closed(self, issue_num: int) -> bool:
        """
        Check if an issue was closed (T018, T049).

        Uses execute_gh_command() for classified error handling.

        Args:
            issue_num: Issue number to check

        Returns:
            True if issue is closed, False otherwise
        """
        try:
            cmd = [
                'gh', 'issue', 'view', str(issue_num), '--repo', self.repo,
                '--json', 'state', '-q', '.state'
            ]
            success, stdout, stderr = execute_gh_command(
                cmd=cmd,
                cwd=self.project_dir,
                timeout=30,
                logger=self.logger
            )
            if success:
                state = stdout.strip().upper()
                return state == 'CLOSED'
        except GitHubAPIError as e:
            self._log(
                "check",
                f"GitHub API error checking issue #{issue_num}: {e.status_code} - {e.message}",
                "warning"
            )
        except Exception as e:
            self._log("check", f"Failed to check issue #{issue_num} state: {e}", "warning")

        return False

    async def _commit_and_push(self, session_id: str, issue_num: int):
        """Commit and push changes (called under git_lock)."""
        self._log(session_id, "Committing and pushing changes")

        # Check for changes
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=self.project_dir,
            capture_output=True, text=True
        )

        if not result.stdout.strip():
            self._log(session_id, "No changes to commit")
            return

        # Pull first
        subprocess.run(
            ['git', 'pull', '--rebase', 'origin', 'main'],
            cwd=self.project_dir,
            capture_output=True
        )

        # Stage all changes
        subprocess.run(
            ['git', 'add', '-A'],
            cwd=self.project_dir,
            capture_output=True
        )

        # Commit
        commit_msg = f"""feat: Implement issue #{issue_num}

Session: {session_id}
Closes #{issue_num}

🤖 Generated by parallel autonomous agent
Co-Authored-By: Claude <noreply@anthropic.com>"""

        subprocess.run(
            ['git', 'commit', '-m', commit_msg],
            cwd=self.project_dir,
            capture_output=True
        )

        # Push
        result = subprocess.run(
            ['git', 'push', 'origin', 'main'],
            cwd=self.project_dir,
            capture_output=True, text=True
        )

        if result.returncode == 0:
            self._log(session_id, f"Pushed changes for issue #{issue_num}")
        else:
            self._log(session_id, f"Push failed: {result.stderr}", level="warning")


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(
        description="Parallel Autonomous Agent - Run multiple sessions concurrently",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run 3 concurrent sessions once
    python parallel_agent.py --project-dir ./generations/my_project

    # Run 2 concurrent sessions for 5 iteration rounds
    python parallel_agent.py --project-dir ./generations/my_project --concurrent 2 --iterations 5

    # Use a specific project spec
    python parallel_agent.py --project-dir ./generations/my_project --project-name my_spec

    # Use Sonnet instead of Opus (faster, cheaper)
    python parallel_agent.py --project-dir ./generations/my_project --model claude-sonnet-4-20250514

Note: The project must be initialized first with autonomous_agent_fixed.py to create
      the GitHub repository and .github_project.json file.
"""
    )

    parser.add_argument(
        "--project-dir", "-p",
        type=Path,
        required=True,
        help="Project directory (must already be initialized)"
    )

    parser.add_argument(
        "--concurrent", "-c",
        type=int,
        default=3,
        help="Number of concurrent sessions (default: 3)"
    )

    parser.add_argument(
        "--iterations", "-i",
        type=int,
        default=1,
        help="Number of parallel iteration rounds (default: 1)"
    )

    parser.add_argument(
        "--model", "-m",
        type=str,
        default="claude-opus-4-5-20251101",
        help="Model to use (default: claude-opus-4-5-20251101)"
    )

    parser.add_argument(
        "--project-name", "-n",
        type=str,
        default=None,
        help="Project spec name from prompts/{name}/app_spec.txt"
    )

    args = parser.parse_args()

    # Validate/create project directory
    if not args.project_dir.exists():
        print(f"Creating project directory: {args.project_dir}")
        args.project_dir.mkdir(parents=True, exist_ok=True)

    # Copy spec if project-name provided
    if args.project_name:
        print(f"Copying spec from prompts/{args.project_name}/app_spec.txt")
        copy_spec_to_project(args.project_dir, project_name=args.project_name)

    project_file = args.project_dir / ".github_project.json"
    if not project_file.exists():
        print(f"Error: Project not initialized. Run autonomous_agent_fixed.py first.")
        print(f"       Missing: {project_file}")
        print(f"       The parallel agent requires the project to be initialized with GitHub repo.")
        sys.exit(1)

    # Initialize token rotator (supports multiple tokens for rate limit handling)
    try:
        rotator = TokenRotator.from_env(env_file=Path.cwd() / ".env")
        rotator.sync_env()
        set_rotator(rotator)
        print(f"Token rotator initialized with {len(rotator.tokens)} token(s)")
        print(f"  Current: {rotator.current_name} ({rotator.current.auth_type.value})")
    except ValueError as e:
        print(f"Error: {e}")
        print("\nSet one of:")
        print("  - CLAUDE_CODE_OAUTH_TOKEN (for Claude Max subscription)")
        print("  - ANTHROPIC_API_KEY (for API credits)")
        print("\nSee .env.example for backup token naming conventions")
        sys.exit(1)

    # Run parallel agent
    try:
        manager = ParallelAgentManager(
            project_dir=args.project_dir,
            max_concurrent=args.concurrent,
            model=args.model
        )

        await manager.run_parallel(num_iterations=args.iterations)

    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
