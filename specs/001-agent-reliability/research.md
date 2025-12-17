# Research: Agent Reliability Improvements

**Feature**: 001-agent-reliability
**Date**: 2025-12-17

## Research Task 1: Issue Claim TTL Implementation

### Decision
Implement time-based claim expiration with a 30-minute default TTL, cleaned up lazily during claim operations.

### Rationale
- **Lazy cleanup** preferred over background threads for simplicity and cross-platform compatibility
- **30 minutes** balances typical issue complexity (most resolved in 20-40 minutes) with allowing retry of failed claims
- **Failure tracking** keeps claims with failure metadata rather than releasing immediately to prevent infinite retry loops

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Background cleanup thread | Adds complexity, requires thread-safe coordination |
| Shorter TTL (10 min) | Too aggressive for complex issues |
| Longer TTL (60 min) | Stale claims block backlog too long |
| Immediate release on failure | Causes infinite reclaim loops (observed: 30+ reclaims) |

### Implementation Notes
```python
# In IssueLockManager._cleanup_stale_claims()
# Called at start of claim_issue() - lazy evaluation
ttl = timedelta(minutes=self.CLAIM_TTL_MINUTES)  # default: 30
for key, data in claims.items():
    claimed_at = datetime.fromisoformat(data['claimed_at'])
    if now - claimed_at > ttl:
        del claims[key]  # Stale claim - release
```

---

## Research Task 2: File-based Locking Patterns

### Decision
Use existing FileLock class with platform-specific implementations (msvcrt on Windows, fcntl on Unix). Add atomic read-modify-write pattern for claim cleanup.

### Rationale
- **Existing implementation** already proven to work cross-platform
- **File locking** sufficient for single-machine concurrency (up to 5 sessions)
- **Lock file separate from data file** prevents corruption during cleanup

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Redis/distributed lock | Over-engineered for single-machine use case |
| Database with transactions | Adds dependency, JSON files sufficient |
| In-memory only | Doesn't persist across restarts |

### Implementation Notes
```python
# Atomic cleanup pattern
with self.lock:
    claims = self._load_claims()
    claims = self._cleanup_stale_claims(claims)  # Modifies in place
    self._save_claims(claims)
```

---

## Research Task 3: API Error Classification

### Decision
Create error classification with recoverable/non-recoverable categories and specific recovery actions.

### Rationale
- **Clear categories** enable automated recovery for transient errors
- **Specific messages** improve operator debugging
- **Recovery hints** guide both automated retry and manual intervention

### Error Classification Table

| Error Type | Code(s) | Recoverable | Recovery Action |
|------------|---------|-------------|-----------------|
| Content Filtering | 400 | No | Mark issue for manual review |
| Auth Failure | 401 | Maybe | Rotate token, retry once |
| Forbidden | 403 | No | Check permissions |
| Not Found | 404 | No | Validate issue exists |
| Conflict | 409 | Yes | Pull latest, retry |
| Rate Limited | 429 | Yes | Wait (use Retry-After header) |
| Server Error | 500/502/503 | Yes | Exponential backoff |

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Treat all errors same | Misses recovery opportunities |
| Always retry | Wastes resources on non-recoverable errors |
| Never retry | Fails on transient network issues |

### Implementation Notes
```python
class APIError(Exception):
    def __init__(self, code: int, message: str, recoverable: bool, action: str):
        self.code = code
        self.message = message
        self.recoverable = recoverable
        self.action = action  # e.g., "rotate_token", "wait_30s", "manual_review"
```

---

## Research Task 4: GitHub Projects v2 API

### Decision
Use GitHub GraphQL API via `gh api graphql` for Projects v2 operations. Create project during initialization, update item status on claim/close.

### Rationale
- **GraphQL required** - REST API doesn't support Projects v2 mutations
- **gh CLI wrapper** - Simplifies auth handling (uses existing `gh auth`)
- **Status field** - Standard "Status" single-select field for Kanban columns

### Key GraphQL Operations

**Create Project:**
```graphql
mutation {
  createProjectV2(input: {ownerId: $ownerId, title: $title}) {
    projectV2 { id number }
  }
}
```

**Add Issue to Project:**
```graphql
mutation {
  addProjectV2ItemById(input: {projectId: $projectId, contentId: $issueNodeId}) {
    item { id }
  }
}
```

