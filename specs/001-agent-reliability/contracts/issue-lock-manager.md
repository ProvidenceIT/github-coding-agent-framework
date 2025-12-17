# Contract: IssueLockManager

**Module**: `parallel_agent.py`
**Class**: `IssueLockManager`

## Interface

### Constructor

```python
def __init__(self, project_dir: Path, repo: str, claim_ttl_minutes: int = 30)
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| project_dir | Path | Yes | - | Project directory for claim file storage |
| repo | str | Yes | - | GitHub repo (e.g., "owner/repo") |
| claim_ttl_minutes | int | No | 30 | Time-to-live for claims in minutes |

---

### claim_issue

Atomically claim the next available issue.

```python
def claim_issue(self, session_id: str) -> Optional[int]
```

**Input**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| session_id | str | Yes | Unique session identifier |

**Output**: `Optional[int]`
- Issue number if claimed successfully
- `None` if no issues available

**Behavior**:
1. Acquire file lock
2. Load existing claims
3. **NEW**: Clean up stale claims (older than TTL)
4. Query GitHub for open issues (sorted by priority)
5. Skip META issues and already-claimed issues
6. **NEW**: Skip issues with failure_count >= 3 (or flag for review)
7. Claim first available issue
8. Save claims and release lock
9. Post claim comment on GitHub issue

**Error Handling**:
- Lock acquisition timeout: Return `None`, log warning
- GitHub API failure: Return `None`, log error
- File I/O error: Raise exception (critical)

---

### release_issue

Release claim on an issue.

```python
def release_issue(self, issue_num: int, session_id: str, was_closed: bool = False)
```

**Input**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| issue_num | int | Yes | - | Issue number to release |
| session_id | str | Yes | - | Session that owns the claim |
| was_closed | bool | No | False | Whether issue was successfully closed |

**Output**: `None`

**Behavior (NEW)**:
- If `was_closed = True`: Remove claim entirely (success path)
- If `was_closed = False`: Mark as failed, increment failure_count, keep claim with `failed_at` timestamp

---

### get_active_claims

Get all active claims.

```python
def get_active_claims(self) -> Dict[str, Dict]
```

**Output**: Dictionary of issue_number (str) -> claim data

---

### _cleanup_stale_claims (NEW)

Remove claims older than TTL.

```python
def _cleanup_stale_claims(self, claims: Dict) -> Dict
```

**Behavior**:
1. For each claim, check if `claimed_at` is older than TTL
2. Remove stale claims
3. Log cleanup actions
4. Return modified claims dict

---

## File Format

**Location**: `{project_dir}/.issue_claims.json`

```json
{
  "42": {
    "session_id": "session_20251217_143022_1",
    "claimed_at": "2025-12-17T14:30:22.123456",
    "title": "Add user authentication",
    "failed_at": null,
    "failure_count": 0
  },
  "43": {
    "session_id": "session_20251217_143022_2",
    "claimed_at": "2025-12-17T14:31:00.000000",
    "title": "Fix login bug",
    "failed_at": "2025-12-17T14:45:00.000000",
    "failure_count": 1
  }
}
```

---

## Configuration

| Constant | Default | Description |
|----------|---------|-------------|
| CLAIM_TTL_MINUTES | 30 | Time before stale claims are cleaned up |
| MAX_FAILURE_COUNT | 3 | Failures before issue is deprioritized |

---

## Usage Example

```python
from parallel_agent import IssueLockManager

lock_mgr = IssueLockManager(
    project_dir=Path("./generations/my_project"),
    repo="owner/my-project",
    claim_ttl_minutes=30
)

# Claim an issue
issue_num = lock_mgr.claim_issue("session_001")
if issue_num:
    try:
        # ... do work ...
        success = close_issue(issue_num)
        lock_mgr.release_issue(issue_num, "session_001", was_closed=success)
    except Exception:
        lock_mgr.release_issue(issue_num, "session_001", was_closed=False)
```
