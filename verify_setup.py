"""
Quick Setup Verification Script
================================

Run this before starting the autonomous agent to verify everything is configured correctly.
"""

import os
import sys
import subprocess
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def check_mark(condition):
    return "OK" if condition else "FAIL"


def main():
    print("\n" + "="*70)
    print("  AUTONOMOUS AGENT SETUP VERIFICATION")
    print("="*70 + "\n")

    all_good = True

    # 1. Check Python version
    print("1. Checking Python version...")
    python_version = sys.version_info
    python_ok = python_version >= (3, 8)
    print(f"   {check_mark(python_ok)} Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    if not python_ok:
        print("   ⚠️  Python 3.8+ required")
        all_good = False

    # 2. Check required packages
    print("\n2. Checking required Python packages...")
    required_packages = [
        "claude_code_sdk",
        "dotenv",
        "asyncio",
    ]

    for package in required_packages:
        try:
            __import__(package if package != "dotenv" else "dotenv")
            print(f"   ✓ {package}")
        except ImportError:
            print(f"   ✗ {package} - Run: pip install {package}")
            all_good = False

    # 3. Check Claude CLI
    print("\n3. Checking Claude Code CLI...")
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            shell=(sys.platform == 'win32')  # Use shell on Windows for PATH resolution
        )
        if result.returncode == 0:
            print(f"   OK Claude CLI installed: {result.stdout.strip()}")
        else:
            print("   FAIL Claude CLI not working")
            print("        Install: npm install -g @anthropics/claude-code")
            all_good = False
    except FileNotFoundError:
        print("   FAIL Claude CLI not found")
        print("        Install: npm install -g @anthropics/claude-code")
        all_good = False
    except subprocess.TimeoutExpired:
        print("   FAIL Claude CLI timed out")
        all_good = False

    # 4. Check OAuth token
    print("\n4. Checking Claude OAuth token...")
    token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if token:
        print(f"   ✓ Token set (length: {len(token)})")
    else:
        print("   ✗ CLAUDE_CODE_OAUTH_TOKEN not set")
        print("      Run: claude setup-token")
        all_good = False

    # 5. Check GitHub CLI
    print("\n5. Checking GitHub CLI...")
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("   ✓ GitHub CLI authenticated")
        else:
            print("   ✗ GitHub CLI not authenticated")
            print("      Run: gh auth login")
            all_good = False
    except FileNotFoundError:
        print("   ✗ GitHub CLI not found")
        print("      Install: https://cli.github.com/")
        all_good = False
    except subprocess.TimeoutExpired:
        print("   ✗ GitHub CLI timed out")
        all_good = False

    # 6. Check network connectivity
    print("\n6. Checking network connectivity...")
    try:
        import socket
        socket.create_connection(("api.anthropic.com", 443), timeout=5)
        print("   ✓ Can reach api.anthropic.com")
    except Exception as e:
        print(f"   ✗ Cannot reach api.anthropic.com: {e}")
        print("      Check firewall/proxy settings")
        all_good = False

    # 7. Check project files
    print("\n7. Checking required project files...")
    required_files = [
        "autonomous_agent_optimized.py",
        "connection_helper.py",
        "security_yolo.py",
        "agent.py",
        "client.py",
        "prompts.py",
        "logging_system.py",
        "github_cache.py",
        "github_enhanced.py",
        "git_utils.py",
    ]

    for file in required_files:
        file_path = Path(file)
        exists = file_path.exists()
        print(f"   {check_mark(exists)} {file}")
        if not exists:
            all_good = False

    # 8. Check prompts directory
    print("\n8. Checking prompts directory...")
    prompts_files = [
        "prompts/initializer_prompt.md",
        "prompts/coding_prompt.md",
        "prompts/app_spec.txt",
    ]

    for file in prompts_files:
        file_path = Path(file)
        exists = file_path.exists()
        print(f"   {check_mark(exists)} {file}")
        if not exists:
            all_good = False

    # Summary
    print("\n" + "="*70)
    if all_good:
        print("  ✅ ALL CHECKS PASSED - Ready to run autonomous agent!")
        print("="*70)
        print("\nTo start the agent, run:")
        print("  python autonomous_agent_optimized.py --project-dir ./my_project --yolo")
        print()
        return 0
    else:
        print("  ❌ SOME CHECKS FAILED - Fix the issues above before running")
        print("="*70)
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
