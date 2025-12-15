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
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
import logging

# Windows console UTF-8 fix
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
from github_config import get_repo_info, save_repo_info, DEFAULT_GITHUB_ORG, GITHUB_ISSUE_LIST_LIMIT
from prompts import set_project_context, copy_spec_to_project, get_constitution
from token_rotator import TokenRotator, get_rotator, set_rotator


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
# ISSUE LOCK MANAGER
# =============================================================================

class IssueLockManager:
    """
    Manages atomic issue claiming to prevent multiple sessions
    from working on the same issue.
    """

    def __init__(self, project_dir: Path, repo: str):
        self.project_dir = project_dir
        self.repo = repo
        self.claims_file = project_dir / ".issue_claims.json"
        self.lock = FileLock(project_dir / ".issue_claims.lock")

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

    def _get_open_issues(self) -> List[Dict]:
        """Get open issues from GitHub, sorted by priority."""
        try:
            result = subprocess.run(
                ['gh', 'issue', 'list', '--repo', self.repo,
                 '--state', 'open', '--json', 'number,title,labels',
                 '--limit', str(GITHUB_ISSUE_LIST_LIMIT)],
                capture_output=True, text=True, check=True,
                cwd=self.project_dir
            )
            issues = json.loads(result.stdout)

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

        except Exception as e:
            print(f"Error getting issues: {e}")
            return []

    def claim_issue(self, session_id: str) -> Optional[int]:
        """
        Atomically claim the next available issue.

        Returns:
            Issue number if claimed, None if no issues available
        """
        with self.lock:
            claims = self._load_claims()
            issues = self._get_open_issues()

            # Filter out META issue and already claimed issues
            for issue in issues:
                num = issue['number']
                title = issue.get('title', '')

                # Skip META issue
                if '[META]' in title.upper():
                    continue

                # Skip already claimed
                if str(num) in claims:
                    continue

                # Claim this issue
                claims[str(num)] = {
                    'session_id': session_id,
                    'claimed_at': datetime.now().isoformat(),
                    'title': title
                }
                self._save_claims(claims)

                # Post claim comment on GitHub
                try:
                    subprocess.run(
                        ['gh', 'issue', 'comment', str(num),
                         '--repo', self.repo,
                         '--body', f'🤖 **Claimed by parallel session:** `{session_id}`'],
                        capture_output=True, cwd=self.project_dir
                    )
                except Exception:
                    pass

                return num

            return None

    def release_issue(self, issue_num: int, session_id: str):
        """Release claim on an issue."""
        with self.lock:
            claims = self._load_claims()
            key = str(issue_num)
            if key in claims and claims[key].get('session_id') == session_id:
                del claims[key]
                self._save_claims(claims)

    def get_active_claims(self) -> Dict[str, Dict]:
        """Get all active claims."""
        with self.lock:
            return self._load_claims()


# =============================================================================
# SESSION HEALTH MONITORING (Ported from autonomous_agent_fixed.py)
# =============================================================================

