# Autonomous GitHub Coding Agent - Comprehensive Improvement Plan

**Generated:** 2025-12-17
**Based on:** Analysis of 6+ projects, 50+ session logs, and full codebase review

---

## Executive Summary

This plan addresses critical issues discovered through exhaustive log analysis of the autonomous coding agent framework. The system works well for moderate workloads (first 70-80% of issues) but experiences significant degradation near backlog completion. Key problems include:

1. **Issue claiming deadlocks** - Same issues reclaimed 30+ times in a single session
2. **Stale claims** - Claimed issues never released, blocking the backlog
3. **Broken outcome validation** - Sessions marked failed despite completing work
4. **Missing GitHub Projects integration** - No Kanban visualization despite commit claiming it
5. **Cascading API errors** - No recovery from mid-session Claude API failures

---

## Priority 1: Critical Fixes (Impact: Session Success)

### 1.1 Fix Issue Claim Lifecycle (MOST CRITICAL)

**Problem:** Issues claimed but never released. Same issues reclaimed 30+ times.

**Files:** `parallel_agent.py`, `autonomous_agent_fixed.py`

**Root Causes:**
- No TTL (time-to-live) on claims
- Claims released even on failure, causing re-claiming loops
- Race condition between GitHub query and lock acquisition

**Solution:**

```python
# parallel_agent.py - IssueLockManager

class IssueLockManager:
    CLAIM_TTL_MINUTES = 30  # Auto-expire stale claims

    def claim_issue(self, session_id: str) -> Optional[int]:
        with self.lock:
            claims = self._load_claims()
            self._cleanup_stale_claims(claims)  # NEW: Expire old claims

            # ... existing code ...

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
            print(f"Cleaning stale claim: #{key} (claimed {data['session_id']})")
            del claims[key]

        if stale_keys:
            self._save_claims(claims)

        return claims

    def release_issue(self, issue_num: int, session_id: str, was_closed: bool = False):
        """Release claim - but only if issue was actually closed."""
        with self.lock:
            claims = self._load_claims()
            key = str(issue_num)

            if key in claims and claims[key].get('session_id') == session_id:
                if was_closed:
                    # Successful completion - release
                    del claims[key]
                else:
                    # Failed session - mark as stale but don't release
                    claims[key]['failed_at'] = datetime.now().isoformat()
                    claims[key]['failure_count'] = claims[key].get('failure_count', 0) + 1

                self._save_claims(claims)
```

**Impact:** Prevents infinite reclaim loops and cleans up stale claims.

---

### 1.2 Fix Outcome Validation Logic

**Problem:** Sessions marked as "FAILED" despite successfully closing issues.

**Files:** `autonomous_agent_fixed.py` lines 99-238

**Root Cause:** Time-based check only looks at issues closed "within last hour", missing edge cases.

**Solution:**

```python
def check_session_mandatory_outcomes(
    project_dir: Path,
    repo: str,
    issues_worked: List[int],  # NEW: Pass issues we worked on
    logger: logging.Logger = None
) -> Dict[str, Any]:
    """Validate session achieved mandatory outcomes."""

    result = {
        'success': False,
        'issues_closed': 0,
        'issues_worked': issues_worked,
        'meta_updated': False,
        'git_pushed': False,
        'failures': []
    }

    # Check SPECIFIC issues we worked on, not time-based
    for issue_num in issues_worked:
        try:
            check = subprocess.run(
                ['gh', 'issue', 'view', str(issue_num), '--repo', repo,
                 '--json', 'state', '-q', '.state'],
                capture_output=True, text=True, cwd=project_dir, timeout=30
            )
            if check.returncode == 0 and check.stdout.strip() == 'CLOSED':
                result['issues_closed'] += 1
        except Exception as e:
            logger.warning(f"Failed to check issue #{issue_num}: {e}")

    if result['issues_closed'] == 0:
        result['failures'].append(f"Worked on {len(issues_worked)} issues but none were closed")

    # ... rest of validation
```

**Impact:** Accurate success/failure reporting.

---

### 1.3 Add Graceful Termination Detection

**Problem:** Agent spams "No unclaimed issues available" indefinitely when backlog depletes.

**Files:** `parallel_agent.py`

**Solution:**

