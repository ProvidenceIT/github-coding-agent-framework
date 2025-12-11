# Solution: Claude Code SDK Initialization Timeout Fix

## Problem

The autonomous agent was failing with "Control request timeout: initialize" error when trying to connect to Claude Code CLI subprocess.

```
Exception: Control request timeout: initialize
Error: EPIPE: broken pipe, write
```

## Root Cause

After extensive testing, the root cause was identified:

**Multiline system_prompt strings cause the Claude CLI subprocess to fail during initialization.**

### What Works ✅

```python
client = ClaudeSDKClient(
    options=ClaudeCodeOptions(
        model="claude-sonnet-4-5-20250929",
        system_prompt="You are an expert developer. Use GitHub Issues via gh CLI.",
        allowed_tools=["Read", "Write", "Edit", "Glob", "Grep", "Bash"],
        max_turns=50
    )
)
```

### What Fails ❌

```python
client = ClaudeSDKClient(
    options=ClaudeCodeOptions(
        model="claude-sonnet-4-5-20250929",
        system_prompt="""You are an expert developer.
Use GitHub Issues via gh CLI.
Build quality code.""",  # Multiline string causes timeout!
        allowed_tools=["Read", "Write", "Edit", "Glob", "Grep", "Bash"],
        max_turns=50
    )
)
```

## Test Results

Systematic testing revealed the following:

| Configuration | Result |
|--------------|--------|
| Simple config, no system_prompt | ✅ Works |
| Simple config, single-line system_prompt | ✅ Works |
| All GitHub modules imported | ✅ Works |
| Prompts module imported | ✅ Works |
| All tools enabled | ✅ Works |
| max_turns=50 | ✅ Works |
| **Multiline system_prompt** | **❌ Fails** |

## Solution

Convert all multiline system_prompt strings to single-line strings.

### Before

```python
system_prompt="""You are an expert full-stack developer.
Use GitHub Issues and GitHub Projects for project management via gh CLI.
Build production-quality code with tests."""
```

### After

```python
system_prompt="You are an expert full-stack developer. Use GitHub Issues and GitHub Projects for project management via gh CLI. Build production-quality code with tests."
```

## Files Fixed

1. ✅ `autonomous_agent_fixed.py` - Main working agent
2. ✅ `github_autonomous_agent.py` - Alternative implementation
3. ℹ️  `simple_github_agent.py` - Already working (no multiline prompt)

## Test Verification

```bash
cd "G:\source code\github-coding-agent-framework"
python autonomous_agent_fixed.py --project-dir ./test_final --max-iterations 2
```

Result:
```
✓ Connected!
✅ Agent session complete (Session 1: Initializer)
✅ Agent session complete (Session 2: Coding)
✅ Reached maximum iterations (2)
```

## Recommendation

**Always use single-line strings for system_prompt** when using Claude Code SDK on Windows with Python 3.13+.

## Related Issues

This appears to be a bug in either:
- Claude Code CLI subprocess handling of multiline strings
- JSON serialization of multiline strings in control messages
- Windows-specific newline handling (\r\n vs \n)

Consider reporting to Anthropic if this persists in future SDK versions.

## Working Agent Files

The following agent files are now fully functional:

1. **autonomous_agent_fixed.py** (Recommended)
   - Creates client once, reuses for all sessions
   - Single-line system_prompt
   - Full GitHub integration
   - Automatic prompt switching (initializer → coding)

2. **github_autonomous_agent.py**
   - Creates new client each iteration
   - Single-line system_prompt
   - Full GitHub integration
   - Inline prompts (no external files)

3. **simple_github_agent.py**
   - Minimal configuration
   - Single session
   - Good for testing

---

**Last Updated:** 2025-12-11
**Tested With:** Claude Code SDK v0.0.25, Python 3.13, Windows