def analyze_session_health(
    response: str,
    session_id: str,
    logger: logging.Logger = None,
    tool_count: int = None
) -> Dict[str, Any]:
    """
    Analyze the session response to detect if the agent is doing meaningful work.

    Args:
        response: The text response from the agent
        session_id: Session identifier for logging
        logger: Logger instance
        tool_count: Actual number of tool calls made (from SDK)

    Returns:
        dict with health status and metrics
    """
    health_status = {
        'is_healthy': True,
        'warnings': [],
        'tool_calls_count': tool_count or 0,
        'response_length': len(str(response)) if response else 0,
        'has_content': bool(response and str(response).strip())
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
    logger: logging.Logger = None
) -> Dict[str, Any]:
    """
    Check if session achieved mandatory outcomes.

    Returns:
        dict with outcome status
    """
    result = {
        'success': False,
        'issues_closed': 0,
        'meta_updated': False,
        'git_pushed': False,
        'failures': []
    }

    try:
        # Check for recently closed issues (within last hour)
        closed_check = subprocess.run(
            ['gh', 'issue', 'list', '--repo', repo, '--state', 'closed',
             '--json', 'number,closedAt', '--limit', str(GITHUB_ISSUE_LIST_LIMIT)],
            capture_output=True, text=True, cwd=project_dir, timeout=30
        )

        if closed_check.returncode == 0:
            issues = json.loads(closed_check.stdout)
            now = datetime.now()
            for issue in issues:
                closed_at = issue.get('closedAt', '')
                if closed_at:
                    try:
                        closed_time = datetime.fromisoformat(closed_at.replace('Z', '+00:00'))
                        # Check if closed within last hour
                        if (now.timestamp() - closed_time.timestamp()) < 3600:
                            result['issues_closed'] += 1
                    except Exception:
                        pass

        if result['issues_closed'] == 0:
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

        # Initialize managers
        self.issue_lock = IssueLockManager(project_dir, self.repo)
        self.git_lock = AsyncFileLock(project_dir / ".git_push.lock")

        # Shared client options
        self.client_options = ClaudeCodeOptions(
            model=model,
            system_prompt=f"You are an expert full-stack developer. Working on repo: {self.repo}. Use --repo {self.repo} with ALL gh commands.",
            allowed_tools=["Read", "Write", "Edit", "Glob", "Grep", "Bash"],
            max_turns=50
        )

        # Setup logging
        self.logger = self._setup_logger()

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
        Run multiple parallel iteration rounds.

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

            # Report results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"  Session {i}: FAILED - {result}")
                    total_failed += 1
                else:
                    print(f"  Session {i}: {result}")
                    if "Completed" in str(result):
                        total_completed += 1

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
            return "No unclaimed issues available"

        self._log(session_id, f"Claimed issue #{issue_num}")
        print(f"  [{session_id}] Claimed issue #{issue_num}")

        try:
            # 2. Sync token and create fresh client for this session
            try:
                rotator = get_rotator()
                rotator.sync_env()
                self._log(session_id, f"Using token: {rotator.current_name}")
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
                    self.issue_lock.release_issue(issue_num, session_id)
                    return await self._run_single_session(iteration, session_num, retry_attempt=1)

            # 6. Commit and push (serialized)
            async with self.git_lock:
                await self._commit_and_push(session_id, issue_num)

            # 7. Check outcomes
            outcomes = check_session_outcomes(self.project_dir, self.repo, self.logger)
            if not outcomes['success']:
                for failure in outcomes['failures']:
                    self._log(session_id, f"Outcome failure: {failure}", level="warning")

            # 8. Release claim
            self.issue_lock.release_issue(issue_num, session_id)

            status = "healthy" if health_status['is_healthy'] else "unhealthy"
            return f"Completed issue #{issue_num} ({tool_count} tools, {status})"

        except Exception as e:
            self._log(session_id, f"Error: {e}\n{traceback.format_exc()}", level="error")
            self.issue_lock.release_issue(issue_num, session_id)

            # Check for rate limit and rotate token if needed
            error_str = str(e).lower()
            rate_limit_indicators = [
                "rate limit", "rate_limit", "429", "too many requests",
                "quota exceeded", "usage limit", "overloaded", "capacity"
            ]
            is_rate_limit = any(indicator in error_str for indicator in rate_limit_indicators)

            if is_rate_limit:
                try:
                    rotator = get_rotator()
                    old_token = rotator.current_name
                    rotator.rotate(reason="rate limit error in parallel session")
                    self._log(session_id, f"Rate limit! Rotated: {old_token} -> {rotator.current_name}", "warning")
                    print(f"  [{session_id}] Rate limit hit! Switched to: {rotator.current_name}")
                except Exception as rotate_error:
                    self._log(session_id, f"Token rotation failed: {rotate_error}", "error")

            # Don't re-raise, return error status instead (prevents crashing entire run)
            return f"Error on issue #{issue_num}: {str(e)[:100]}"

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