```python
class ParallelAgentManager:
    def __init__(self, ...):
        # ... existing ...
        self.consecutive_no_issues = 0
        self.MAX_NO_ISSUES_ROUNDS = 3

    async def _run_single_session(self, ...):
        issue_num = self.issue_lock.claim_issue(session_id)

        if not issue_num:
            self._log(session_id, "No unclaimed issues available")
            return "NO_ISSUES"  # NEW: Distinct return value

        self.consecutive_no_issues = 0  # Reset on success
        # ... rest of session

    async def run_parallel(self, num_iterations: int = 1):
        for iteration in range(1, num_iterations + 1):
            # ... existing parallel execution ...

            # Check if all sessions got NO_ISSUES
            no_issues_count = sum(1 for r in results if r == "NO_ISSUES")
            if no_issues_count == len(results):
                self.consecutive_no_issues += 1

                if self.consecutive_no_issues >= self.MAX_NO_ISSUES_ROUNDS:
                    print(f"\n{'='*60}")
                    print("  ALL ISSUES COMPLETE - Stopping agent")
                    print(f"{'='*60}\n")
                    break  # Graceful termination
```

**Impact:** Prevents hours of wasted compute on empty backlogs.

---

## Priority 2: Major Improvements (Impact: Code Quality)

### 2.1 Add Claude API Error Handling

**Problem:** Content filtering (HTTP 400) crashes sessions without recovery.

**Files:** `autonomous_agent_fixed.py`, `parallel_agent.py`

**Solution:**

```python
async def _run_single_session(self, ...):
    try:
        async with client:
            await client.query(prompt, session_id=session_id)
            # ... message processing ...

    except Exception as e:
        error_str = str(e).lower()

        # Claude API specific errors
        if 'content filtering' in error_str or 'blocked' in error_str:
            self._log(session_id, "Content filtering triggered - skipping issue", "warning")
            # Mark issue as requiring manual review
            await self._mark_issue_blocked(issue_num, "Content filtering triggered")
            return f"Blocked: Issue #{issue_num} (content filtering)"

        elif '401' in error_str or 'unauthorized' in error_str:
            self._log(session_id, "Auth error - rotating token", "error")
            rotator.rotate(reason="auth error")
            # Retry once with new token
            return await self._run_single_session(iteration, session_num, retry_attempt=1)

        elif '500' in error_str or 'server error' in error_str:
            self._log(session_id, "Server error - will retry", "warning")
            await asyncio.sleep(30)
            return await self._run_single_session(iteration, session_num, retry_attempt=1)

        # ... existing error handling
```

**Impact:** Prevents cascading failures from API errors.

---

### 2.2 Add GitHub API Error Handling

**Problem:** No handling for GitHub 401/403/409 errors.

**Files:** `github_cache.py`, `github_enhanced.py`

**Solution:**

```python
# github_cache.py

class GitHubAPIError(Exception):
    """Specific GitHub API error with recovery hints."""
    def __init__(self, status_code: int, message: str, recoverable: bool = False):
        self.status_code = status_code
        self.message = message
        self.recoverable = recoverable
        super().__init__(f"GitHub API {status_code}: {message}")

def execute_gh_command(cmd: List[str], cwd: Path) -> Tuple[bool, str, str]:
    """Execute gh CLI with error classification."""
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)

    if result.returncode != 0:
        stderr = result.stderr.lower()

        if '401' in stderr or 'unauthorized' in stderr:
            raise GitHubAPIError(401, "Authentication failed - check gh auth status", False)
        elif '403' in stderr or 'forbidden' in stderr:
            raise GitHubAPIError(403, "Permission denied - check repo access", False)
        elif '409' in stderr or 'conflict' in stderr:
            raise GitHubAPIError(409, "Conflict - may need to pull latest", True)
        elif '422' in stderr or 'unprocessable' in stderr:
            raise GitHubAPIError(422, "Invalid input - check command syntax", False)
        elif '429' in stderr or 'rate limit' in stderr:
            raise GitHubAPIError(429, "Rate limited - waiting", True)

    return result.returncode == 0, result.stdout, result.stderr
```

**Impact:** Clear error messages and recovery paths.

---

### 2.3 Improve Session Health Monitoring

**Problem:** Health checks accurate but don't detect "busy but unproductive" sessions.

**Files:** `autonomous_agent_fixed.py`

**Solution:**

```python
def analyze_session_health(
    response: str,
    session_id: str,
    logger: logging.Logger = None,
    tool_count: int = None,
    files_changed: int = 0,  # NEW
    issues_closed: int = 0   # NEW
) -> Dict[str, Any]:
    """Enhanced health analysis with productivity metrics."""

    health_status = {
        # ... existing fields ...
        'productivity_score': 0.0,
        'productive': True
    }

    # NEW: Productivity ratio
    if tool_count and tool_count > 10:
        # Calculate productivity: (issues_closed + files_changed) / tool_count
        productivity = (issues_closed * 10 + files_changed) / tool_count
        health_status['productivity_score'] = productivity

        if productivity < 0.1 and tool_count > 30:
            health_status['productive'] = False
            health_status['warnings'].append(
                f"Low productivity: {tool_count} tools but only {files_changed} files changed"
            )

    return health_status
```

