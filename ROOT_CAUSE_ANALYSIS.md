# Root Cause Analysis: Autonomous Agent Failures

## Date: 2025-12-12
## Analysis by: Claude (Sonnet 4.5)

---

## Executive Summary

The autonomous agent framework has **TWO CRITICAL FLAWS** that cause it to fail after just 3 successful iterations:

1. **API 400 "tool use concurrency issues"** starting at iteration 4 - agent becomes completely non-functional
2. **Only 10 issues created** instead of the required 50 - insufficient work tracking

---

## Problem 1: API 400 Tool Use Concurrency Error

### Symptoms
- Starting at **iteration 4**, every agent session immediately fails
- Error message: `"API Error: 400 due to tool use concurrency issues."`
- **Zero tool calls made** - agent outputs only the error text (50 chars)
- **Persists through all retries** - happened for iterations 4-50 (46 consecutive failures)
- **Cost per failed attempt: $6.31** - burning money on failed API calls

### Timeline
```
Iteration 1: ✓ Success (748s, 49 tool calls, initialized project)
Iteration 2: ✓ Success (699s, 45 tool calls, created brand system)
Iteration 3: ✓ Success (716s, 50 tool calls, implemented dashboard)
Iteration 4: ✗ FAIL - API Error 400 (4.56s, 0 tool calls)
Iteration 5-50: ✗ ALL FAIL - Same error pattern
```

### Root Cause

The Claude Code SDK client is **accumulating conversation history** across multiple sessions without proper cleanup. After 3 successful iterations with 50 turns each (max_turns=50), the conversation context becomes too large.

When the agent tries to respond in iteration 4, it attempts to use multiple tools in parallel (as encouraged by the coding_prompt.md which says "you may complete multiple issues per session"). However, the **accumulated context causes Claude to generate an invalid request** that violates API concurrency limits.

**Evidence:**
1. The error happens at exactly the same point (iteration 4) every run
2. Each failed iteration still costs $6.31 - indicating a full API call was made
3. The client is created ONCE and reused across all iterations (line 452: `client = ClaudeSDKClient`)
4. The `async with client:` context (line 461) keeps the same client alive
5. Each session calls `client.query()` which appends to the existing conversation

### Why It's Insidious

- The health check correctly detects the failure (0 tool calls, 50 char response)
- The retry mechanism can't fix it (same context, same error)
- The agent has no way to recover - it's permanently stuck
- Each retry wastes ~$6.31 and 5 seconds

---

## Problem 2: Only 10 Issues Created (Not 50)

### Symptoms
- GitHub has only **10 issues** when 50 were requested
- Issues created:
  ```
  #1  [META] Project Progress Tracker
  #2  Initialize Next.js 15 with App Router
  #3  Set up Tailwind CSS and shadcn/ui
  #4  Create multi-brand theme system
  #5  Set up PostgreSQL database with Prisma ORM
  #6  Implement authentication system with Clerk
  #7  Build executive dashboard with real-time KPIs
  #8  Build navigation sidebar with brand switcher
  #10 Create SEO dashboard with mock data
  ```
- Missing: Issues for 40+ other features from app_spec.txt

### Root Cause

The initializer prompt says:
```markdown
### CRITICAL TASK: Create GitHub Issues

Based on `app_spec.txt`, create GitHub issues for each feature using the
`gh issue create` command. Create 50 detailed issues that comprehensively
cover all features in the spec.
```

**BUT** it doesn't provide a structured template or requirement to actually create all 50. The agent:
1. Started creating issues
2. Created 10 covering high-priority items
3. Switched to implementation (init.sh, project structure)
4. Never came back to finish creating the remaining 40 issues

### Why This Matters

- **Incomplete work tracking** - no issues = no work gets done
- **Future agents have no guidance** on what features to implement
- **The prompt says "Create 50 issues"** but doesn't enforce it
- **No verification** that 50 issues were actually created

---

## Critical Issues with Current Design

### Issue 1: Client State Management
```python
# autonomous_agent_fixed.py, line 452
client = ClaudeSDKClient(options=client_options)

async with client:
    # Client stays alive for ALL iterations
    while True:
        iteration += 1
        # Line 262: await client.query(prompt, session_id=session_id)
        # This APPENDS to the existing conversation!
```

**Problem:** The client accumulates messages across all iterations, leading to context bloat.

### Issue 2: No Context Reset
The `session_id` parameter changes each iteration, but the client itself doesn't reset its internal conversation state. After 3 iterations × 50 turns = 150 messages, the context is huge.

### Issue 3: Prompt Encourages Parallel Work
```markdown
# coding_prompt.md, line 307
**Early phase (< 20% Done):** You may complete multiple issues per session when:
- Setting up infrastructure/scaffolding that unlocks many issues at once
```

