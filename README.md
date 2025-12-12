# Autonomous Coding Agent Framework (GitHub-Integrated)

A production-ready autonomous coding agent framework using Claude Code SDK and GitHub Issues/Projects v2 for project management.

## ✅ Status: Working

The agent is fully functional after fixing the multiline system_prompt timeout issue. See [SOLUTION_MULTILINE_PROMPT_FIX.md](SOLUTION_MULTILINE_PROMPT_FIX.md) for details.

## Key Features

- **GitHub Integration**: Work tracked as GitHub Issues with Projects v2
- **Real-time Visibility**: Watch agent progress in your GitHub repository
- **Two-Agent Pattern**: Initializer creates GitHub project & issues, coding agents implement them
- **Autonomous Loop**: Agent automatically switches between initializer and coding modes
- **Auto-Commit & Push**: Automatic git operations after each session
- **Intelligent Caching**: Reduces API calls by 60-80%
- **Production Logging**: Structured JSON logging with rotation

## Quick Start

### 1. Prerequisites

```bash
# Install Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Install Python dependencies
pip install -r requirements.txt

# Authenticate with GitHub
gh auth login

# Set up Claude Code token
claude setup-token
# Copy token to .env file:
# CLAUDE_CODE_OAUTH_TOKEN=your-oauth-token-here
```

### 2. Run the Agent

```bash
# Basic usage
python autonomous_agent_fixed.py --project-dir ./my_project

# Limited iterations for testing
python autonomous_agent_fixed.py --project-dir ./my_project --max-iterations 5

# Use a different model
python autonomous_agent_fixed.py --project-dir ./my_project --model claude-opus-4-5-20251101

# Use a specific project spec from your library
python autonomous_agent_fixed.py --project-dir ./my_project --project-name my-saas-app
```

## Managing Project Specifications

The framework now supports organized project specifications stored in `prompts/{project_name}/` directories. This allows you to maintain a library of reusable project specs.

See [PROJECT_SPECS_README.md](PROJECT_SPECS_README.md) for full documentation.

### Quick Reference

```bash
# List all available project specs
python manage_specs.py list

# Create a new project spec
python manage_specs.py create my-new-project

# View a project spec
python manage_specs.py view test_fresh

# Edit a project spec
python manage_specs.py edit my-new-project
```

### Running with a Specific Spec

```bash
# Use the test_fresh spec
python autonomous_agent_fixed.py \
  --project-dir ./generations/my-project \
  --project-name test_fresh

# The agent will:
# 1. Copy prompts/test_fresh/app_spec.txt to project directory
# 2. Create GitHub repo: ProvidenceIT/clevertech-providenceit-automation
# 3. Create 50 issues from the spec
# 4. Start building
```

The spec lookup order is:
1. `prompts/{--project-name}/app_spec.txt` (if specified)
2. `prompts/{directory-name}/app_spec.txt` (auto-detect)
3. `prompts/app_spec.txt` (legacy fallback)

## Agent Features

**`autonomous_agent_fixed.py`** - Production-ready autonomous coding agent

**Status:** ✅ Working perfectly

**Features:**
- Creates client once and reuses it (efficient)
- Single-line system_prompt (no timeout issues)
- Full GitHub integration (Issues + Projects v2)
- Automatic prompt switching (initializer → coding)
- GitHub API caching (reduces calls by 60-80%)
- Auto-commit and push after each session
- Clean, maintainable codebase

## How It Works

### Workflow

```
Session 1 (Initializer):
  ├── Read app_spec.txt
  ├── Create GitHub Project (v2 board)
  ├── Create labeled GitHub issues
  ├── Set up project structure
  └── Mark initialization complete

Session 2+ (Coding Agent):
  ├── Query GitHub for open issues
  ├── Pick highest priority Todo issue
  ├── Move issue to In Progress
  ├── Implement the feature
  ├── Test implementation
  ├── Update issue with comment
  ├── Close issue (mark Done)
  └── Repeat for next issue
```

