# Deep Analysis of Autonomous Agent Issues

Date: 2025-12-12
Analyzed by: Claude Sonnet 4.5

## Executive Summary

The autonomous coding agent framework is experiencing critical failures that prevent meaningful work:
- **0% completion rate** across all sessions
- **100% health check failure rate** despite active tool usage
- Agent spends entire 25-turn budget on orientation, never implementing features
- No GitHub project or META issue created

## Root Cause Analysis

### Issue #1: Broken Health Check Logic ⚠️ CRITICAL

**Location:** `autonomous_agent_fixed.py:97-207` and `autonomous_agent_fixed.py:330-338`

**Problem:**
The health check function searches for tool usage patterns in the agent's TEXT response, but tool calls are separate message blocks in Claude Code SDK. The function finds 0 matches and marks session as unhealthy, even though 24-25 actual tool calls occurred.

**Code Flow:**
```python
# Line 332: Health check called with TEXT ONLY
health_status = analyze_session_health(full_response_text, session_id, logger)

# Inside analyze_session_health:
# Line 129-143: Searches for tool patterns like '<invoke name="..."' in TEXT
# Line 156: Finds 0 matches → sets is_healthy = False

# Line 335: Tool count is overridden with actual count (24-25)
health_status['tool_calls_count'] = tool_count

# BUT: is_healthy stays False! The damage is already done.
```

**Evidence from Logs:**
```
INFO: Tool calls detected: 25
WARNING: Health check failed: No tool usage detected
WARNING: - No tool usage detected - agent may not be doing any work
```

**Impact:**
- All sessions marked unhealthy despite working correctly
- Retries triggered unnecessarily
- Confusing logs that report both "25 tool calls" and "no tool usage"

---

### Issue #2: Prompt Drives Excessive Exploration

**Location:** `prompts/coding_prompt.md:9-52`

**Problem:**
The prompt instructs the agent to run 5+ bash commands in Step 1 (Get Your Bearings), then check GitHub status with multiple commands in Step 2. With fresh context each session, agents spend 15-20 turns just orienting before any work.

**Prompt Analysis:**
```markdown
### STEP 1: GET YOUR BEARINGS (MANDATORY)
- pwd
- ls -la
- cat app_spec.txt
- cat .github_project.json
- git log --oneline -20

### STEP 2: CHECK GITHUB STATUS
- gh issue list --search "[META]"
- gh issue list --state open
- gh issue list --state closed
- gh project item-list
```

**Observed Behavior:**
- Session 3: 24 tool calls, all exploration (pwd, git status, reading files repeatedly)
- Session 4: 25 tool calls, all exploration, hit turn limit
- Session 5: 25 tool calls, mostly exploration, hit turn limit

**Impact:**
- Agent never reaches Step 3+ (actual implementation)
- 100% of turn budget consumed by orientation
- No progress made despite agent functioning correctly

---

### Issue #3: Turn Limit Too Low

**Location:** `autonomous_agent_fixed.py:760`

**Problem:**
```python
max_turns=25  # REDUCED from 50 to prevent context bloat
```

With current prompt structure requiring 15-20 turns for orientation, only 5-10 turns remain for actual work. Complex issues require 30-50+ turns to implement and verify.

**Impact:**
- Agent hits limit before completing single issue
- Orientation overhead consumes majority of budget
- Reduced from 50 → 25 to prevent "context bloat", but this makes agent ineffective

---

### Issue #4: No State Persistence

**Problem:**
Each session starts with fresh context, no memory of:
- What files exist
- What's been explored
- Current project structure
- Previous session findings

**Impact:**
- Same exploration repeated every session
- `pwd`, `ls -la`, `cat app_spec.txt` run in EVERY session
- Wasted turns on redundant operations
- No learning or cumulative progress

---

### Issue #5: Agent Has Adequate Tools But Poor Guidance

**Available Tools:** ✅ Sufficient
- Bash, Read, Write, Edit, Glob, Grep
- GitHub CLI (gh)
- Puppeteer for browser testing
- Git operations

**Guidance Issues:** ❌ Problems
- Prompt too prescriptive about HOW to explore
- No guidance on minimizing redundant operations
- No clear success criteria per session
- No instruction to skip orientation if files already read

---

## Comprehensive Fix Plan

### Fix #1: Repair Health Check Logic

**File:** `autonomous_agent_fixed.py`

