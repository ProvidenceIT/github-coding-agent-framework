# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **Autonomous GitHub Coding Agent Framework** built on the Claude Code SDK. It enables AI agents to autonomously work on software development projects using GitHub Issues as the source of truth for task management.

The framework operates in two modes:
- **Initializer mode**: First-run setup that creates GitHub Issues from an `app_spec.txt` specification (25-50 issues), sets up labels, creates a META tracking issue, and initializes project structure
- **Coding agent mode**: Subsequent sessions that pick issues, implement them, close them, and push changes

## Commands

### Running the Agent
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
