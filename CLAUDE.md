# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **Autonomous GitHub Coding Agent Framework** built on the Claude Code SDK. It enables AI agents to autonomously work on software development projects using GitHub Issues as the source of truth for task management.

The framework operates in two modes:
- **Initializer mode**: First-run setup that creates GitHub Issues from an `app_spec.txt` specification (25-50 issues), sets up labels, creates a META tracking issue, and initializes project structure
- **Coding agent mode**: Subsequent sessions that pick issues, implement them, close them, and push changes

## Commands

### Running the Agent (Sequential)
```bash
# Basic usage - runs indefinitely
python autonomous_agent_fixed.py --project-dir ./generations/my_project

# Run for specific iterations
python autonomous_agent_fixed.py --project-dir ./generations/my_project --max-iterations 5

# Use specific project spec from prompts/{name}/app_spec.txt
python autonomous_agent_fixed.py --project-dir ./generations/my_project --project-name my_spec

# Use different model (default: claude-opus-4-5-20251101)
python autonomous_agent_fixed.py --project-dir ./generations/my_project --model claude-sonnet-4-20250514
```

### Running Parallel Sessions (Faster)
```bash
# Run 3 concurrent sessions (default)
python parallel_agent.py --project-dir ./generations/my_project

# Run 2 concurrent sessions for 5 iteration rounds
python parallel_agent.py --project-dir ./generations/my_project --concurrent 2 --iterations 5

# Conservative: 2 sessions (safer for rate limits)
python parallel_agent.py --project-dir ./generations/my_project --concurrent 2
```

**Note:** The project must be initialized first with `autonomous_agent_fixed.py`.

### Monitoring
```bash
# One-time dashboard snapshot
python monitor.py ./generations/my_project

# Auto-refresh watch mode
python monitor.py ./generations/my_project --watch

# Custom refresh interval
python monitor.py ./generations/my_project --watch --interval 60
```

### Viewing Logs
```bash
# View session logs (JSON Lines format)
python view_logs.py ./generations/my_project/logs/session_*.jsonl

# Or use jq for filtering
cat logs/session_*.jsonl | jq 'select(.category == "github_api")'
```

### Managing Project Specs
```bash
# List available project specs
python manage_specs.py list

# Create new project spec template
python manage_specs.py create my-new-project
```

## Architecture

### Core Components

```
autonomous_agent_fixed.py   # Main entry point - orchestrates agent sessions
prompts.py                  # Loads prompts from prompts/ directory
prompts/
  initializer_prompt.md     # First-run setup instructions
  coding_prompt.md          # Ongoing coding session instructions
  {project_name}/app_spec.txt  # Project specifications
```

### GitHub Integration Layer

```
github_cache.py             # Smart caching to reduce API calls (5000/hour limit)
github_enhanced.py          # Progress tracking, milestones, health status
github_config.py            # Configuration constants
git_utils.py                # Commit/push with large file handling
```

### Session Management

```
session_state.py            # Checkpoints between sessions
logging_system.py           # Structured JSON logging
monitor.py                  # Real-time progress dashboard
```

### Key Patterns

**Repo Targeting (CRITICAL)**: All `gh` CLI commands use `--repo OWNER/REPO` flag to ensure commands target the correct repository. The repo info is:
- Saved to `.github_project.json` when repo is created/detected
- Injected into prompts via `set_project_context()` in `prompts.py`
- All prompt templates use `--repo REPO` placeholder

**Client Creation**: A fresh `ClaudeSDKClient` is created for each iteration to prevent context accumulation that causes API 400 errors. The client uses:
- Single-line system prompt (multiline causes initialization timeout)
- 50 max turns per session
- Allowed tools: Read, Write, Edit, Glob, Grep, Bash

**Session Flow**:
1. Load prompt based on mode (initializer vs coding)
2. Create fresh client
3. Run session via `client.query()` + `client.receive_response()`
4. Analyze session health (tool usage, response length)
5. Commit and push changes
6. Check mandatory outcomes (issues closed, META updated, git pushed)

**GitHub Caching Strategy**:
- Permanent cache: Issue descriptions (immutable)
- Session cache: Issue statuses (5min TTL)
- API calls tracked for rate limit monitoring

## Slash Commands