**Change:** Move tool count override BEFORE health check analysis
```python
# BEFORE (line 330-335):
health_status = analyze_session_health(full_response_text, session_id, logger)
health_status['tool_calls_count'] = tool_count  # Too late!

# AFTER:
# Pass tool_count directly to health check function
health_status = analyze_session_health(full_response_text, session_id, logger, tool_count=tool_count)
```

**Function signature change:**
```python
def analyze_session_health(response: str, session_id: str, logger: logging.Logger = None, tool_count: int = None) -> dict:
    """
    Analyze the session response to detect if the agent is doing meaningful work.

    Args:
        tool_count: Actual number of tool calls made (from SDK). If provided, this
                   overrides pattern-based detection.
    """
    # ... existing code ...

    # If actual tool count provided, use it directly
    if tool_count is not None:
        health_status['tool_calls_count'] = tool_count
    else:
        # Fall back to pattern matching (legacy)
        tool_matches = []
        for pattern in tool_patterns:
            matches = re.findall(pattern, response_str, re.IGNORECASE)
            tool_matches.extend(matches)
        health_status['tool_calls_count'] = len(tool_matches)

    # Check 3: No tool usage detected
    if health_status['tool_calls_count'] == 0:
        health_status['is_healthy'] = False
        # ... rest of check
```

---

### Fix #2: Optimize Prompt for Efficiency

**File:** `prompts/coding_prompt.md`

**Changes:**

1. **Streamline Step 1:**
```markdown
### STEP 1: GET YOUR BEARINGS (QUICK!)

Run this ONCE at the start:
```bash
pwd && ls -la
```

Then read ONLY files you haven't seen before in this context:
- app_spec.txt (if you don't know what you're building)
- .github_project.json (if you need GitHub IDs)
- .initialized (to check setup status)

**DON'T repeatedly run pwd, ls, git log if you've already done it this session.**
```

2. **Add efficiency guidance:**
```markdown
### EFFICIENCY RULES

- Minimize exploration - you have limited turns
- Don't re-read files you've already read this session
- Use `gh issue view NUMBER` to read ONE issue, not `gh issue list` repeatedly
- Parallel tool calls when possible (read multiple files at once)
- Skip orientation if you remember the project structure
```

3. **Add session success criteria:**
```markdown
### SESSION SUCCESS CRITERIA

A successful session means AT LEAST ONE of:
✅ 1+ GitHub issue closed with implementation + verification
✅ META issue created with project breakdown
✅ GitHub project initialized
✅ Critical bug fixed
✅ Infrastructure set up that unblocks multiple issues

If after 10 turns you haven't started actual work, STOP exploring and START implementing.
```

---

### Fix #3: Increase Turn Limit with Safeguards

**File:** `autonomous_agent_fixed.py:760`

**Change:**
```python
# OLD:
max_turns=25  # REDUCED from 50 to prevent context bloat

# NEW:
max_turns=50  # Sufficient for orientation + implementation + verification
```

**Justification:**
- Current prompt requires 15-20 turns for mandatory orientation
- Complex issues need 20-30 turns for implementation
- Verification + GitHub updates need 5-10 turns
- Total: 40-60 turns for complete issue lifecycle
- 50 is reasonable middle ground

**Safeguards:**
- Keep health checks to detect actual stalls
- Prompt now instructs efficiency
- Monitor for context bloat in logs

---

### Fix #4: Add State Hints to Prompt

**File:** `autonomous_agent_fixed.py` (in prompt generation)

**Add to beginning of coding prompt:**
```markdown
## CONTEXT REMINDER

You have NO memory of previous sessions, but the state is preserved in:
- Git history: `git log --oneline -5` shows recent work
- GitHub issues: `gh issue list --state closed` shows completed features
- File structure: If files exist, they've been created already
- .initialized: If exists, setup is complete

**SKIP redundant exploration!** If files exist and you understand the structure,
start working immediately.
```

---

### Fix #5: Add Progress Checkpointing

**New file:** `progress.py`

