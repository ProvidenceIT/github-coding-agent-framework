"""
YOLO Security Mode - Minimal Restrictions
==========================================

WARNING: This disables security restrictions for maximum agent autonomy.
Only use in controlled/sandboxed environments!

This mode:
- Allows all bash commands (no allowlist)
- Skips pre-tool-use validation hooks
- Uses dangerouslyDisableSandbox when needed
- Enables maximum agent freedom

Use Cases:
- Rapid prototyping
- Trusted environments
- When security hooks are blocking necessary operations
"""

from pathlib import Path
import json
import subprocess
from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient
import os

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# All MCP tools (no restrictions)
PUPPETEER_TOOLS = [
    "mcp__puppeteer__puppeteer_navigate",
    "mcp__puppeteer__puppeteer_screenshot",
    "mcp__puppeteer__puppeteer_click",
    "mcp__puppeteer__puppeteer_fill",
    "mcp__puppeteer__puppeteer_select",
    "mcp__puppeteer__puppeteer_hover",
    "mcp__puppeteer__puppeteer_evaluate",
]

BUILTIN_TOOLS = [
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "Bash",
]


def check_gh_auth() -> bool:
    """
    Check if GitHub CLI is authenticated.

    Returns:
        True if authenticated, False otherwise
    """
    import sys
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10,
            shell=(sys.platform == 'win32')  # Use shell on Windows for PATH resolution
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def verify_claude_cli() -> bool:
    """Verify Claude CLI is installed and working."""
    import sys
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            shell=(sys.platform == 'win32')  # Use shell on Windows for PATH resolution
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def create_yolo_client(project_dir: Path, model: str) -> ClaudeSDKClient:
    """
    Create a Claude Agent SDK client with MINIMAL security restrictions.

    WARNING: This bypasses security hooks and allows all commands!
    Only use in trusted/sandboxed environments.

    Args:
        project_dir: Directory for the project
        model: Claude model to use

    Returns:
        Configured ClaudeSDKClient with YOLO mode
    """
    api_key = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if not api_key:
        raise ValueError(
            "CLAUDE_CODE_OAUTH_TOKEN environment variable not set.\n"
            "Run 'claude setup-token' after installing the Claude Code CLI."
        )

    # Verify Claude CLI is installed
    if not verify_claude_cli():
        raise ValueError(
            "Claude CLI is not installed or not working.\n"
            "Install with: npm install -g @anthropics/claude-code"
        )

    # Check GitHub CLI authentication
    if not check_gh_auth():
        raise ValueError(
            "GitHub CLI is not authenticated.\n"
            "Run 'gh auth login' to authenticate with GitHub."
        )

    # YOLO security settings - minimal restrictions
    # Note: Sandbox can still be enabled for filesystem isolation
    # but we remove the allowlist restrictions
    security_settings = {
        "sandbox": {
            "enabled": True,  # Still isolate bash, but no command restrictions
            "autoAllowBashIfSandboxed": True
        },
        "permissions": {
            "defaultMode": "accept",  # Auto-approve everything
            "allow": [
                # Allow ALL file operations (using wildcards)
                "Read(**)",
                "Write(**)",
                "Edit(**)",
                "Glob(**)",
                "Grep(**)",
                "Bash(*)",  # No restrictions on bash commands
                # Allow all MCP tools
                *PUPPETEER_TOOLS,
            ],
        },
    }

    # Ensure project directory exists
    project_dir.mkdir(parents=True, exist_ok=True)

    # Write settings to file
    settings_file = project_dir / ".claude_settings_yolo.json"
    with open(settings_file, "w") as f:
        json.dump(security_settings, f, indent=2)

    print("YOLO MODE ENABLED - Security restrictions minimized!")
    print(f"   - Settings: {settings_file}")
    print(f"   - Sandbox: Enabled (filesystem isolation only)")
    print(f"   - Bash: All commands allowed")
    print(f"   - File ops: Unrestricted")
    print("   - GitHub CLI (gh) authenticated for project management")
    print("   WARNING: Use only in trusted environments!")
    print()

    return ClaudeSDKClient(
        options=ClaudeCodeOptions(
            model=model,
            system_prompt="""You are an expert full-stack developer with maximum autonomy.
You have unrestricted access to all development tools and commands.
Use GitHub Issues and GitHub Projects for project management and tracking.
Use 'gh' CLI commands to interact with GitHub. Build production-quality applications.""",
            allowed_tools=[
                *BUILTIN_TOOLS,
                *PUPPETEER_TOOLS,
            ],
            mcp_servers={
                "puppeteer": {"command": "npx", "args": ["puppeteer-mcp-server"]},
            },
            # NO security hooks - all commands allowed
            hooks={},
            max_turns=1000,
            cwd=str(project_dir.resolve()),
            settings=str(settings_file.resolve()),
        )
    )


def create_ultra_yolo_client(project_dir: Path, model: str) -> ClaudeSDKClient:
    """
    Create a Claude Agent SDK client with ZERO restrictions.

    EXTREME WARNING: This disables even sandbox isolation!
    Only use when sandbox is blocking necessary operations.

    Args:
        project_dir: Directory for the project
        model: Claude model to use

    Returns:
        Configured ClaudeSDKClient with ultra-YOLO mode
    """
    api_key = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if not api_key:
        raise ValueError("CLAUDE_CODE_OAUTH_TOKEN environment variable not set.")

    # Check GitHub CLI authentication
    if not check_gh_auth():
        raise ValueError(
            "GitHub CLI is not authenticated.\n"
            "Run 'gh auth login' to authenticate with GitHub."
        )

    # ULTRA YOLO - No sandbox, no restrictions
    security_settings = {
        "sandbox": {
            "enabled": False,  # DISABLED - No sandbox isolation
        },
        "permissions": {
            "defaultMode": "accept",
            "allow": [
                "Read(**)",
                "Write(**)",
                "Edit(**)",
                "Glob(**)",
                "Grep(**)",
                "Bash(*)",
                *PUPPETEER_TOOLS,
            ],
        },
    }

    project_dir.mkdir(parents=True, exist_ok=True)
    settings_file = project_dir / ".claude_settings_ultra_yolo.json"

    with open(settings_file, "w") as f:
        json.dump(security_settings, f, indent=2)

    print("ULTRA YOLO MODE - ALL RESTRICTIONS DISABLED!")
    print(f"   - Settings: {settings_file}")
    print(f"   - Sandbox: DISABLED")
    print(f"   - Bash: Unrestricted system access")
    print(f"   - File ops: Full filesystem access")
    print("   - GitHub CLI (gh) authenticated for project management")
    print("   DANGER: Agent has full system access!")
    print()

    return ClaudeSDKClient(
        options=ClaudeCodeOptions(
            model=model,
            system_prompt="""You are an expert full-stack developer with complete system access.
You have unrestricted access to all commands and system operations.
Use GitHub Issues and GitHub Projects for project management.
Use 'gh' CLI commands to interact with GitHub. Build production-quality applications with maximum freedom.""",
            allowed_tools=[
                *BUILTIN_TOOLS,
                *PUPPETEER_TOOLS,
            ],
            mcp_servers={
                "puppeteer": {"command": "npx", "args": ["puppeteer-mcp-server"]},
            },
            hooks={},
            max_turns=1000,
            cwd=str(project_dir.resolve()),
            settings=str(settings_file.resolve()),
        )
    )
