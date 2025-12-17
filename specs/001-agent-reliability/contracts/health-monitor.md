# Contract: Enhanced Health Monitor

**Module**: `autonomous_agent_fixed.py`
**Function**: `analyze_session_health`

## Interface

### analyze_session_health

Analyze session response for health and productivity.

```python
def analyze_session_health(
    response: str,
    session_id: str,
    logger: logging.Logger = None,
    tool_count: int = None,
    files_changed: int = 0,
    issues_closed: int = 0
) -> Dict[str, Any]
```

**Input**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| response | str | Yes | - | Agent response text |
| session_id | str | Yes | - | Session identifier |
| logger | Logger | No | None | Optional logger |
| tool_count | int | No | None | Actual tool calls (from SDK) |
| files_changed | int | No | 0 | **NEW**: Files modified |
| issues_closed | int | No | 0 | **NEW**: Issues closed |

**Output**: Dictionary with health metrics:

| Field | Type | Description |
|-------|------|-------------|
| is_healthy | bool | Overall health status |
| warnings | List[str] | Warning messages |
| tool_calls_count | int | Number of tool invocations |
| response_length | int | Response character count |
| has_content | bool | Whether response has meaningful content |
| productivity_score | float | **NEW**: Ratio of outcomes to effort |
| productive | bool | **NEW**: Whether session is productive |

---

## Productivity Calculation

```python
# Productivity formula
if tool_count and tool_count > 0:
    productivity_score = (issues_closed * 10 + files_changed) / tool_count
else:
    productivity_score = 0.0

# Thresholds
PRODUCTIVITY_THRESHOLD = 0.1
MIN_TOOLS_FOR_WARNING = 30

productive = True
if productivity_score < PRODUCTIVITY_THRESHOLD and tool_count > MIN_TOOLS_FOR_WARNING:
    productive = False
    warnings.append(
        f"Low productivity: {tool_count} tools but only {files_changed} files changed"
    )
```

---

## Health Check Matrix

| Check | Threshold | Result |
|-------|-----------|--------|
| Empty response | < 10 chars | is_healthy = False |
| No tool usage | 0 tools | is_healthy = False |
| Low productivity | score < 0.1 AND tools > 30 | productive = False, warning added |
| Stall phrases detected | Contains "I apologize", "stuck" | warning added |
| Error indicators | Contains traceback, exception | warning added |

---

## Productivity Score Examples

| Scenario | Formula | Score | Status |
|----------|---------|-------|--------|
| 1 issue, 5 files, 40 tools | (1*10 + 5) / 40 | 0.375 | Healthy |
| 0 issues, 0 files, 50 tools | (0*10 + 0) / 50 | 0.0 | Warning |
| 0 issues, 3 files, 20 tools | (0*10 + 3) / 20 | 0.15 | Healthy |
| 0 issues, 2 files, 35 tools | (0*10 + 2) / 35 | 0.057 | Warning |

---

## Integration

### In parallel_agent.py

```python
# After session completes
files_changed = count_modified_files(project_dir)
issues_closed = len(outcome.get('issues_closed_list', []))

health = analyze_session_health(
    response=response,
    session_id=session_id,
    tool_count=actual_tool_count,
    files_changed=files_changed,
    issues_closed=issues_closed
)

if not health['productive']:
    logger.warning(f"Session {session_id} has low productivity")
    for warning in health['warnings']:
        logger.warning(f"  - {warning}")
```

---

## Configuration Constants

| Constant | Default | Description |
|----------|---------|-------------|
| PRODUCTIVITY_THRESHOLD | 0.1 | Minimum acceptable productivity score |
| MIN_TOOLS_FOR_WARNING | 30 | Minimum tool calls before productivity check |
| MIN_RESPONSE_LENGTH | 10 | Minimum response length for health |

---

## Output Example

```python
{
    "is_healthy": True,
    "warnings": ["Low productivity: 45 tools but only 2 files changed"],
    "tool_calls_count": 45,
    "response_length": 15234,
    "has_content": True,
    "productivity_score": 0.044,
    "productive": False
}
```
