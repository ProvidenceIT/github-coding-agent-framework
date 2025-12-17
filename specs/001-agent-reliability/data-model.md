# Data Model: Agent Reliability Improvements

**Feature**: 001-agent-reliability
**Date**: 2025-12-17

## Entity Definitions

### 1. IssueClaim

Represents a session's lock on a GitHub issue.

**Storage**: `.issue_claims.json` (JSON file in project directory)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| issue_number | string (key) | Yes | GitHub issue number as string key |
| session_id | string | Yes | Unique identifier for claiming session |
| claimed_at | ISO8601 datetime | Yes | When claim was acquired |
| title | string | Yes | Issue title for display |
| failed_at | ISO8601 datetime | No | When last failure occurred (if any) |
| failure_count | integer | No | Number of times this issue has failed |

**State Transitions**:
```
[Unclaimed] --claim--> [Claimed] --success--> [Released/Closed]
                            |
                            +--failure--> [Failed] --TTL expires--> [Unclaimed]
                                             |
                                             +--3+ failures--> [Blocked]
```

**Validation Rules**:
- `claimed_at` must be valid ISO8601
- `session_id` must be non-empty
- `failure_count` defaults to 0 if not present
- Claims older than TTL (30 min default) are considered stale

**Example**:
```json
{
  "42": {
    "session_id": "session_20251217_143022_1",
    "claimed_at": "2025-12-17T14:30:22.123456",
    "title": "Add user authentication",
    "failed_at": "2025-12-17T14:45:00.000000",
    "failure_count": 1
  }
}
```

---

### 2. SessionOutcome

Represents the result of an agent session.