Custom slash commands available in `.claude/commands/`:
- `/idea-to-spec` - Interactive workflow to transform an idea into `app_spec.txt`
- `/generate-spec` - Generate comprehensive `app_spec.txt` from requirements
- `/research-tech-stack` - Research optimal technology choices
- `/optimize-agent` - Configure agent for performance
- `/regenerate-issues` - Regenerate or expand GitHub issues when backlog is empty
- `/tdd-workflow` - Test-Driven Development workflow with browser verification
- `/create-constitution` - Create project constitution for governance rules

## Important Implementation Details

**Windows Compatibility**: The agent handles Windows console encoding by wrapping stdout/stderr with UTF-8 TextIOWrapper.

**Git Large File Handling**: The `git_utils.py` module automatically:
- Detects large files (>100MB) before push
- Updates `.gitignore` with critical patterns
- Can clean git history with filter-branch/filter-repo
- Nuclear option: Reset to clean orphan branch if needed

**Health Monitoring**: Each session is analyzed for:
- Tool usage count (from SDK or pattern matching)
- Response length thresholds
- Error indicators in responses
- Stall detection phrases

**Generated Projects**: Output projects go to `generations/{project_name}/` and include:
- `.initialized` marker file
- `.github_project.json` project metadata
- `.github_cache.json` API cache
- `logs/` session logs directory

## Parallel Agent Architecture

The `parallel_agent.py` enables running multiple sessions concurrently:

**Issue Claiming**: Uses file-based atomic locking (`.issue_claims.json` + `.issue_claims.lock`) to prevent multiple sessions from working on the same issue. Cross-platform compatible (Windows uses `msvcrt`, Unix uses `fcntl`).

**Git Serialization**: Push operations are serialized via `AsyncFileLock` to prevent conflicts. Only one session can push at a time.

**Session Isolation**: Each session gets its own `ClaudeSDKClient` instance. No `os.chdir()` is used - all subprocess calls use `cwd=project_dir`.

**Recommended Concurrency Limits**:
- 2 sessions: Conservative, safe for testing
- 3 sessions: Good balance of throughput and stability
- 5+ sessions: Risk of rate limits and conflicts

**Enhanced Features (v2)**:
- Session health monitoring (tool usage, response length, error detection)
- Outcome validation (issues closed, git pushed)
- Automatic retry on unhealthy sessions
- Constitution support for project governance rules

## Agent Reliability Features (v3)

New reliability improvements implemented in Phases 6-11:

### Issue Claim Lifecycle (US1)

**TTL-Based Expiration**: Claims expire after 30 minutes (configurable via `CLAIM_TTL_MINUTES` in `github_config.py`). This prevents orphaned claims from blocking issues indefinitely.

**Stale Claim Cleanup**: Before claiming a new issue, the lock manager automatically cleans up expired claims from other sessions.

**Failure Tracking**: Issues track failure counts. After 3 failures (`FAILURE_DEPRIORITIZE_THRESHOLD`), issues are deprioritized and sorted last in the queue.

```python
# Configuration in github_config.py
CLAIM_TTL_MINUTES = 30  # Claims expire after 30 minutes
FAILURE_DEPRIORITIZE_THRESHOLD = 3  # Issues deprioritized after 3 failures
```

### Graceful Termination (US2)

**Backlog Depletion Detection**: If parallel sessions find no available issues for `MAX_NO_ISSUES_ROUNDS` consecutive rounds (default: 3), the agent terminates gracefully instead of spinning.

```python
MAX_NO_ISSUES_ROUNDS = 3  # Terminate after 3 rounds with no issues
```

### Outcome Validation (US3)

**Issue-Specific Tracking**: Sessions track specific issues worked on (`issues_worked` list) and validate closures against those specific issues, not time-based queries.

**Productivity Metrics**: Sessions calculate a productivity score:
```
score = (files_changed * 2 + issues_closed * 5) / max(tool_count, 1)
```

Low productivity warnings trigger when `tool_count >= 30` and `score < 0.1`.

### API Error Classification (US4, US5)

**Claude API Errors**: Classified with recovery actions:
- 401: `ROTATE_TOKEN` - Try different API key
- 429: `WAIT_AND_RETRY` - Exponential backoff (60s base)
- 500/529: `WAIT_AND_RETRY` - Server errors (30s/120s)
- 400: `MANUAL_REVIEW` - Content filtering

