# Autonomous Coding Agent Demo (GitHub-Integrated)

A minimal harness demonstrating long-running autonomous coding with the Claude Agent SDK. This demo implements a two-agent pattern (initializer + coding agent) with **GitHub Issues and GitHub Projects v2 as the core project management system** for tracking all work.

## Key Features

- **GitHub Integration**: All work is tracked as GitHub Issues with Projects v2, not local files
- **Real-time Visibility**: Watch agent progress directly in your GitHub repository
- **Session Handoff**: Agents communicate via GitHub issue comments, not text files
- **Two-Agent Pattern**: Initializer creates GitHub project & issues, coding agents implement them
- **Browser Testing**: Puppeteer MCP for UI verification
- **Claude Opus 4.5**: Uses Claude's most capable model by default
- **Intelligent Caching**: Reduces API calls by 60-80%
- **Auto-Commit & Push**: Automatic git operations after each session
- **Structured Logging**: Production-grade JSON logging

## Prerequisites

### 1. Install Claude Code CLI and Python SDK

```bash
# Install Claude Code CLI (latest version required)
npm install -g @anthropic-ai/claude-code

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Set Up Authentication

You need two authentications:

#### Claude Code OAuth Token

```bash
# Generate by running:
claude setup-token

# Then add to .env file:
CLAUDE_CODE_OAUTH_TOKEN=your-oauth-token-here
```

#### GitHub CLI Authentication

```bash
# Install GitHub CLI if not already installed
# On Windows: winget install GitHub.cli
# On macOS: brew install gh
# On Linux: see https://github.com/cli/cli/blob/trunk/docs/install_linux.md

# Login to GitHub
gh auth login

# Verify authentication
gh auth status
```

**Note:** Unlike the Linear version, no API key is needed - GitHub CLI handles OAuth automatically.

### 3. Verify Installation

```bash
claude --version     # Should be latest version
pip show claude-code-sdk  # Check SDK is installed
gh auth status       # Should show logged in
```

## Quick Start

### Optimized Version (Recommended)
```bash
# With all optimizations enabled (auto-commit and push)
python autonomous_agent_optimized.py --project-dir ./my_project

# With YOLO mode (unrestricted commands)
python autonomous_agent_optimized.py --project-dir ./my_project --yolo

# Disable auto-push (commit only)
python autonomous_agent_optimized.py --project-dir ./my_project --no-push

# Monitor progress in another terminal
python monitor.py ./my_project --watch
```

For testing with limited iterations:
```bash
python autonomous_agent_optimized.py --project-dir ./my_project --max-iterations 3
```

## How It Works

### GitHub-Centric Workflow

```
+-------------------------------------------------------------+
|                  GITHUB-INTEGRATED WORKFLOW                   |
+-------------------------------------------------------------+
|  app_spec.txt --> Initializer Agent --> GitHub Issues (50)  |
|                                              |               |
|                    +-------------------------v----------+    |
|                    |       GITHUB REPOSITORY            |    |
|                    |  +----------------------------+    |    |
|                    |  | Issue: Auth - Login flow   |    |    |
|                    |  | Status: Todo -> In Progress|    |    |
|                    |  | Comments: [session notes]  |    |    |
|                    |  +----------------------------+    |    |
|                    +------------------------------------+    |
|                                              |               |
|                    Coding Agent queries GitHub              |
|                    |-- gh issue list (Todo issues)          |
|                    |-- gh project item-edit (In Progress)   |
|                    |-- Implement & test with Puppeteer      |
|                    |-- gh issue comment (implementation)    |
|                    |-- gh issue close (Done)                |
+-------------------------------------------------------------+
```

### Two-Agent Pattern

1. **Initializer Agent (Session 1):**
   - Reads `app_spec.txt`
   - Creates a new GitHub Project (v2 board)
   - Creates 50 GitHub issues with detailed test steps
   - Creates a META issue for session tracking
   - Sets up project structure, `init.sh`, and git

2. **Coding Agent (Sessions 2+):**
   - Queries GitHub for highest-priority open issue
   - Runs verification tests on previously completed features
   - Claims issue (moves to In Progress column)
   - Implements the feature
   - Tests via Puppeteer browser automation
   - Adds implementation comment to issue
   - Closes issue (marks as Done)
   - Updates META issue with session summary

### Session Handoff via GitHub

Instead of local text files, agents communicate through:
- **Issue Comments**: Implementation details, blockers, context
- **META Issue**: Session summaries and handoff notes
- **Project Status**: Todo / In Progress / Done columns

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `CLAUDE_CODE_OAUTH_TOKEN` | Claude Code OAuth token (from `claude setup-token`) | Yes |

**Note:** GitHub authentication is handled by `gh auth login`, not environment variables.

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--project-dir` | Directory for the project | `./autonomous_demo_project` |
| `--max-iterations` | Max agent iterations | Unlimited |
| `--model` | Claude model to use | `claude-opus-4-5-20251101` |
| `--yolo` | Enable YOLO security mode | Off |
| `--ultra-yolo` | Enable ultra YOLO mode (no sandbox) | Off |
| `--no-push` | Disable automatic git push | Off |
| `--log-level` | Logging level (DEBUG/INFO/WARNING/ERROR) | INFO |