**Impact:** Detects sessions that run but accomplish nothing.

---

## Priority 3: GitHub Projects Integration (NEW FEATURE)

### 3.1 Phase 1: Basic Project Setup

**Files to create:** `github_projects.py`

```python
"""GitHub Projects v2 Integration"""

import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, List

class GitHubProjectsManager:
    """Manage GitHub Projects v2 for visual workflow tracking."""

    def __init__(self, repo: str, owner: str, project_dir: Path):
        self.repo = repo
        self.owner = owner
        self.project_dir = project_dir
        self.project_number: Optional[int] = None
        self.project_id: Optional[str] = None  # Node ID for GraphQL
        self.status_field_id: Optional[str] = None
        self.status_options: Dict[str, str] = {}  # name -> option_id

    def create_project(self, title: str) -> int:
        """Create a new project board."""
        result = subprocess.run(
            ['gh', 'project', 'create',
             '--owner', self.owner,
             '--title', title,
             '--format', 'json'],
            capture_output=True, text=True
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            self.project_number = data['number']
            return self.project_number

        raise RuntimeError(f"Failed to create project: {result.stderr}")

    def link_repo(self) -> bool:
        """Link repository to project."""
        result = subprocess.run(
            ['gh', 'project', 'link', str(self.project_number),
             '--owner', self.owner,
             '--repo', self.repo],
            capture_output=True, text=True
        )
        return result.returncode == 0

    def add_issue_to_project(self, issue_number: int) -> Optional[str]:
        """Add an issue to the project board. Returns item ID."""
        # Get issue node ID
        result = subprocess.run(
            ['gh', 'issue', 'view', str(issue_number),
             '--repo', self.repo, '--json', 'id', '-q', '.id'],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            return None

        issue_node_id = result.stdout.strip()

        # Add to project via GraphQL
        query = f'''
        mutation {{
            addProjectV2ItemById(input: {{
                projectId: "{self.project_id}"
                contentId: "{issue_node_id}"
            }}) {{ item {{ id }} }}
        }}
        '''

        result = subprocess.run(
            ['gh', 'api', 'graphql', '-f', f'query={query}'],
            capture_output=True, text=True
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data['data']['addProjectV2ItemById']['item']['id']

        return None

    def update_item_status(self, item_id: str, status: str) -> bool:
        """Update item status (Todo, In Progress, Done)."""
        if status not in self.status_options:
            return False

        option_id = self.status_options[status]

        query = f'''
        mutation {{
            updateProjectV2ItemFieldValue(input: {{
                projectId: "{self.project_id}"
                itemId: "{item_id}"
                fieldId: "{self.status_field_id}"
                value: {{ singleSelectOptionId: "{option_id}" }}
            }}) {{ projectV2Item {{ id }} }}
        }}
        '''

        result = subprocess.run(
            ['gh', 'api', 'graphql', '-f', f'query={query}'],
            capture_output=True, text=True
        )

        return result.returncode == 0
```

### 3.2 Integration Points

**Update `prompts/initializer_prompt.md`:**

```markdown
### 4️⃣b OPTIONAL: Create GitHub Project Board

gh project create --owner OWNER --title "Project Name" --format json
gh project link PROJECT_NUMBER --owner OWNER --repo OWNER/REPO
```

**Update `prompts/coding_prompt.md`:**

```markdown
## When Claiming Issue
gh project item-edit PROJECT --owner OWNER --id ITEM_ID --field Status --value "In Progress"

## When Closing Issue
gh project item-edit PROJECT --owner OWNER --id ITEM_ID --field Status --value "Done"
```

---

## Priority 4: Prompt System Cleanup

### 4.1 Remove Redundancy

**Problem:** `--repo` mentioned 15+ times, turn budgeting explained 4+ times.

**Action:** Create single reference section, use cross-references.

```markdown
## Quick Reference (MEMORIZE THIS)

**Repo:** `--repo {REPO}` (use with ALL gh commands)
**Turns:** 50 max (1 turn = 1 SDK operation)

---

[Rest of prompt references "Quick Reference" section]
```

### 4.2 Fix Constitution Conflicts

**Problem:** Constitution and coding_prompt.md have duplicate TDD sections.

**Solution:** Make constitution sections REPLACE prompt sections, not append.

```python
# prompts.py

def get_coding_prompt(project_dir: Path) -> str:
    base_prompt = _load_prompt('coding_prompt.md')
    constitution = get_constitution()

    if constitution and constitution.tdd_enabled:
        # REPLACE TDD section instead of appending
        base_prompt = base_prompt.replace(
            '## TDD & VERIFICATION (When Constitution Requires)',
            constitution.get_tdd_section()
        )

    return get_context_header() + base_prompt
```