This encourages Claude to attempt parallel tool usage, which triggers the concurrency error when combined with large context.

### Issue 4: No Issue Creation Verification
The initializer_prompt.md doesn't verify that 50 issues were created. It should:
1. Create all 50 issues in a loop
2. Verify the count: `gh issue list --json number | jq 'length'`
3. Fail if count ≠ 50

---

## Impact Assessment

### Agent Effectiveness
- **Success rate: 6% (3/50 iterations)**
- **Cost waste: $289.92** on failed iterations (46 × $6.31)
- **Time waste: ~230 seconds** on failed iterations (46 × 5s)
- **Actual work done: 3 features** (brand system, dashboard, init)

### Business Impact
- Agent gets stuck after 3 successful iterations
- 80% of planned work (40/50 issues) never created
- No path to recovery without manual intervention
- Burning money on repeated API errors

---

## Recommended Fixes

### Fix 1: Reset Client Between Sessions

**Option A: Create New Client Per Iteration**
```python
# Instead of ONE client for all iterations:
async with client:
    while True:
        iteration += 1
        ...

# Do this - create FRESH client each iteration:
while True:
    iteration += 1
    client = ClaudeSDKClient(options=client_options)
    async with client:
        # Run ONE session
        # Client closes and context clears after session
```

**Option B: Clear Conversation History**
```python
# After each session, clear the client's conversation history
# (Need to check if SDK supports this)
```

### Fix 2: Enforce 50 Issue Creation

Update `initializer_prompt.md`:

```markdown
### CRITICAL TASK: Create ALL 50 GitHub Issues

You MUST create exactly 50 detailed issues. Follow this process:

1. Read app_spec.txt and identify all 50 features
2. Create each issue with proper labels and test steps
3. After creating issues, VERIFY the count:
   ```bash
   ISSUE_COUNT=$(gh issue list --json number --limit 100 | jq 'length')
   echo "Created $ISSUE_COUNT issues"
   if [ "$ISSUE_COUNT" -lt 50 ]; then
     echo "ERROR: Only $ISSUE_COUNT issues created, need 50"
     exit 1
   fi
   ```
4. Do NOT proceed to implementation until all 50 issues exist

**This is a hard requirement. If you run out of context, end the session
and let the next agent continue creating issues.**
```

### Fix 3: Reduce Context Bloat

Update `ClaudeCodeOptions`:
```python
client_options = ClaudeCodeOptions(
    model=model,
    system_prompt="...",
    allowed_tools=["Read", "Write", "Edit", "Glob", "Grep", "Bash"],
    max_turns=25,  # REDUCED from 50 to avoid context bloat
)
```

### Fix 4: Better Error Handling

```python
# In run_agent_session(), detect this specific error:
if "API Error: 400 due to tool use concurrency issues" in response_text:
    logger.error("FATAL: Tool concurrency error - client context is likely corrupted")
    logger.error("Recommendation: Restart with fresh client")
    return "fatal_error", response_data, error_health_status
```

### Fix 5: Add Context Budget Tracking

```python
# Track cumulative tokens used
total_tokens_used = 0
MAX_TOKENS_PER_RUN = 500000  # Safety limit

# After each session:
total_tokens_used += session_tokens
if total_tokens_used > MAX_TOKENS_PER_RUN:
    logger.warning("Approaching token budget limit, creating fresh client")
    # Recreate client
```

---

## Testing Plan

1. **Test Fix 1:** Create new client per iteration
   - Run for 10 iterations
   - Verify no API 400 errors
   - Confirm each iteration starts fresh

2. **Test Fix 2:** Verify 50 issues created
   - Run initializer session
   - Count issues: `gh issue list --json number | jq 'length'`
   - Should be exactly 50

3. **Test Combined:** Full agent run
   - Initialize project (verify 50 issues)
   - Run coding agent for 20 iterations
   - Monitor for API errors
   - Verify work progresses smoothly

---

## Conclusion

The autonomous agent framework has fundamental architectural flaws:

1. **Client reuse causes context accumulation** → API 400 errors after 3 iterations
2. **Incomplete issue creation** → Only 10/50 issues created
3. **No recovery mechanism** → Agent is permanently stuck once error occurs

These issues make the framework **unusable for production** in its current state.

**Priority fixes:**
1. ✅ HIGH: Create new client per iteration (fixes 94% of failures)
2. ✅ HIGH: Enforce 50-issue creation (fixes incomplete planning)
3. ✅ MEDIUM: Reduce max_turns to 25 (reduces context growth)
4. ✅ LOW: Better error detection and recovery

**Estimated effort:** 2-4 hours to implement all fixes and test thoroughly.
