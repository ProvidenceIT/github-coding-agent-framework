"""
Optimized Autonomous Coding Agent Demo
=======================================

Fully optimized version with:
- GitHub API caching (60-80% reduction)
- YOLO security mode (configurable)
- Enhanced logging (structured JSON + console)
- Rich GitHub integration (milestones, health status)
- Performance monitoring

Usage:
    python autonomous_agent_optimized.py --project-dir ./my_project
    python autonomous_agent_optimized.py --project-dir ./my_project --yolo
    python autonomous_agent_optimized.py --project-dir ./my_project --ultra-yolo
    python autonomous_agent_optimized.py --project-dir ./my_project --max-iterations 5
"""

import asyncio
import os
import sys
import subprocess
from pathlib import Path
import argparse
from datetime import datetime

# Import optimized modules
from github_cache import GitHubCache
from logging_system import create_logger
from github_enhanced import create_enhanced_integration
from git_utils import create_git_manager
from agent import run_agent_session
from prompts import get_initializer_prompt, get_coding_prompt

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def check_gh_auth() -> bool:
    """Check if GitHub CLI is authenticated."""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def validate_environment():
    """Validate required environment variables and GitHub CLI auth."""
    oauth_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")

    if not oauth_token:
        print("❌ Error: CLAUDE_CODE_OAUTH_TOKEN environment variable not set.")
        print("Run 'claude setup-token' to generate a token.")
        sys.exit(1)

    if not check_gh_auth():
        print("❌ Error: GitHub CLI is not authenticated.")
        print("Run 'gh auth login' to authenticate with GitHub.")
        sys.exit(1)

    print("✅ Environment validated (Claude token + GitHub CLI auth)")


def create_client_with_mode(project_dir: Path, model: str, security_mode: str):
    """Create client based on security mode."""
    if security_mode == 'yolo':
        from security_yolo import create_yolo_client
        print("🚀 Using YOLO security mode (unrestricted commands)")
        return create_yolo_client(project_dir, model)
    elif security_mode == 'ultra-yolo':
        from security_yolo import create_ultra_yolo_client
        print("💀 Using ULTRA YOLO security mode (no sandbox!)")
        return create_ultra_yolo_client(project_dir, model)
    else:
        from client import create_client
        print("🔒 Using standard security mode (allowlist)")
        return create_client(project_dir, model)


async def run_optimized_autonomous_agent(
    project_dir: Path,
    model: str,
    max_iterations: int = None,
    security_mode: str = 'standard',
    log_level: str = 'INFO',
    auto_push: bool = True
):
    """
    Run autonomous agent with all optimizations enabled.

    Args:
        project_dir: Directory for the project
        model: Claude model to use
        max_iterations: Maximum number of iterations (None = unlimited)
        security_mode: 'standard', 'yolo', or 'ultra-yolo'
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        auto_push: Automatically commit and push after each session (default: True)
    """
    # Ensure absolute path
    project_dir = project_dir.resolve()
    project_dir.mkdir(parents=True, exist_ok=True)

    # Initialize optimized modules
    cache = GitHubCache(project_dir)
    integration = create_enhanced_integration(project_dir, cache)
    git_mgr = create_git_manager(project_dir, auto_push=auto_push)

    # Check if this is first run
    github_marker = project_dir / ".github_project.json"
    is_first_run = not github_marker.exists()

    # Print startup banner
    print("\n" + "="*70)
    print("  OPTIMIZED GITHUB CODING AGENT")
    print("="*70)
    print(f"  Project: {project_dir.name}")
    print(f"  Model: {model}")
    print(f"  Security: {security_mode}")
    print(f"  Mode: {'Initializer (first run)' if is_first_run else 'Coding agent'}")
    print(f"  Optimizations: Caching ✓ | Enhanced GitHub ✓ | Structured Logging ✓")
    print("="*70 + "\n")

    # Display initial progress if not first run
    if not is_first_run:
        print(integration.generate_progress_report())
        print()

    iteration = 0
    while True:
        iteration += 1

        if max_iterations and iteration > max_iterations:
            print(f"\n✅ Reached maximum iterations ({max_iterations})")
            break

        # Generate session ID
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{iteration:03d}"
        agent_type = "initializer" if is_first_run else "coding"

        # Create logger for this session
        logger = create_logger(project_dir, session_id, agent_type, log_level)
        logger.log_session_start()

        print(f"\n{'='*70}")
        print(f"  SESSION {iteration}: {session_id}")
        print(f"{'='*70}\n")

        # Start session timer
        logger.start_timer('session')

        try:
            # Create fresh client for this session
            client = create_client_with_mode(project_dir, model, security_mode)

            # Choose prompt
            if is_first_run:
                prompt = get_initializer_prompt()
                print("📝 Running initializer agent (creating GitHub project and issues)")
            else:
                prompt = get_coding_prompt()
                print("🔨 Running coding agent (working on GitHub issues)")

            # Run agent session
            print(f"🤖 Starting agent with model: {model}\n")

            async with client:
                status, response = await run_agent_session(
                    client,
                    prompt,
                    project_dir,
                    logger=logger  # Pass logger to agent
                )

            # End session timer
            session_duration_ms = logger.end_timer('session')
            session_duration_min = session_duration_ms / 1000 / 60

            # Log session end
            logger.metrics['duration_minutes'] = round(session_duration_min, 2)
            logger.log_session_end(
                issues_completed=0,  # TODO: Track from response
                issues_attempted=1
            )

            # Print session summary
            summary = logger.get_session_summary()
            print(f"\n{'='*70}")
            print(f"  SESSION COMPLETE")
            print(f"{'='*70}")
            print(f"  Duration: {summary['metrics']['duration_minutes']} minutes")
            print(f"  GitHub API Calls: {summary['metrics']['github_api_calls']}")
            print(f"  Cached Calls: {summary['metrics']['github_api_cached']}")
            print(f"  Errors: {summary['metrics']['errors']}")
            print(f"\n  Log Files:")
            print(f"    - Session: {summary['log_files']['session']}")
            print(f"    - Daily: {summary['log_files']['daily']}")
            print(f"    - Errors: {summary['log_files']['errors']}")
            print(f"{'='*70}\n")

            # Auto-commit and push if enabled
            if auto_push:
                print("📝 Committing and pushing changes...")
                commit_success, commit_msg = git_mgr.commit_and_push(
                    issues_completed=[],  # TODO: Track from GitHub
                    issues_attempted=[],
                    session_metrics=logger.metrics,
                    session_id=session_id
                )

                if commit_success:
                    print(f"✅ {commit_msg}\n")
                else:
                    print(f"⚠️  Git operation: {commit_msg}\n")
                    if "Authentication required" in commit_msg:
                        print("   💡 Tip: Run 'gh auth login' or set up SSH keys")
                        print("   💡 Or disable auto-push with --no-push flag\n")

            # Check API usage
            api_stats = cache.get_api_stats()
            if api_stats['calls_last_hour'] > 4000:
                print(f"⚠️  WARNING: High API usage ({api_stats['calls_last_hour']}/5000 in last hour)")
                print(f"   Consider increasing delay or reducing iterations\n")

            # After first run, switch to coding agent
            if is_first_run:
                is_first_run = False
                print("✅ Initialization complete! Future runs will use coding agent.\n")

            # Status determines whether to continue
            if status == "error":
                print(f"❌ Session ended with error. Retrying with fresh context...\n")
                # Continue to next iteration
            else:
                print(f"✅ Session completed successfully.\n")

        except Exception as e:
            logger.log_error("session_error", str(e))
            print(f"❌ Error during session: {e}")
            print(f"   Retrying with fresh context...\n")

        # Auto-continue with delay (3 seconds)
        if max_iterations is None or iteration < max_iterations:
            print(f"⏸️  Waiting 3 seconds before next session...\n")
            await asyncio.sleep(3)

    # Final summary
    print("\n" + "="*70)
    print("  AGENT RUN COMPLETE")
    print("="*70)
    print(integration.generate_progress_report())
    print("="*70 + "\n")


