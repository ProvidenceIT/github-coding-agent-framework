# Quickstart: Agent Reliability Improvements

**Feature**: 001-agent-reliability
**Date**: 2025-12-17

## Overview

This guide provides implementation order and key code patterns for the agent reliability improvements.

## Implementation Order

### Phase 1: Critical Fixes (P1)

Implement in this order due to dependencies:

1. **Issue Claim TTL** (`parallel_agent.py`)
   - Add `_cleanup_stale_claims()` method
   - Call from `claim_issue()` before querying GitHub
   - Add `CLAIM_TTL_MINUTES` constant

2. **Failure Tracking** (`parallel_agent.py`)
   - Modify `release_issue()` to accept `was_closed` parameter
   - Track `failed_at` and `failure_count` in claims
   - Skip issues with high failure counts in `claim_issue()`

3. **Graceful Termination** (`parallel_agent.py`)
   - Add `consecutive_no_issues` counter
   - Return "NO_ISSUES" from sessions
   - Check counter in `run_parallel()` loop

4. **Outcome Validation Fix** (`autonomous_agent_fixed.py`)
   - Modify `check_session_mandatory_outcomes()` signature
   - Replace time-based query with issue-specific checks
   - Track `issues_worked` through session lifecycle

### Phase 2: Error Handling (P2)

Can be implemented in parallel:

5. **GitHub API Errors** (`github_cache.py`)
   - Create `GitHubAPIError` exception class
   - Add `execute_gh_command()` with error classification
   - Update callers to handle classified errors

6. **Claude API Errors** (`parallel_agent.py`)
   - Add error classification in `_run_single_session()`
   - Implement retry logic with token rotation
   - Add `_mark_issue_blocked()` helper

7. **Productivity Monitoring** (`autonomous_agent_fixed.py`)
   - Add `files_changed`, `issues_closed` params to `analyze_session_health()`
   - Calculate productivity score
   - Add productivity warnings

### Phase 3: Enhancements (P3)

Optional improvements:

8. **GitHub Projects** (`github_projects.py` - new file)
   - Create `GitHubProjectsManager` class
   - Integrate with initializer and parallel agent
   - Update status on claim/close

9. **Prompt Cleanup** (`prompts/coding_prompt.md`)
   - Create "Quick Reference" section
   - Remove redundant `--repo` mentions
   - Add issue selection algorithm

---

## Key Code Patterns

### Pattern 1: Stale Claim Cleanup

```python
# parallel_agent.py

class IssueLockManager:
    CLAIM_TTL_MINUTES = 30

    def _cleanup_stale_claims(self, claims: Dict) -> Dict:
        """Remove claims older than TTL."""
        now = datetime.now()
        ttl = timedelta(minutes=self.CLAIM_TTL_MINUTES)

        stale_keys = []
        for key, data in claims.items():
            claimed_at = datetime.fromisoformat(data['claimed_at'])
            if now - claimed_at > ttl:
                stale_keys.append(key)

        for key in stale_keys:
            print(f"Cleaning stale claim: #{key}")
            del claims[key]

        if stale_keys:
            self._save_claims(claims)

        return claims

    def claim_issue(self, session_id: str) -> Optional[int]:
        with self.lock:
            claims = self._load_claims()
            claims = self._cleanup_stale_claims(claims)  # ADD THIS
            # ... rest of existing code
```

### Pattern 2: Failure Tracking

```python
# parallel_agent.py

def release_issue(self, issue_num: int, session_id: str, was_closed: bool = False):
    """Release claim - handle success vs failure differently."""
    with self.lock:
        claims = self._load_claims()
        key = str(issue_num)

        if key in claims and claims[key].get('session_id') == session_id:
            if was_closed:
                # Success - remove claim entirely
                del claims[key]
            else:
                # Failure - keep claim with failure metadata
                claims[key]['failed_at'] = datetime.now().isoformat()
                claims[key]['failure_count'] = claims[key].get('failure_count', 0) + 1

            self._save_claims(claims)
```

### Pattern 3: Graceful Termination

```python
# parallel_agent.py

class ParallelAgentManager:
    MAX_NO_ISSUES_ROUNDS = 3

    async def run_parallel(self, num_iterations: int = 1):
        consecutive_no_issues = 0

        for iteration in range(1, num_iterations + 1):
            results = await self._run_iteration(iteration)

            no_issues_count = sum(1 for r in results if r == "NO_ISSUES")

            if no_issues_count == len(results):
                consecutive_no_issues += 1
                if consecutive_no_issues >= self.MAX_NO_ISSUES_ROUNDS:
                    print("\n" + "="*60)
                    print("  ALL ISSUES COMPLETE - Stopping agent")
                    print("="*60 + "\n")
                    break
            else:
                consecutive_no_issues = 0
```