**GitHub API Errors**: Via `execute_gh_command()` wrapper:
- 401: Authentication failed → rotate token
- 403: Forbidden → may be rate limit
- 404: Not found → abort
- 409: Conflict → pull and retry
- 429: Rate limited → wait and retry

### Session Health Monitoring (US6)

**Productivity Scoring**: Each session's productivity is scored based on:
- Tool calls made
- Files changed
- Issues closed

Low-productivity sessions (high tool count, no progress) generate warnings in logs.

### GitHub Projects Integration (US7)

**Kanban Board**: Issues automatically move through project board columns:
- When claimed → "In Progress"
- When closed → "Done"

```python
from github_projects import create_projects_manager

manager = create_projects_manager(project_dir, "owner/repo")
manager.get_or_create_project()
manager.move_to_in_progress(42)
manager.move_to_done(42)
```

### API Error Handler Module

New `api_error_handler.py` provides:

```python
from api_error_handler import classify_error, APISource, get_retry_delay

# Classify an error
error = classify_error(APISource.CLAUDE, 429, "Rate limited")
if error.should_retry():
    delay = get_retry_delay(error, attempt=0)
    time.sleep(delay)
```

### New Files

```
api_error_handler.py    # API error classification and recovery
issue_claim_manager.py  # IssueClaim dataclass
github_projects.py      # GitHub Projects v2 integration
tests/
  test_api_error_handler.py   # Error classification tests
  test_claim_lifecycle.py     # TTL/failure tracking tests
  test_outcome_validation.py  # Outcome validation tests
```

## Project Constitution System

The constitution system (`constitution.py`) provides structured governance rules for projects:

### Creating a Constitution

```python
from constitution import create_constitution_template
from pathlib import Path

# Use the Plesk preset (recommended - includes TDD + browser testing)
constitution = create_constitution_template(
    project_dir=Path("./generations/my_project"),
    name="My Project",
    preset="plesk"  # Full Plesk + TDD + browser verification
)

# Or configure manually
constitution = create_constitution_template(
    project_dir=Path("./generations/my_project"),
    name="My Project",
    deployment_target="plesk",
    organization_prefix="PROVIDENCE_",
    enable_tdd=True,
    browser_testing=True
)
```

Or use the `/create-constitution` slash command:
```
/create-constitution myproject --template plesk
```

### Constitution Features

The `project_constitution.json` file defines:

**Deployment Rules:**
- Target environment (Plesk, Vercel, AWS)
- CI/CD provider
- Required checks before deploy

**Secret Naming:**
- Use organization secrets vs repo-level
- Naming conventions (SCREAMING_SNAKE_CASE)
- Required secrets list
- Organization prefix

**Coding Standards:**
- Commit message format (conventional)
- Test requirements
- Linting requirements

**TDD Configuration:**
- Enable/disable TDD mode
- Minimum coverage percentage
- Browser verification requirements
- MCP Puppeteer integration

**Agent Constraints:**
- Max turns per session
- Mandatory outcomes
- Verification before closing issues

### Constitution Injection

Constitutions are automatically injected into agent prompts via `prompts.py`:
1. `set_project_context()` loads constitution if `project_constitution.json` exists
2. `get_constitution_context()` generates markdown summary
3. Context is prepended to all prompts (initializer and coding)

## Issue Regeneration Workflow

When all issues are completed or the spec changes, use `/regenerate-issues` to:

1. **Expand from Spec** - Create issues for new features in `app_spec.txt`
2. **Phase Transition** - Move from Phase 1 (MVP) to Phase 2 (Enhancement)
3. **Issue Improvement** - Split large issues, improve descriptions
4. **Full Regeneration** - Re-create entire issue set (use sparingly)

## TDD Workflow

Use `/tdd-workflow` for Test-Driven Development:

1. **RED Phase** - Write failing test first
2. **GREEN Phase** - Implement minimal code to pass
3. **REFACTOR Phase** - Clean up while tests stay green

The coding prompt includes TDD verification steps when constitution enables TDD mode:
- Run tests before closing issues
- Check lint passes
- Verify build succeeds
- Browser verification (if required)