### Session Handoff via GitHub

Agents communicate through:
- **Issue Comments**: Implementation details, blockers, context
- **Project Status**: Todo / In Progress / Done columns
- **Git Commits**: Code changes with session metadata

## Project Structure

```
github-coding-agent-framework/
├── autonomous_agent_fixed.py      # ✅ Main agent
├── github_cache.py                # GitHub API response caching
├── github_enhanced.py             # Enhanced GitHub integration
├── github_config.py               # GitHub configuration
├── git_utils.py                   # Git operations
├── prompts.py                     # Prompt loading utilities
├── logging_system.py              # Structured logging
├── monitor.py                     # Progress monitoring
├── progress.py                    # Progress tracking
├── security.py                    # Security configuration
├── prompts/
│   ├── app_spec.txt               # Application specification
│   ├── initializer_prompt.md      # Session 1 prompt
│   └── coding_prompt.md           # Session 2+ prompt
└── requirements.txt               # Python dependencies
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--project-dir` | Directory for the project | Required |
| `--max-iterations` | Max agent iterations | Unlimited |
| `--model` | Claude model to use | `claude-sonnet-4-5-20250929` |

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `CLAUDE_CODE_OAUTH_TOKEN` | From `claude setup-token` | Yes |

GitHub authentication is handled by `gh auth login`.

## Customization

### Change the Application

Edit `prompts/app_spec.txt` to specify what to build.

### Adjust Issue Count

Edit `prompts/initializer_prompt.md` and change the number of issues to create.

### Modify Security

Edit `security.py` to add/remove allowed commands in `ALLOWED_COMMANDS`.

## Troubleshooting

**"Control request timeout: initialize"**
- **Cause:** Multiline system_prompt in ClaudeCodeOptions
- **Fix:** Use single-line system_prompt (already fixed in both agents)
- **Details:** See [SOLUTION_MULTILINE_PROMPT_FIX.md](SOLUTION_MULTILINE_PROMPT_FIX.md)

**"CLAUDE_CODE_OAUTH_TOKEN not set"**
- Run `claude setup-token` to generate a token
- Add it to `.env` file

**"GitHub CLI not authenticated"**
- Run `gh auth login` to authenticate

**Agent appears to hang on first run**
- Normal behavior - initializer is creating GitHub project and issues
- Watch for `[Tool: Bash]` output showing `gh issue create` commands

**Command blocked by security**
- Agent tried to run a disallowed command
- Add it to `ALLOWED_COMMANDS` in `security.py` if safe

## Monitoring Progress

### In GitHub
- Open your repository to see the project board
- Watch issues move through Todo → In Progress → Done
- Read implementation comments on each issue

### With Monitor Tool
```bash
python monitor.py ./my_project --watch
```

## Documentation

- [SOLUTION_MULTILINE_PROMPT_FIX.md](SOLUTION_MULTILINE_PROMPT_FIX.md) - How we fixed the timeout issue
- [README_SIMPLE_AGENT.md](README_SIMPLE_AGENT.md) - Debugging history and solution
- [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) - Original implementation guide
- [OPTIMIZATION_GUIDE.md](OPTIMIZATION_GUIDE.md) - Performance optimizations

## GitHub CLI Commands Used

```bash
# Project management
gh project create --title "Project Name" --owner @me
gh project item-add [number] --owner @me --url [issue-url]
gh project item-edit --project-id [id] --id [item-id] --field-id [field]

# Issue management
gh issue create --title "Title" --body "Body" --label "priority:high"
gh issue list --state open --json number,title,labels
gh issue comment [number] --body "Comment text"
gh issue close [number]
```

## License

MIT License - see [LICENSE](LICENSE) for details.

---

**Last Updated:** 2025-12-11
**Status:** ✅ Agent working perfectly
**Files:** Cleaned up - only working agent and core modules remain