Create lightweight state tracker:
```python
"""
Progress checkpointing for session efficiency.
Records basic state to avoid redundant exploration.
"""
from pathlib import Path
import json
from datetime import datetime

def save_session_checkpoint(project_dir: Path, data: dict):
    """Save session checkpoint."""
    checkpoint_file = project_dir / ".session_checkpoint.json"
    data['timestamp'] = datetime.now().isoformat()
    checkpoint_file.write_text(json.dumps(data, indent=2))

def load_session_checkpoint(project_dir: Path) -> dict:
    """Load last session checkpoint."""
    checkpoint_file = project_dir / ".session_checkpoint.json"
    if checkpoint_file.exists():
        return json.loads(checkpoint_file.read_text())
    return {}

def get_orientation_summary(project_dir: Path) -> str:
    """Generate quick orientation summary for prompt injection."""
    checkpoint = load_session_checkpoint(project_dir)
    if not checkpoint:
        return "No previous session data."

    return f"""
## PREVIOUS SESSION SUMMARY
Last session: {checkpoint.get('timestamp', 'unknown')}
Issues closed last session: {checkpoint.get('issues_closed', [])}
Current focus: {checkpoint.get('current_focus', 'none')}
Files modified: {len(checkpoint.get('modified_files', []))}

You can skip basic orientation and jump to checking GitHub status.
"""
```

**Inject into prompt:** Add `get_orientation_summary()` output to coding prompt.

---

## Implementation Priority

### CRITICAL (Fix Immediately):
1. **Fix #1: Health Check Logic** - 5 minutes
   - Prevents false failures
   - Restores confidence in health monitoring

### HIGH (Fix Today):
2. **Fix #2: Optimize Prompt** - 15 minutes
   - Immediate impact on agent efficiency
   - Reduces wasted turns

3. **Fix #3: Increase Turn Limit** - 1 minute
   - Simple change, big impact
   - Gives agent room to work

### MEDIUM (Fix This Week):
4. **Fix #5: Progress Checkpointing** - 30 minutes
   - Reduces redundant exploration
   - Cumulative improvement over sessions

5. **Fix #4: State Hints** - 10 minutes
   - Improves prompt awareness
   - Easy win

---

## Expected Outcomes After Fixes

### Before Fixes:
- ❌ 0% completion rate
- ❌ 100% health check failure rate
- ❌ 0 issues closed
- ❌ All turns spent on orientation
- ❌ No META issue created

### After Fixes:
- ✅ 60-80% successful session rate
- ✅ Accurate health check detection
- ✅ 1-2 issues closed per session
- ✅ 30-40% of turns on orientation, 60-70% on work
- ✅ META issue created in first session
- ✅ Meaningful progress visible in git log

---

## Testing Plan

After implementing fixes:

1. **Dry run** with existing test_fresh project:
   ```bash
   python autonomous_agent_fixed.py --max-iterations 3
   ```

2. **Validate:**
   - Health checks pass for working sessions
   - At least 1 issue closed in first 3 iterations
   - META issue exists
   - Git commits show actual code, not just config

3. **Monitor:**
   - Turn usage distribution (orientation vs work)
   - Health check false positive rate
   - Issues closed per iteration

---

## Long-term Recommendations

### Architecture:
1. **Separate orientation agent from implementation agent**
   - Orientation runs ONCE at project start
   - Implementation agent gets pre-digested context

2. **Caching layer for expensive operations**
   - Cache `gh issue list` results
   - Cache file tree structure
   - Invalidate on file changes

3. **Adaptive turn limits**
   - More turns for complex issues (database, auth)
   - Fewer turns for simple issues (UI tweaks)

### Prompt engineering:
1. **Add examples of efficient sessions**
   - Show good session: 5 orientation turns, 40 work turns
   - Show bad session: 20 orientation turns, timeout

2. **Explicit anti-patterns**
   - Don't run `pwd` more than once
   - Don't run `git log` repeatedly
   - Don't read entire app_spec.txt every time

### Monitoring:
1. **Turn usage metrics**
   - Track % of turns spent on each step
   - Alert if >40% spent on orientation

2. **Progress velocity**
   - Issues closed per iteration
   - Lines of code per iteration
   - Features completed per hour

---

## Conclusion

The agent has all necessary tools and is functioning correctly. The issues are:
1. **Broken health check** giving false negatives
2. **Inefficient prompt** causing excessive exploration
3. **Too-low turn limit** preventing completion
4. **No state persistence** forcing repeated work

All issues are fixable with code changes. No fundamental redesign needed.

**Recommended action:** Implement Critical and High priority fixes immediately (20 minutes total), test, then iterate on Medium priority improvements.
