# Autonomous Coding Agent Framework

A production-ready autonomous coding agent framework using Claude Code SDK and GitHub Issues/Projects v2 for project management.

## Key Features

- **GitHub Integration**: Work tracked as GitHub Issues with Projects v2 Kanban boards
- **Parallel Execution**: Run multiple agent sessions concurrently for faster development
- **Agent Reliability**: TTL-based claim expiration, graceful termination, outcome validation
- **API Error Handling**: Automatic token rotation and retry strategies for rate limits
- **Constitution System**: Project governance rules for deployment, secrets, and coding standards
- **Session Health Monitoring**: Productivity scoring, stall detection, error tracking
- **Intelligent Caching**: Reduces GitHub API calls by 60-80%
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

**Sequential mode (single agent):**
```bash
# Basic usage - runs indefinitely
python autonomous_agent_fixed.py --project-dir ./generations/my_project

# Run for specific iterations
python autonomous_agent_fixed.py --project-dir ./generations/my_project --max-iterations 5

# Use specific project spec
python autonomous_agent_fixed.py --project-dir ./generations/my_project --project-name my_spec
```

**Parallel mode (recommended for faster development):**
```bash
# Run 3 concurrent sessions (default)
python parallel_agent.py --project-dir ./generations/my_project

# Run 2 concurrent sessions for 5 iteration rounds
python parallel_agent.py --project-dir ./generations/my_project --concurrent 2 --iterations 5
```

### 3. Monitor Progress

```bash
# Real-time dashboard
python monitor.py ./generations/my_project --watch

# View session logs
python view_logs.py ./generations/my_project/logs/session_*.jsonl
```

## How It Works

### Workflow

```
Session 1 (Initializer):
  ├── Read app_spec.txt
  ├── Create GitHub Project (v2 Kanban board)
  ├── Create labeled GitHub issues (25-50)
  ├── Set up project structure
  └── Mark initialization complete

Session 2+ (Coding Agents):
  ├── Claim issue with TTL lock
  ├── Move issue to In Progress
  ├── Implement the feature
  ├── Verify implementation
  ├── Close issue and move to Done
  ├── Update META issue with progress
  └── Commit and push changes
```

### Agent Reliability Features

- **TTL-Based Claims**: Issues are locked for 30 minutes; stale claims auto-expire
- **Graceful Termination**: Stops after 3 rounds with no available issues
- **Failure Tracking**: Issues deprioritized after 3 failures
- **Outcome Validation**: Sessions must close issues, update META, and push to git
- **Productivity Scoring**: Formula: `(files_changed * 2 + issues_closed * 5) / tool_count`

### API Error Handling

Automatic classification and recovery:
- **Rate Limits (429)**: Wait and retry with exponential backoff
- **Authentication (401/403)**: Rotate to next available token
- **Conflicts (409)**: Pull and retry with rebase
- **Overloaded (529)**: Extended wait before retry

## Project Structure

```
github-coding-agent-framework/
├── autonomous_agent_fixed.py   # Sequential agent (single session)
├── parallel_agent.py           # Parallel agent (multiple sessions)
├── api_error_handler.py        # Error classification and recovery
├── github_cache.py             # API caching with TTL
├── github_projects.py          # Projects v2 Kanban integration
├── github_enhanced.py          # Enhanced GitHub operations
├── github_config.py            # Configuration constants
├── git_utils.py                # Git operations with large file handling
├── issue_claim_manager.py      # Cross-session issue locking
├── session_state.py            # Session checkpointing
├── token_rotator.py            # Multi-token rotation
├── constitution.py             # Project governance rules
├── logging_system.py           # Structured JSON logging
├── prompts.py                  # Prompt loading utilities
├── monitor.py                  # Progress dashboard
├── manage_specs.py             # Project spec management
├── view_logs.py                # Log viewer
├── prompts/
│   ├── initializer_prompt.md   # Session 1 prompt
│   ├── coding_prompt.md        # Session 2+ prompt
│   └── {project_name}/         # Project-specific specs
│       └── app_spec.txt
├── tests/                      # Test suite
└── docs/                       # Documentation
```

## Command Line Options

### autonomous_agent_fixed.py

| Option | Description | Default |
|--------|-------------|---------|
| `--project-dir` | Directory for the project | Required |
| `--max-iterations` | Max agent iterations | Unlimited |
| `--model` | Claude model to use | claude-opus-4-5-20251101 |
| `--project-name` | Spec from prompts/{name}/ | Auto-detect |

### parallel_agent.py

| Option | Description | Default |
|--------|-------------|---------|
| `--project-dir` | Directory for the project | Required |
| `--concurrent` | Number of parallel sessions | 3 |
| `--iterations` | Max iteration rounds | Unlimited |
| `--model` | Claude model to use | claude-opus-4-5-20251101 |

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `CLAUDE_CODE_OAUTH_TOKEN` | Primary Claude Code token | Yes |
| `CLAUDE_CODE_OAUTH_TOKEN_2` | Backup token for rotation | No |
| `CLAUDE_CODE_OAUTH_TOKEN_3` | Additional backup token | No |

GitHub authentication is handled by `gh auth login`.

## Constitution System

Create project governance rules with the `/create-constitution` slash command:

```bash
/create-constitution myproject --template plesk
```

Constitutions define:
- Deployment target (Plesk, Vercel, AWS)
- Secret naming conventions
- TDD requirements
- Browser verification settings
- Agent constraints

## Slash Commands

Available in `.claude/commands/`:
- `/idea-to-spec` - Transform an idea into `app_spec.txt`
- `/generate-spec` - Generate spec from requirements
- `/research-tech-stack` - Research optimal technology choices
- `/regenerate-issues` - Regenerate issues when backlog is empty
- `/create-constitution` - Create project governance rules
- `/tdd-workflow` - Test-Driven Development workflow

## Documentation

Detailed documentation is available in the `docs/` folder:

- [IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md) - Original implementation guide
- [OPTIMIZATION_GUIDE.md](docs/OPTIMIZATION_GUIDE.md) - Performance optimizations
- [PROJECT_SPECS_README.md](docs/PROJECT_SPECS_README.md) - Managing project specifications
- [LOGGING.md](docs/LOGGING.md) - Logging system documentation
- [IMPROVEMENT_PLAN.md](docs/IMPROVEMENT_PLAN.md) - Agent reliability improvements

## Troubleshooting

**"Control request timeout: initialize"**
- Use single-line system_prompt in ClaudeCodeOptions
- See [SOLUTION_MULTILINE_PROMPT_FIX.md](docs/SOLUTION_MULTILINE_PROMPT_FIX.md)

**Rate limit errors (429)**
- Add backup tokens to `.env` for automatic rotation
- Reduce `--concurrent` sessions

**Agent appears to hang on first run**
- Normal - initializer is creating GitHub project and issues
- Monitor with `python monitor.py ./project --watch`

**Stale claims blocking issues**
- Claims auto-expire after 30 minutes
- Force cleanup: delete `.issue_claims.json` in project directory

## License

MIT License - see [LICENSE](LICENSE) for details.

---

**Last Updated:** 2025-12-17
