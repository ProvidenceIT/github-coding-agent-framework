"""
Connection Helper for Claude SDK Client
========================================

Provides robust connection handling with timeouts, retries, and diagnostics.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from claude_code_sdk import ClaudeSDKClient


class ConnectionError(Exception):
    """Raised when client connection fails."""
    pass


async def connect_with_timeout(
    client: ClaudeSDKClient,
    timeout_seconds: int = 30
) -> None:
    """
    Connect to Claude SDK client with timeout.

    Args:
        client: ClaudeSDKClient instance
        timeout_seconds: Maximum seconds to wait for connection

    Raises:
        ConnectionError: If connection fails or times out
    """
    try:
        # Use asyncio.wait_for to add timeout to the connection
        await asyncio.wait_for(
            client.__aenter__(),
            timeout=timeout_seconds
        )
    except asyncio.TimeoutError:
        raise ConnectionError(
            f"Connection timed out after {timeout_seconds} seconds.\n"
            "Possible causes:\n"
            "  1. Claude Code CLI server not responding\n"
            "  2. Network connectivity issues\n"
            "  3. Invalid OAuth token\n"
            "  4. Firewall blocking connection\n"
            "Try running 'claude --version' to verify CLI installation."
        )
    except Exception as e:
        raise ConnectionError(f"Connection failed: {e}")


@asynccontextmanager
async def managed_client_connection(
    client: ClaudeSDKClient,
    timeout_seconds: int = 30,
    max_retries: int = 2
):
    """
    Async context manager for Claude SDK client with retry logic.

    Args:
        client: ClaudeSDKClient instance
        timeout_seconds: Maximum seconds per connection attempt
        max_retries: Number of retry attempts

    Yields:
        Connected ClaudeSDKClient

    Example:
        async with managed_client_connection(client, timeout_seconds=30) as connected_client:
            await connected_client.query("Hello")
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                wait_time = min(2 ** attempt, 10)  # Exponential backoff, max 10s
                print(f"Retrying connection in {wait_time}s... (attempt {attempt + 1}/{max_retries + 1})")
                await asyncio.sleep(wait_time)

            # Try to connect
            print(f"Connecting to Claude Code CLI... (timeout: {timeout_seconds}s)")
            await connect_with_timeout(client, timeout_seconds)

            try:
                yield client
            finally:
                # Always cleanup
                try:
                    await client.__aexit__(None, None, None)
                except Exception as e:
                    print(f"Warning: Error during client cleanup: {e}")

            return  # Success, exit

        except ConnectionError as e:
            last_error = e
            print(f"❌ Connection failed: {e}")

            if attempt < max_retries:
                print("Will retry...")
            else:
                print("\n" + "="*70)
                print("TROUBLESHOOTING STEPS:")
                print("="*70)
                print("1. Verify Claude CLI is installed:")
                print("   npm list -g @anthropics/claude-code")
                print()
                print("2. Verify OAuth token is set:")
                print("   echo %CLAUDE_CODE_OAUTH_TOKEN%")
                print("   (Should start with 'claude_oauth_token_')")
                print()
                print("3. Try running Claude CLI directly:")
                print("   claude --version")
                print()
                print("4. Regenerate token if needed:")
                print("   claude setup-token")
                print()
                print("5. Check network connectivity:")
                print("   ping api.anthropic.com")
                print("="*70)
                print()

    # All retries failed
    raise last_error


def print_connection_diagnostics():
    """Print diagnostic information about the Claude Code setup."""
    import subprocess

    print("\n" + "="*70)
    print("CONNECTION DIAGNOSTICS")
    print("="*70)

    # Check Claude CLI
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        print(f"✓ Claude CLI: {result.stdout.strip()}")
    except Exception as e:
        print(f"✗ Claude CLI: Not found or error - {e}")

    # Check OAuth token
    import os
    token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if token:
        print(f"✓ OAuth token: Set (length: {len(token)})")
    else:
        print("✗ OAuth token: Not set")

    # Check GitHub CLI
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("✓ GitHub CLI: Authenticated")
        else:
            print("✗ GitHub CLI: Not authenticated")
    except Exception as e:
        print(f"✗ GitHub CLI: Not found or error - {e}")

    print("="*70 + "\n")