**Update Item Status:**
```graphql
mutation {
  updateProjectV2ItemFieldValue(input: {
    projectId: $projectId,
    itemId: $itemId,
    fieldId: $statusFieldId,
    value: {singleSelectOptionId: $optionId}
  }) { projectV2Item { id } }
}
```

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| REST API | Projects v2 not supported |
| PyGitHub library | Adds dependency, gh CLI sufficient |
| Classic Projects | Deprecated, limited features |

### Implementation Notes
- Store project metadata in `.github_project.json`: project_id, number, status_field_id, status_options
- Detect existing project by title before creating new one
- Handle missing columns gracefully (recreate or warn)

---

## Research Task 5: Prompt Token Optimization

### Decision
Consolidate repeated content into "Quick Reference" section at top of prompt. Use replacement (not append) for constitution sections.

### Rationale
- **Redundancy found**: `--repo` mentioned 15+ times, turn budgeting explained 4+ times
- **Token savings**: Estimated 20-30% reduction in prompt size
- **Maintainability**: Single source of truth for each concept

### Consolidation Strategy

**Before (scattered):**
```markdown
Use `gh issue list --repo OWNER/REPO`...
Remember to use `--repo OWNER/REPO` with gh commands...
Always include `--repo OWNER/REPO`...
```

**After (consolidated):**
```markdown
## Quick Reference (MEMORIZE THIS)
- **Repo:** `--repo {REPO}` (use with ALL gh commands)
- **Turns:** 50 max (1 turn = 1 SDK operation)
- **Budget:** 20 turns for claiming, 30 for implementation
```

### Constitution Replacement Pattern
```python
def get_coding_prompt(project_dir: Path) -> str:
    base = _load_prompt('coding_prompt.md')
    constitution = get_constitution()
    if constitution and constitution.tdd_enabled:
        # REPLACE TDD section, don't append
        base = base.replace('## TDD & VERIFICATION', constitution.tdd_section)
    return get_context_header() + base
```

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Keep redundancy | Wastes tokens, harder to maintain |
| Aggressive trimming | Risk losing important context |
| Dynamic generation | More complex, harder to debug |

---

## Research Task 6: Outcome Validation Fix

### Decision
Track specific issues worked on by session instead of time-based queries.

### Rationale
- **Current bug**: Counts ALL issues closed in last hour, not issues THIS session worked on
- **Time overlap**: Multiple sessions may run concurrently, making time-based queries unreliable
- **Session isolation**: Each session should only validate its own work

### Current Problem (autonomous_agent_fixed.py:131-159)
```python
# BROKEN: Counts ALL issues closed in last hour
one_hour_ago = datetime.now() - timedelta(hours=1)
for issue in issues:
    if closed_time > one_hour_ago:
        result['issues_closed'] += 1  # Wrong! Other sessions' work counted
```

### Fixed Approach
```python
@dataclass
class SessionState:
    session_id: str
    issues_worked: List[int] = field(default_factory=list)  # Issues THIS session claimed
    issues_closed: List[int] = field(default_factory=list)  # Issues THIS session closed

def validate_session_outcomes(state: SessionState, repo: str) -> SessionOutcome:
    """Validate outcomes for SPECIFIC issues this session worked on."""
    closed = []
    for issue_num in state.issues_worked:
        # Check actual GitHub state for THIS issue
        result = subprocess.run(
            ['gh', 'issue', 'view', str(issue_num), '--repo', repo, '--json', 'state'],
            capture_output=True, text=True
        )
        if '"state":"CLOSED"' in result.stdout:
            closed.append(issue_num)
    return SessionOutcome(
        issues_worked=state.issues_worked,
        issues_closed=closed,
        success_rate=len(closed) / max(len(state.issues_worked), 1)
    )
```

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Keep time-based | Fundamentally broken for parallel sessions |
| Timestamp per issue | Still requires correlation, more complex |
| Session markers in comments | Adds GitHub API calls, parsing overhead |

---

## Research Task 7: Productivity Scoring

### Decision
Calculate productivity score based on outcomes vs effort, with configurable thresholds.

### Rationale
- **Gap identified**: Current health checks detect stopped sessions but miss "busy but unproductive" sessions
- **Metric needed**: Ratio of visible output to tool invocations
- **Early warning**: Flag sessions spinning without making progress

### Productivity Formula
```python
def calculate_productivity_score(tool_count: int, files_changed: int, issues_closed: int) -> float:
    """
    Score = (files_changed * 2 + issues_closed * 5) / max(tool_count, 1)

    Interpretation:
    - < 0.1: Very low productivity (many tools, no output)
    - 0.1-0.5: Low productivity
    - 0.5-1.0: Normal productivity
    - > 1.0: High productivity
    """
    outcomes = files_changed * 2 + issues_closed * 5
    return outcomes / max(tool_count, 1)
```

