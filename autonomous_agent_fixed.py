"""
Autonomous GitHub Coding Agent - Fixed Version
===============================================

Key fixes:
1. Create client ONCE at start, reuse for all sessions
2. Use single-line system_prompt (multiline prompts cause initialization timeout)

Usage:
    set CLAUDE_CODE_OAUTH_TOKEN=your-token-here
    python autonomous_agent_fixed.py --project-dir ./my_project [--max-iterations 5]
"""

import asyncio
import os
import sys
import subprocess
from pathlib import Path
import argparse
from datetime import datetime
import io

# Fix Windows console encoding
if sys.platform == 'win32' and sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
from github_cache import GitHubCache
from github_enhanced import create_enhanced_integration
from git_utils import create_git_manager
from prompts import get_initializer_prompt, get_coding_prompt, copy_spec_to_project

# Load .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


async def run_agent_session(client: ClaudeSDKClient, prompt: str, project_dir: Path):
    """Run a single agent session with the client."""
    print("Sending prompt to agent...\n")

    # Change to project directory for command execution
    original_dir = Path.cwd()
    os.chdir(project_dir)

    try:
        response = await client.query(prompt)
        print("\n✅ Agent session complete")
        return "success", response
    except Exception as e:
        print(f"\n❌ Error during session: {e}")
        return "error", str(e)
    finally:
        os.chdir(original_dir)


async def main(project_dir: Path, model: str, max_iterations: int = None):
    """Main autonomous agent loop."""

    # Ensure absolute path
    project_dir = project_dir.resolve()
    project_dir.mkdir(parents=True, exist_ok=True)

    # Copy app_spec.txt to project directory
    copy_spec_to_project(project_dir)

    # Initialize GitHub integration
    cache = GitHubCache(project_dir)
    integration = create_enhanced_integration(project_dir, cache)
    git_mgr = create_git_manager(project_dir, auto_push=True)

    # Check if first run
    github_marker = project_dir / ".github_project.json"
    is_first_run = not github_marker.exists()

    # Print banner
    print("\n" + "="*70)
    print("  AUTONOMOUS GITHUB CODING AGENT (FIXED)")
    print("="*70)
    print(f"  Project: {project_dir.name}")
    print(f"  Location: {project_dir}")
    print(f"  Model: {model}")
    print(f"  Mode: {'Initializer (first run)' if is_first_run else 'Coding agent'}")
    print("="*70 + "\n")

    # Show progress if not first run
    if not is_first_run:
        print(integration.generate_progress_report())
        print()

    # KEY FIX: Change to project directory BEFORE creating client
    print(f"Changing to project directory: {project_dir}\n")
    os.chdir(project_dir)

    # Create client ONCE at the start, outside the loop
    print("Creating Claude Code client...")
    client = ClaudeSDKClient(
        options=ClaudeCodeOptions(
            model=model,
            system_prompt="You are an expert full-stack developer. Use GitHub Issues and GitHub Projects for project management via gh CLI. Build production-quality code with tests.",
            allowed_tools=["Read", "Write", "Edit", "Glob", "Grep", "Bash"],
            max_turns=50
        )
    )

    print("Connecting to Claude Code CLI...")
    async with client:
        print("✓ Connected!\n")

        iteration = 0
        while True:
            iteration += 1

            if max_iterations and iteration > max_iterations:
                print(f"\n✅ Reached maximum iterations ({max_iterations})")
                break

            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{iteration:03d}"

            print(f"\n{'='*70}")
            print(f"  SESSION {iteration}: {session_id}")
            print(f"{'='*70}\n")

            try:
                # Choose prompt based on mode
                if is_first_run:
                    prompt = get_initializer_prompt()
                    mode_name = "Initializer"
                else:
                    prompt = get_coding_prompt()
                    mode_name = "Coding"

                print(f"📝 Running {mode_name} agent\n")

                # Run session with the same client (no reconnection needed)
                status, response = await run_agent_session(client, prompt, project_dir)

                # Commit changes
                print("\n📝 Committing changes...")
                commit_success, commit_msg = git_mgr.commit_and_push(
                    issues_completed=[],
                    issues_attempted=[],
                    session_metrics={'status': status},
                    session_id=session_id
                )

                if commit_success:
                    print(f"✅ {commit_msg}")
                else:
                    print(f"⚠️  {commit_msg}")

                # After first run, switch modes
                if is_first_run:
                    is_first_run = False
                    github_marker.write_text(f"Initialized: {datetime.now().isoformat()}")
                    print("\n✅ Initialization complete! Next session will use coding agent.\n")

            except Exception as e:
                print(f"\n❌ Error: {e}")
                print("Continuing to next iteration...\n")

            # Delay before next iteration
            if max_iterations is None or iteration < max_iterations:
                print("\n⏸️  Waiting 3 seconds before next session...\n")
                await asyncio.sleep(3)

    # Final summary (after client closes)
    print("\n" + "="*70)
    print("  AGENT RUN COMPLETE")
    print("="*70)
    print(integration.generate_progress_report())
    print("="*70 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Autonomous GitHub Coding Agent (Fixed)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run agent - initializes project and works on issues
  python autonomous_agent_fixed.py --project-dir ./my_project

  # Run for 5 iterations
  python autonomous_agent_fixed.py --project-dir ./my_project --max-iterations 5

  # Use Opus model (more capable)
  python autonomous_agent_fixed.py --project-dir ./my_project --model claude-opus-4-5-20251101
        """
    )

    parser.add_argument("--project-dir", type=Path, required=True, help="Project directory")
    parser.add_argument("--max-iterations", type=int, default=None, help="Max iterations (default: unlimited)")
    parser.add_argument("--model", type=str, default="claude-sonnet-4-5-20250929", help="Claude model")

    args = parser.parse_args()

    # Validate token
    if not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        print("❌ Error: CLAUDE_CODE_OAUTH_TOKEN not set")
        print("Run: claude setup-token")
        sys.exit(1)

    # Validate gh CLI
    try:
        result = subprocess.run(["gh", "auth", "status"], capture_output=True, shell=(sys.platform=='win32'))
        if result.returncode != 0:
            print("❌ Error: GitHub CLI not authenticated")
            print("Run: gh auth login")
            sys.exit(1)
        print("✓ GitHub CLI authenticated\n")
    except:
        print("❌ Error: GitHub CLI not found")
        sys.exit(1)

    # Setup project directory
    project_dir = args.project_dir.resolve()
    if "generations" not in str(project_dir):
        project_dir = Path.cwd() / "generations" / project_dir.name

    project_dir.mkdir(parents=True, exist_ok=True)

    # Run agent
    asyncio.run(main(project_dir, args.model, args.max_iterations))
