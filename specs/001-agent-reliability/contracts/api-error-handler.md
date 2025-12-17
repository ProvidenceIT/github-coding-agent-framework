# Contract: API Error Handler

**Module**: `github_cache.py` (GitHub), `parallel_agent.py` (Claude)
**Classes**: `GitHubAPIError`, `ClaudeAPIError`

## Interface

### GitHubAPIError

Exception for classified GitHub API errors.

```python
class GitHubAPIError(Exception):
    def __init__(
        self,
        status_code: int,
        message: str,
        recoverable: bool = False,
        action: str = "abort",
        retry_after: int = None
    )
```

| Field | Type | Description |
|-------|------|-------------|
| status_code | int | HTTP status code |
| message | str | Human-readable error description |
| recoverable | bool | Whether automated recovery is possible |
| action | str | Recovery action identifier |
| retry_after | int | Seconds to wait before retry (optional) |

---

### execute_gh_command

Execute gh CLI with error classification.

```python
def execute_gh_command(
    cmd: List[str],
    cwd: Path,
    timeout: int = 30
) -> Tuple[bool, str, str]
```

**Input**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| cmd | List[str] | Yes | - | Command parts (e.g., ['gh', 'issue', 'list']) |
| cwd | Path | Yes | - | Working directory |
| timeout | int | No | 30 | Command timeout in seconds |

**Output**: `Tuple[bool, str, str]`
- `(success, stdout, stderr)`

**Raises**: `GitHubAPIError` on classified errors

---

## Error Classification Table

| HTTP Code | Error Type | recoverable | action | retry_after |
|-----------|------------|-------------|--------|-------------|
| 400 | Bad Request | No | `abort` | - |
| 401 | Unauthorized | No | `check_auth` | - |
| 403 | Forbidden | No | `check_permissions` | - |
| 404 | Not Found | No | `abort` | - |
| 409 | Conflict | Yes | `pull_retry` | - |
| 422 | Unprocessable | No | `fix_input` | - |
| 429 | Rate Limited | Yes | `wait_retry` | Retry-After header |
| 500 | Server Error | Yes | `wait_retry` | 30 |
| 502 | Bad Gateway | Yes | `wait_retry` | 10 |
| 503 | Unavailable | Yes | `wait_retry` | 30 |

---

### Claude API Error Handling

In `parallel_agent.py._run_single_session`:

```python
async def _run_single_session(self, ...):
    try:
        await client.query(prompt)
        # ... process response ...
    except Exception as e:
        error = classify_claude_error(e)

        if error.action == "content_filter":
            await self._mark_issue_blocked(issue_num, "Content filtering")
            return f"Blocked: Issue #{issue_num}"

        elif error.action == "rotate_token":
            rotator.rotate(reason="auth error")
            if retry_attempt == 0:
                return await self._run_single_session(..., retry_attempt=1)

        elif error.action == "wait_retry":
            await asyncio.sleep(error.retry_after or 30)
            if retry_attempt == 0:
                return await self._run_single_session(..., retry_attempt=1)

        raise  # Non-recoverable
```

---

## Claude Error Classification

| Error Pattern | action | recoverable |
|---------------|--------|-------------|
| "content filtering" | `content_filter` | No (mark for review) |
| "blocked" | `content_filter` | No |
| "401", "unauthorized" | `rotate_token` | Maybe (try once) |
| "500", "server error" | `wait_retry` | Yes |
| "overloaded" | `wait_retry` | Yes |
| "rate limit" | `wait_retry` | Yes |

---

## Usage Example

```python
from github_cache import execute_gh_command, GitHubAPIError

try:
    success, stdout, stderr = execute_gh_command(
        ['gh', 'issue', 'close', '42', '--repo', 'owner/repo'],
        cwd=project_dir
    )
except GitHubAPIError as e:
    if e.recoverable:
        if e.action == "wait_retry":
            time.sleep(e.retry_after or 30)
            # Retry operation
        elif e.action == "pull_retry":
            subprocess.run(['git', 'pull'], cwd=project_dir)
            # Retry operation
    else:
        logger.error(f"Non-recoverable: {e.message}")
        raise
```