### Warning Thresholds
```python
PRODUCTIVITY_THRESHOLDS = {
    'min_tools_for_analysis': 30,   # Only analyze if enough activity
    'low_productivity_score': 0.1,  # Trigger warning below this
}

# Example warnings:
# "Low productivity: 50 tool calls but 0 files changed"
# "Productivity score 0.06 below threshold 0.1"
```

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Simple tool count | Doesn't account for valuable exploratory work |
| Files only | Misses successful issue closures without file changes |
| Time-based | Duration varies widely, not a good proxy |

---

## Research Task 8: Empty Backlog Detection

### Decision
Stop agent after N consecutive rounds where ALL sessions report no available issues.

### Rationale
- **Current problem**: Agent runs indefinitely printing "No unclaimed issues available"
- **Resource waste**: Hours of API calls with no productive output
- **Graceful termination**: Clear message and clean exit

### Implementation
```python
NO_ISSUES_THRESHOLD = 3  # Configurable

class BacklogMonitor:
    def __init__(self):
        self.consecutive_no_issues = 0

    def record_round(self, session_results: List[str]) -> bool:
        """Returns True if agent should terminate."""
        all_no_issues = all(
            "No unclaimed issues" in result or "NO_ISSUES" in result
            for result in session_results
        )

        if all_no_issues:
            self.consecutive_no_issues += 1
            if self.consecutive_no_issues >= NO_ISSUES_THRESHOLD:
                print("ALL ISSUES COMPLETE - Stopping agent")
                return True  # Terminate
        else:
            self.consecutive_no_issues = 0  # Reset on any work found

        return False  # Continue
```

### Edge Cases
- **Single new issue created**: Reset counter, continue running
- **Partial sessions find work**: Reset counter (not all sessions empty)
- **Network error vs empty**: Distinguish "no issues" from "failed to fetch"

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Stop immediately | Too aggressive; may miss stragglers |
| 5+ rounds | Too slow to terminate |
| Manual only | Wastes resources if operator not watching |

---

## Research Task 9: Failure Tracking Enhancement

### Decision
Track failure count per issue to deprioritize repeatedly failing issues.

### Rationale
- **Infinite loop prevention**: Some issues may consistently fail (bad spec, missing deps)
- **Failure visibility**: Operators can see which issues need manual intervention
- **Graceful degradation**: System continues working on other issues

### Enhanced Claim Structure
```json
{
  "5": {
    "session_id": "parallel_20250117_120000_01_02",
    "claimed_at": "2025-01-17T12:00:00",
    "title": "Add user authentication",
    "status": "claimed",
    "failure_count": 2,
    "last_failure_at": "2025-01-17T13:30:00",
    "failure_reasons": ["content_filter", "no_files_changed"]
  }
}
```

### Deprioritization Logic
```python
def get_available_issues(claims: dict, issues: List[dict]) -> List[dict]:
    """Return issues sorted by priority, with high-failure issues last."""
    available = [i for i in issues if str(i['number']) not in claims]

    # Move issues with 3+ failures to end
    def sort_key(issue):
        claim = claims.get(str(issue['number']), {})
        failures = claim.get('failure_count', 0)
        if failures >= 3:
            return (1, failures)  # Deprioritized
        return (0, priority_label_order(issue))  # Normal priority

    return sorted(available, key=sort_key)
```

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Permanent blacklist | Too aggressive; issues may become fixable |
| No tracking | Infinite loops observed in logs |
| Session-level only | Doesn't persist across sessions |

---

## Summary of Decisions

| Research Area | Decision | Key Benefit |
|---------------|----------|-------------|
| Claim TTL | 30-min lazy cleanup | Prevents stale claim blocking |
| Locking | Existing FileLock pattern | Cross-platform, proven |
| Errors | Classified with recovery | Automated recovery, clear debugging |
| Projects | GraphQL via gh CLI | Full Projects v2 support |
| Prompts | Quick Reference consolidation | 20%+ token reduction |
| Outcome Validation | Track specific issues per session | Accurate success metrics |
| Productivity | Score formula with thresholds | Detect unproductive sessions |
| Empty Backlog | 3 consecutive rounds | Graceful termination |
| Failure Tracking | Count per issue, deprioritize | Prevent infinite loops |