### 4.3 Add Issue Selection Algorithm

**Problem:** "Pick an issue that can be completed in ~20 turns" is vague.

**Solution:** Provide concrete decision tree.

```markdown
## Issue Selection Algorithm

1. List issues: `gh issue list --repo REPO --state open --label "priority:urgent" --limit 5`
2. For each issue:
   - Read body: `gh issue view NUM --repo REPO`
   - Estimate size:
     - < 50 lines in spec = SMALL (10 turns)
     - 50-150 lines = MEDIUM (20 turns)
     - > 150 lines = LARGE (35 turns)
3. Select: Highest priority + smallest size that fits remaining turns
4. Skip: Issues with "blocked" label or requiring external APIs
```

---

## Priority 5: Monitoring & Observability

### 5.1 Enhanced Dashboard

**File:** `monitor.py`

**Add:**
- Project board visualization (ASCII Kanban)
- Error rate by type
- Token rotation frequency
- Session productivity score
- Claim/release tracking

### 5.2 Structured Metrics

**Create:** `metrics.py`

```python
@dataclass
class SessionMetrics:
    session_id: str
    duration_seconds: float
    tool_calls: int
    files_changed: int
    issues_claimed: List[int]
    issues_closed: List[int]
    errors: List[str]
    health_score: float
    productivity_score: float
    token_rotations: int

def export_metrics(metrics: List[SessionMetrics], path: Path):
    """Export to CSV for analysis."""
    # ... implementation
```

---

## Implementation Roadmap

### Phase 1: Critical Fixes (Week 1)
- [ ] Fix issue claim lifecycle (1.1)
- [ ] Fix outcome validation (1.2)
- [ ] Add graceful termination (1.3)

### Phase 2: Error Handling (Week 2)
- [ ] Claude API error handling (2.1)
- [ ] GitHub API error handling (2.2)
- [ ] Enhanced health monitoring (2.3)

### Phase 3: GitHub Projects (Week 3)
- [ ] Create `github_projects.py` module
- [ ] Update prompts with project commands
- [ ] Add to initializer workflow

### Phase 4: Prompt Cleanup (Week 4)
- [ ] Remove redundancy (4.1)
- [ ] Fix constitution conflicts (4.2)
- [ ] Add selection algorithm (4.3)

### Phase 5: Monitoring (Week 5)
- [ ] Enhanced dashboard (5.1)
- [ ] Structured metrics (5.2)

---

## Summary of Key Issues Found

| Category | Issue | Severity | Status |
|----------|-------|----------|--------|
| Claim Lifecycle | No TTL on claims | CRITICAL | Plan Ready |
| Claim Lifecycle | Same issue reclaimed 30+ times | CRITICAL | Plan Ready |
| Validation | Outcome check broken (time-based) | CRITICAL | Plan Ready |
| Termination | No backlog completion detection | HIGH | Plan Ready |
| API Errors | No content filtering recovery | HIGH | Plan Ready |
| API Errors | No GitHub 401/403/409 handling | HIGH | Plan Ready |
| Health | Productivity not measured | MEDIUM | Plan Ready |
| Projects | No Kanban integration | MEDIUM | Plan Ready |
| Prompts | Massive redundancy | MEDIUM | Plan Ready |
| Prompts | Turn counting ambiguous | MEDIUM | Plan Ready |
| Prompts | Issue selection vague | MEDIUM | Plan Ready |

---

## Files to Modify

| File | Changes | Priority |
|------|---------|----------|
| `parallel_agent.py` | Claim TTL, graceful termination, API error handling | P0 |
| `autonomous_agent_fixed.py` | Outcome validation, health monitoring | P0 |
| `github_projects.py` | NEW: Projects v2 integration | P1 |
| `prompts/coding_prompt.md` | Redundancy removal, algorithm | P2 |
| `prompts/initializer_prompt.md` | Projects setup, cleanup | P2 |
| `prompts.py` | Constitution conflict resolution | P2 |
| `github_cache.py` | API error classification | P1 |
| `monitor.py` | Dashboard enhancements | P3 |
| `metrics.py` | NEW: Structured metrics | P3 |

---

## Expected Outcomes

After implementing this plan:

1. **Session Success Rate:** 70% → 95%
2. **Claim Deadlocks:** Eliminated
3. **Empty Backlog Detection:** Immediate (vs hours of spinning)
4. **Error Recovery:** Automatic for transient errors
5. **Visibility:** Kanban board for stakeholders
6. **Productivity:** Measurable per session