def main():
    """CLI entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Optimized Autonomous Coding Agent with GitHub Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Standard mode with caching
  python autonomous_agent_optimized.py --project-dir ./my_project

  # YOLO mode (unrestricted commands)
  python autonomous_agent_optimized.py --project-dir ./my_project --yolo

  # Ultra YOLO mode (no sandbox)
  python autonomous_agent_optimized.py --project-dir ./my_project --ultra-yolo

  # Limited iterations
  python autonomous_agent_optimized.py --project-dir ./my_project --max-iterations 5

  # Debug logging
  python autonomous_agent_optimized.py --project-dir ./my_project --log-level DEBUG
        """
    )

    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path("./autonomous_demo_project"),
        help="Directory for the project (default: ./autonomous_demo_project)"
    )

    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Maximum number of agent iterations (default: unlimited)"
    )

    parser.add_argument(
        "--model",
        type=str,
        default="claude-opus-4-5-20251101",
        help="Claude model to use (default: claude-opus-4-5-20251101)"
    )

    parser.add_argument(
        "--yolo",
        action="store_true",
        help="Enable YOLO security mode (unrestricted commands, sandbox enabled)"
    )

    parser.add_argument(
        "--ultra-yolo",
        action="store_true",
        help="Enable ULTRA YOLO mode (no sandbox, full system access - use with caution!)"
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )

    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Disable automatic git push after each session"
    )

    args = parser.parse_args()

    # Determine security mode
    if args.ultra_yolo:
        security_mode = 'ultra-yolo'
    elif args.yolo:
        security_mode = 'yolo'
    else:
        security_mode = 'standard'

    # Validate environment
    validate_environment()

    # Normalize project directory (ensure it's under generations/)
    project_dir = args.project_dir
    if not project_dir.is_absolute():
        project_dir = Path.cwd() / project_dir

    # Ensure projects are in generations/ directory
    if "generations" not in str(project_dir):
        generations_dir = Path.cwd() / "generations"
        generations_dir.mkdir(exist_ok=True)
        project_dir = generations_dir / project_dir.name
        print(f"📁 Placing project in: {project_dir}\n")

    # Run the agent
    asyncio.run(run_optimized_autonomous_agent(
        project_dir=project_dir,
        model=args.model,
        max_iterations=args.max_iterations,
        security_mode=security_mode,
        log_level=args.log_level,
        auto_push=not args.no_push
    ))


if __name__ == "__main__":
    main()
