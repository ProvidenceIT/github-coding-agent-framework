# Contract: Session Outcome Validator

**Module**: `autonomous_agent_fixed.py`
**Function**: `check_session_mandatory_outcomes`

## Interface

### check_session_mandatory_outcomes

Validate session achieved mandatory outcomes by checking specific issues.

```python
def check_session_mandatory_outcomes(
    project_dir: Path,
    repo: str,
    issues_worked: List[int],
    logger: logging.Logger = None
) -> Dict[str, Any]
```

**Input**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| project_dir | Path | Yes | Project directory |
| repo | str | Yes | GitHub repo (e.g., "owner/repo") |
| issues_worked | List[int] | Yes | **NEW**: Issue numbers this session worked on |
| logger | Logger | No | Optional logger instance |

**Output**: Dictionary with:
| Field | Type | Description |
|-------|------|-------------|
| success | bool | True if at least one issue closed |
| issues_worked | List[int] | Issues attempted (input echo) |
| issues_closed | int | Count of issues successfully closed |
| issues_closed_list | List[int] | **NEW**: Specific issue numbers closed |
| meta_updated | bool | Whether META issue was updated |
| git_pushed | bool | Whether changes were pushed |
| failures | List[str] | Failure messages if any |

---

## Behavior Changes

### OLD (Time-based)
```python
# Check for recently closed issues (within last hour)
issues = gh_issue_list(state='closed', since=1_hour_ago)
result['issues_closed'] = len(issues)
```

### NEW (Issue-specific)
```python
# Check SPECIFIC issues we worked on
for issue_num in issues_worked:
    state = gh_issue_view(issue_num, '--json', 'state')
    if state == 'CLOSED':
        result['issues_closed'] += 1
        result['issues_closed_list'].append(issue_num)

if result['issues_closed'] == 0 and len(issues_worked) > 0:
    result['failures'].append(
        f"Worked on {len(issues_worked)} issues but none were closed: {issues_worked}"
    )
```

---

## Validation Logic

1. **Issue Closure Check**: For each issue in `issues_worked`, query GitHub for current state
2. **Success Determination**: `success = issues_closed > 0`
3. **Failure Messages**: Include specific issue numbers that weren't closed
4. **META Update Check**: Look for recent activity on META issue (optional)
5. **Git Push Check**: Verify local branch is pushed to remote

---

## Usage Example

```python
# In parallel_agent.py session completion
outcome = check_session_mandatory_outcomes(
    project_dir=project_dir,
    repo=repo,
    issues_worked=[42, 43],  # Specific issues this session claimed
    logger=logger
)

if outcome['success']:
    print(f"Session succeeded: {outcome['issues_closed']}/{len(issues_worked)} issues closed")
else:
    for failure in outcome['failures']:
        print(f"FAILURE: {failure}")
```

---

## Error Handling

| Scenario | Handling |
|----------|----------|
| GitHub API timeout | Log warning, mark issue as "unknown" state |
| Issue not found (404) | Treat as not closed, log warning |
| Rate limit (429) | Wait and retry once |
| Auth error (401) | Log error, treat as validation failure |