### Pattern 4: Issue-Specific Validation

```python
# autonomous_agent_fixed.py

def check_session_mandatory_outcomes(
    project_dir: Path,
    repo: str,
    issues_worked: List[int],  # NEW parameter
    logger: logging.Logger = None
) -> Dict[str, Any]:

    result = {
        'success': False,
        'issues_worked': issues_worked,
        'issues_closed': 0,
        'issues_closed_list': [],
        'failures': []
    }

    # Check SPECIFIC issues, not time-based query
    for issue_num in issues_worked:
        try:
            check = subprocess.run(
                ['gh', 'issue', 'view', str(issue_num), '--repo', repo,
                 '--json', 'state', '-q', '.state'],
                capture_output=True, text=True, cwd=project_dir, timeout=30
            )
            if check.returncode == 0 and check.stdout.strip() == 'CLOSED':
                result['issues_closed'] += 1
                result['issues_closed_list'].append(issue_num)
        except Exception as e:
            logger.warning(f"Failed to check issue #{issue_num}: {e}")

    result['success'] = result['issues_closed'] > 0

    if result['issues_closed'] == 0 and len(issues_worked) > 0:
        result['failures'].append(
            f"Worked on {len(issues_worked)} issues but none closed: {issues_worked}"
        )

    return result
```

### Pattern 5: API Error Classification

```python
# github_cache.py

class GitHubAPIError(Exception):
    def __init__(self, status_code: int, message: str,
                 recoverable: bool = False, action: str = "abort"):
        self.status_code = status_code
        self.message = message
        self.recoverable = recoverable
        self.action = action
        super().__init__(f"GitHub API {status_code}: {message}")

def execute_gh_command(cmd: List[str], cwd: Path) -> Tuple[bool, str, str]:
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)

    if result.returncode != 0:
        stderr = result.stderr.lower()

        if '401' in stderr or 'unauthorized' in stderr:
            raise GitHubAPIError(401, "Authentication failed", False, "check_auth")
        elif '403' in stderr or 'forbidden' in stderr:
            raise GitHubAPIError(403, "Permission denied", False, "check_permissions")
        elif '429' in stderr or 'rate limit' in stderr:
            raise GitHubAPIError(429, "Rate limited", True, "wait_retry")
        elif '409' in stderr or 'conflict' in stderr:
            raise GitHubAPIError(409, "Conflict - pull latest", True, "pull_retry")

    return result.returncode == 0, result.stdout, result.stderr
```

---

## Testing Strategy

Since there's no formal test framework, validate each change with:

1. **Unit-style validation**:
   - Run agent with mock/test repository
   - Verify claim file format after operations

2. **Integration validation**:
   - Run parallel agent with 2-3 sessions
   - Verify no duplicate claims
   - Monitor logs for warnings

3. **Edge case validation**:
   - Manually create stale claims (edit .issue_claims.json with old timestamp)
   - Verify cleanup occurs
   - Deplete backlog and verify graceful termination

---

## Files to Modify

| File | Changes | Lines (est.) |
|------|---------|--------------|
| parallel_agent.py | TTL, failures, termination | +80 |
| autonomous_agent_fixed.py | Outcome validation, health | +50 |
| github_cache.py | Error classification | +60 |
| github_projects.py | NEW file | +200 |
| prompts/coding_prompt.md | Quick Reference section | +20, -50 |

---

## Rollback Plan

Each change is isolated and can be reverted independently:

1. **TTL Cleanup**: Remove `_cleanup_stale_claims()` call
2. **Failure Tracking**: Change `release_issue()` back to always delete
3. **Termination**: Remove counter logic in `run_parallel()`
4. **Validation**: Restore time-based query
5. **Error Handling**: Remove exception class, restore basic subprocess calls
6. **Projects**: Don't import `github_projects.py` in agents

---

## Success Verification

After implementation, verify:

- [ ] Stale claims cleaned up after 30 minutes
- [ ] Failed issues tracked with failure_count
- [ ] Agent terminates after 3 rounds of no issues
- [ ] Outcome shows specific issues closed
- [ ] API errors classified with recovery hints
- [ ] Low productivity warnings generated
- [ ] (Optional) Project board updates on claim/close