## Project Structure

```
github-coding-agent-framework/
├── autonomous_agent_optimized.py  # Main entry point
├── agent.py                       # Agent session logic
├── client.py                      # Claude SDK client configuration
├── security.py                    # Bash command allowlist and validation
├── security_yolo.py               # YOLO mode configuration
├── progress.py                    # Progress tracking utilities
├── prompts.py                     # Prompt loading utilities
├── github_config.py               # GitHub configuration constants
├── github_cache.py                # GitHub API response caching
├── github_enhanced.py             # Enhanced GitHub integration
├── logging_system.py              # Structured logging
├── monitor.py                     # Progress monitoring dashboard
├── git_utils.py                   # Git operations
├── prompts/
│   ├── app_spec.txt               # Application specification
│   ├── initializer_prompt.md      # First session prompt (creates GitHub issues)
│   └── coding_prompt.md           # Continuation session prompt (works issues)
└── requirements.txt               # Python dependencies
```

## Generated Project Structure

After running, your project directory will contain:

```
my_project/
├── .github_project.json    # GitHub project state (marker file)
├── .github_cache.json      # API response cache
├── app_spec.txt            # Copied specification
├── init.sh                 # Environment setup script
├── .claude_settings.json   # Security settings
├── logs/                   # Structured logs
│   ├── session_*.jsonl     # Per-session logs
│   ├── agent_daily.log     # Daily aggregated logs
│   └── errors.log          # Error logs
└── [application files]     # Generated application code
```

## GitHub Setup

Before running, ensure you have:

1. A GitHub account with permission to create repositories
2. GitHub CLI installed and authenticated (`gh auth login`)
3. The agent will automatically create issues in the current repo

The initializer agent will create:
- A new GitHub Project (v2 board) named after your app
- 50 feature issues with priority labels
- 1 META issue for session tracking and handoff

All subsequent coding agents will work from this GitHub project.

## Security Model

This demo uses defense-in-depth security (see `security.py` and `client.py`):

1. **OS-level Sandbox:** Bash commands run in an isolated environment
2. **Filesystem Restrictions:** File operations restricted to project directory
3. **Bash Allowlist:** Only specific commands permitted (npm, node, git, gh, etc.)
4. **MCP Permissions:** Tools explicitly allowed in security settings

## Customization

### Changing the Application

Edit `prompts/app_spec.txt` to specify a different application to build.

### Adjusting Issue Count

Edit `prompts/initializer_prompt.md` and change "50 issues" to your desired count.

### Modifying Allowed Commands

Edit `security.py` to add or remove commands from `ALLOWED_COMMANDS`.

## Troubleshooting

**"CLAUDE_CODE_OAUTH_TOKEN not set"**
Run `claude setup-token` to generate a token, then add it to `.env`.

**"GitHub CLI is not authenticated"**
Run `gh auth login` to authenticate with GitHub.

**"Appears to hang on first run"**
Normal behavior. The initializer is creating a GitHub project and 50 issues with detailed descriptions. Watch for `[Tool: Bash]` output showing `gh issue create` commands.

**"Command blocked by security hook"**
The agent tried to run a disallowed command. Add it to `ALLOWED_COMMANDS` in `security.py` if needed.

## Viewing Progress

Open your GitHub repository to see:
- The project board created by the initializer agent
- All 50 issues with priority labels
- Real-time status changes (Todo -> In Progress -> Done columns)
- Implementation comments on each issue
- Session summaries on the META issue

## GitHub CLI Commands Reference

The agent uses these `gh` commands:

```bash
# Project management
gh project create --title "Project Name" --owner @me
gh project field-list [number] --owner @me --format json
gh project item-add [number] --owner @me --url [issue-url]
gh project item-edit --project-id [id] --id [item-id] --field-id [field] --single-select-option-id [option]

# Issue management
gh issue create --title "Title" --body "Body" --label "priority:high"
gh issue list --state open --json number,title,labels
gh issue view [number] --json body,comments
gh issue comment [number] --body "Comment text"
gh issue close [number]
gh issue reopen [number]
```

---

## License

MIT License - see [LICENSE](LICENSE) for details.
