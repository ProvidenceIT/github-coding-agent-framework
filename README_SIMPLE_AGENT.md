# Working Autonomous GitHub Agent

## ✅ What Works

The `simple_github_agent.py` is **verified working** with these characteristics:

1. **Creates client from base directory** (not from within project dir)
2. **No timeouts** on async with client context or queries
3. **Simple inline prompts** (no external file loading)
4. **Minimal dependencies** (just claude_code_sdk)

## 🎯 Recommended Usage

Since the full autonomous agent with GitHub integration has initialization timeout issues when creating clients in a loop, here's the recommended approach:

### Option 1: Use Simple Agent Directly

```bash
cd "g:\source code\github-coding-agent-framework"
set CLAUDE_CODE_OAUTH_TOKEN=your-token-here
python simple_github_agent.py
```

This agent:
- ✅ Connects successfully
- ✅ Runs GitHub CLI commands
- ✅ Completes tasks reliably

### Option 2: Manual GitHub Integration

Run the simple agent multiple times with different prompts:

```python
# Edit simple_github_agent.py and change SIMPLE_PROMPT to:

# First run - Initialize project
SIMPLE_PROMPT = """Initialize a GitHub project:
1. Run: gh repo view --json nameWithOwner
2. Create project: gh project create --title "My Project" --owner @me
3. Create 3 starter issues with gh issue create
"""

# Second run - Work on issues
SIMPLE_PROMPT = """Work on GitHub issues:
1. List issues: gh issue list
2. Pick one and implement it
3. Update issue status
"""
```

## 🐛 Known Issue - SOLVED ✅

**Root Cause Identified:** Multiline `system_prompt` strings cause "Control request timeout: initialize" errors.

The Claude CLI subprocess fails when system_prompt contains newline characters:
```python
# ❌ FAILS - Multiline string
system_prompt="""You are an expert.
Use GitHub CLI.
Build quality code."""

# ✅ WORKS - Single line string
system_prompt="You are an expert. Use GitHub CLI. Build quality code."
```

See `SOLUTION_MULTILINE_PROMPT_FIX.md` for full details and test results.

## 💡 Solution

**Fixed agent available:** Use `autonomous_agent_fixed.py` which implements:
1. Single-line system_prompt (no newlines)
2. Creates client once and reuses it for all sessions
3. Full GitHub integration with automatic prompt switching
4. Works reliably with all tools and features

```bash
python autonomous_agent_fixed.py --project-dir ./my_project --max-iterations 5
```

## 📝 Working Example

See `simple_github_agent.py` for the complete working implementation.