**Storage**: Session logs (JSON Lines in `logs/session_*.jsonl`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| session_id | string | Yes | Session identifier |
| started_at | ISO8601 datetime | Yes | Session start time |
| ended_at | ISO8601 datetime | Yes | Session end time |
| issues_worked | array[integer] | Yes | Issue numbers attempted |
| issues_closed | array[integer] | Yes | Issue numbers successfully closed |
| files_changed | integer | Yes | Count of files modified |
| tool_count | integer | Yes | Total tool invocations |
| productivity_score | float | Yes | Ratio: (issues_closed * 10 + files_changed) / tool_count |
| success | boolean | Yes | True if at least one issue closed |
| health_status | string | Yes | "healthy" | "warning" | "unhealthy" |
| warnings | array[string] | No | Health warning messages |

**Validation Rules**:
- `productivity_score` = 0 if `tool_count` = 0
- `success` = true if `len(issues_closed) > 0`
- `health_status` = "warning" if `productivity_score < 0.1` and `tool_count > 30`

**Example**:
```json
{
  "session_id": "session_20251217_143022_1",
  "started_at": "2025-12-17T14:30:22",
  "ended_at": "2025-12-17T15:05:47",
  "issues_worked": [42, 43],
  "issues_closed": [42],
  "files_changed": 5,
  "tool_count": 45,
  "productivity_score": 0.33,
  "success": true,
  "health_status": "healthy",
  "warnings": []
}
```

---

### 3. GitHubProjectItem

Represents an issue's presence on a GitHub Projects v2 board.

**Storage**: `.github_project.json` (item mappings in project metadata)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| issue_number | integer | Yes | GitHub issue number |
| item_id | string | Yes | GraphQL node ID for project item |
| status | string | Yes | Current column: "Todo" | "In Progress" | "Done" |
| added_at | ISO8601 datetime | Yes | When added to project |
| updated_at | ISO8601 datetime | No | Last status update |

**Storage Context** (parent `.github_project.json`):
```json
{
  "project_id": "PVT_kwDOABC123",
  "project_number": 1,
  "status_field_id": "PVTSSF_abc123",
  "status_options": {
    "Todo": "98f5c...",
    "In Progress": "47d3e...",
    "Done": "f7a2b..."
  },
  "items": {
    "42": {
      "item_id": "PVTI_abc123",
      "status": "In Progress",
      "added_at": "2025-12-17T14:00:00",
      "updated_at": "2025-12-17T14:30:22"
    }
  }
}
```

**State Transitions**:
```
[Not on board] --add--> [Todo] --claim--> [In Progress] --close--> [Done]
```

---

### 4. APIError

Represents a classified error from external APIs.

**Storage**: In-memory (used during error handling)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| source | string | Yes | "claude" | "github" |
| code | integer | Yes | HTTP status code |
| message | string | Yes | Human-readable error description |
| recoverable | boolean | Yes | Whether automated recovery possible |
| action | string | Yes | Recovery action identifier |
| retry_after | integer | No | Seconds to wait before retry (if applicable) |
| original_error | string | No | Original exception message |

**Action Identifiers**:
- `rotate_token` - Try a different API token
- `wait_retry` - Wait and retry (use retry_after)
- `pull_retry` - Git pull then retry
- `manual_review` - Mark for human intervention
- `abort` - Stop processing, non-recoverable

**Example**:
```python
APIError(
    source="github",
    code=429,
    message="Rate limited - waiting",
    recoverable=True,
    action="wait_retry",
    retry_after=60
)
```

---

## Relationships

```
┌─────────────────┐         ┌─────────────────────┐
│   IssueClaim    │◄────────│   SessionOutcome    │
│                 │  works  │                     │
│ issue_number    │  on     │ issues_worked[]     │
│ session_id      │─────────│ issues_closed[]     │
│ claimed_at      │         │ session_id          │
│ failure_count   │         │ productivity_score  │
└─────────────────┘         └─────────────────────┘
        │
        │ syncs to
        ▼
┌─────────────────┐         ┌─────────────────────┐
│GitHubProjectItem│         │     APIError        │
│                 │         │                     │
│ issue_number    │         │ Transient - used    │
│ item_id         │         │ during error        │
│ status          │         │ handling only       │
└─────────────────┘         └─────────────────────┘
```

---

## Storage File Locations

| Entity | File | Format |
|--------|------|--------|
| IssueClaim | `{project_dir}/.issue_claims.json` | JSON object |
| SessionOutcome | `{project_dir}/logs/session_*.jsonl` | JSON Lines |
| GitHubProjectItem | `{project_dir}/.github_project.json` | JSON object |
| APIError | In-memory | Python dataclass |

---

### 5. BacklogState

Tracks empty backlog rounds for graceful termination.

**Storage**: In-memory (managed by ParallelAgentManager)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| consecutive_no_issues | integer | Yes | Rounds where all sessions found no issues |
| threshold | integer | Yes | Rounds before termination (default: 3) |
| last_check | ISO8601 datetime | No | When last round was recorded |

**State Transitions**:
```
[Running] --all sessions empty--> [Counting] --threshold reached--> [Terminated]
              |                        |
              +--any session has work--+--reset counter-->[Running]
```

**Example**:
```python
BacklogState(
    consecutive_no_issues=2,
    threshold=3,
    last_check="2025-12-17T15:00:00"
)
# Next round with all empty sessions would trigger termination
```

---

### 6. ProductivityMetrics

Captures metrics for session health analysis.

**Storage**: Part of SessionOutcome in logs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| tool_count | integer | Yes | Total tool invocations |
| files_changed | integer | Yes | Files with modifications |
| issues_closed | integer | Yes | Issues successfully closed |
| response_length | integer | No | Total response text length |
| score | float | Computed | Productivity score |

**Computed Fields**:
- `score` = `(files_changed * 2 + issues_closed * 5) / max(tool_count, 1)`

**Warning Thresholds**:
- `tool_count >= 30` AND `files_changed == 0`: "Low productivity: N tool calls but 0 files changed"
- `tool_count >= 30` AND `score < 0.1`: "Productivity score X below threshold 0.1"

**Example**:
```python
ProductivityMetrics(
    tool_count=45,
    files_changed=3,
    issues_closed=1,
    response_length=15000
)
# score = (3 * 2 + 1 * 5) / 45 = 0.24 (healthy)
```

---

### 7. ClaimHistoryEntry

Tracks historical claim data for failure analysis.

**Storage**: Optional extension to `.issue_claims.json`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| issue_number | integer | Yes | GitHub issue number |
| total_attempts | integer | Yes | Total claim attempts across sessions |
| successful_closes | integer | Yes | Times issue was successfully closed |
| failure_reasons | array[string] | No | Collected failure reasons |
| last_session | string | No | Session ID of last attempt |

**Example**:
```json
{
  "history": {
    "42": {
      "total_attempts": 3,
      "successful_closes": 1,
      "failure_reasons": ["content_filter", "timeout"],
      "last_session": "session_20251217_150000_1"
    }
  }
}
```

---

## Migration Notes

**Existing `.issue_claims.json` format** does not have `failed_at` or `failure_count` fields. Migration strategy:
- Read existing claims without these fields
- Default `failure_count = 0` and `failed_at = None`
- New fields written on next save
- No explicit migration script needed (additive change)

**Existing `.github_project.json` format** may not have `items` mapping. Migration strategy:
- Check for `items` key on load
- Initialize empty `items = {}` if missing
- Populate on first issue add operation
