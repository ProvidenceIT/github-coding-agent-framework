# Contract: Graceful Termination

**Module**: `parallel_agent.py`
**Class**: `ParallelAgentManager`

## Interface

### Configuration

```python
class ParallelAgentManager:
    MAX_NO_ISSUES_ROUNDS = 3  # Terminate after N consecutive rounds with no issues
```

| Constant | Default | Description |
|----------|---------|-------------|
| MAX_NO_ISSUES_ROUNDS | 3 | Consecutive rounds before graceful termination |

---

### Session Return Values

Sessions now return typed status strings:

| Return Value | Meaning |
|--------------|---------|
| `"SUCCESS"` | Session completed, issue closed |
| `"FAILED"` | Session failed, issue not closed |
| `"NO_ISSUES"` | No unclaimed issues available |
| `"BLOCKED"` | Issue blocked (content filtering, etc.) |
| `"ERROR"` | Unexpected error occurred |

---

### Termination Logic

```python
async def run_parallel(self, num_iterations: int = 1):
    consecutive_no_issues = 0

    for iteration in range(1, num_iterations + 1):
        results = await self._run_iteration(iteration)

        # Count sessions that found no issues
        no_issues_count = sum(1 for r in results if r == "NO_ISSUES")

        if no_issues_count == len(results):
            # ALL sessions reported no issues
            consecutive_no_issues += 1
            logger.info(f"No issues round {consecutive_no_issues}/{MAX_NO_ISSUES_ROUNDS}")

            if consecutive_no_issues >= self.MAX_NO_ISSUES_ROUNDS:
                print(f"\n{'='*60}")
                print("  ALL ISSUES COMPLETE - Stopping agent")
                print(f"{'='*60}\n")
                break  # Graceful termination
        else:
            # At least one session found work - reset counter
            consecutive_no_issues = 0
```

---

### Behavior Specification

| Scenario | Behavior |
|----------|----------|
| All 3 sessions return NO_ISSUES | Increment counter |
| 2 sessions return NO_ISSUES, 1 returns SUCCESS | Reset counter to 0 |
| Counter reaches MAX_NO_ISSUES_ROUNDS | Log termination, break loop |
| New issue created mid-run | Next iteration finds it, counter resets |

---

### Output Messages

**During countdown:**
```
No issues round 1/3 - checking again...
No issues round 2/3 - checking again...
No issues round 3/3 - terminating
```

**On termination:**
```
============================================================
  ALL ISSUES COMPLETE - Stopping agent
============================================================
```

---

### Integration with _run_single_session

```python
async def _run_single_session(self, iteration: int, session_num: int, ...) -> str:
    issue_num = self.issue_lock.claim_issue(session_id)

    if not issue_num:
        self._log(session_id, "No unclaimed issues available")
        return "NO_ISSUES"  # Distinct return value

    # ... do work ...

    if success:
        return "SUCCESS"
    else:
        return "FAILED"
```

---

### Edge Cases

| Edge Case | Handling |
|-----------|----------|
| Mix of NO_ISSUES and SUCCESS | Only increment if ALL sessions report NO_ISSUES |
| Iteration limit reached before termination | Normal exit (no special message) |
| Error during session | Don't count as NO_ISSUES (could be transient) |
| GitHub API failure listing issues | Treat as error, not NO_ISSUES |

---

## Usage Example

```python
manager = ParallelAgentManager(
    project_dir=project_dir,
    concurrent=3
)

# Will auto-terminate when backlog depleted
await manager.run_parallel(num_iterations=100)
# Exits early if 3 consecutive rounds find no issues
```
