"""
Token Rotation System for Claude Agent SDK
==========================================

Automatically rotates between multiple API keys or OAuth tokens when rate limits are hit.

Supports:
- ANTHROPIC_API_KEY (API key authentication)
- CLAUDE_CODE_OAUTH_TOKEN (OAuth authentication for Claude Pro/Max subscriptions)

Environment Variable Naming Convention:
--------------------------------------
Primary tokens (used first):
    CLAUDE_CODE_OAUTH_TOKEN      - Primary OAuth token
    ANTHROPIC_API_KEY            - Primary API key

Backup tokens (rotated to when limits hit):
    CLAUDE_CODE_OAUTH_TOKEN_1, CLAUDE_CODE_OAUTH_TOKEN_2, ...
    CLAUDE_CODE_OAUTH_TOKEN_BACKUP, CLAUDE_CODE_OAUTH_TOKEN_BACKUP_1, ...

    ANTHROPIC_API_KEY_1, ANTHROPIC_API_KEY_2, ...
    ANTHROPIC_API_KEY_BACKUP, ANTHROPIC_API_KEY_BACKUP_1, ...

Usage:
------
    from token_rotator import TokenRotator, create_rate_limit_hooks

    # Auto-detect all tokens from .env / environment
    rotator = TokenRotator.from_env()
    rotator.sync_env()

    # Create hooks for Claude SDK
    pre_hook, post_hook = create_rate_limit_hooks(rotator)
"""

import os
import re
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any, Callable

logger = logging.getLogger(__name__)


class AuthType(Enum):
    """Authentication type for tokens."""
    API_KEY = "ANTHROPIC_API_KEY"
    OAUTH_TOKEN = "CLAUDE_CODE_OAUTH_TOKEN"


@dataclass
class Token:
    """Represents a single authentication token."""
    value: str
    name: str
    auth_type: AuthType
    cooldown_until: Optional[datetime] = None
    usage_count: int = 0
    rate_limit_hits: int = 0
    last_used: Optional[datetime] = None

    @property
    def is_available(self) -> bool:
        """Check if token is available (not in cooldown)."""
        if self.cooldown_until is None:
            return True
        return datetime.now() >= self.cooldown_until

    @property
    def cooldown_remaining_seconds(self) -> float:
        """Get remaining cooldown time in seconds."""
        if self.cooldown_until is None:
            return 0
        remaining = (self.cooldown_until - datetime.now()).total_seconds()
        return max(0, remaining)


class TokenRotator:
    """
    Token rotator supporting both API keys and OAuth tokens.

    Automatically switches tokens when rate limits are detected.

    Example:
        # From environment (recommended)
        rotator = TokenRotator.from_env()

        # Or explicit tokens
        rotator = TokenRotator.from_oauth_tokens([
            (os.getenv("CLAUDE_CODE_OAUTH_TOKEN"), "primary"),
            (os.getenv("CLAUDE_CODE_OAUTH_TOKEN_BACKUP"), "backup"),
        ])
    """

    # Rate limit detection patterns
    RATE_LIMIT_PATTERNS = [
        "rate limit",
        "rate_limit",
        "429",
        "too many requests",
        "quota exceeded",
        "request limit",
        "usage limit",
        "capacity",
        "overloaded",
        "exceeded your current quota",
        "rate-limited",
        "throttled",
        "approaching.*limit",
        "limit.*reached",
    ]

    def __init__(
        self,
        tokens: List[Token],
        cooldown_minutes: int = 5,
        on_rotate: Optional[Callable[[str, str, str], None]] = None
    ):
        """
        Initialize token rotator.

        Args:
            tokens: List of Token objects
            cooldown_minutes: Minutes to wait before reusing a rate-limited token
            on_rotate: Optional callback(old_name, new_name, reason) called on rotation
        """
        if not tokens:
            raise ValueError("At least one token is required")

        self.tokens = tokens
        self.current_index = 0
        self.cooldown_minutes = cooldown_minutes
        self.on_rotate = on_rotate
        self.rotation_count = 0
        self.started_at = datetime.now()

        logger.info(f"TokenRotator initialized with {len(tokens)} tokens")

    @classmethod
    def from_api_keys(
        cls,
        keys: List[Tuple[str, str]],
        cooldown_minutes: int = 5
    ) -> 'TokenRotator':
        """
        Create rotator from list of (api_key, name) tuples.

        Args:
            keys: List of (api_key_value, friendly_name) tuples
            cooldown_minutes: Cooldown period for rate-limited keys
        """
        tokens = [
            Token(key, name, AuthType.API_KEY)
            for key, name in keys
            if key  # Skip None/empty values
        ]
        return cls(tokens, cooldown_minutes)

    @classmethod
    def from_oauth_tokens(
        cls,
        oauth_tokens: List[Tuple[str, str]],
        cooldown_minutes: int = 5
    ) -> 'TokenRotator':
        """
        Create rotator from list of (oauth_token, name) tuples.

        Args:
            oauth_tokens: List of (oauth_token_value, friendly_name) tuples
            cooldown_minutes: Cooldown period for rate-limited tokens
        """
        tokens = [
            Token(token, name, AuthType.OAUTH_TOKEN)
            for token, name in oauth_tokens
            if token  # Skip None/empty values
        ]
        return cls(tokens, cooldown_minutes)

    @classmethod
    def from_env(
        cls,
        cooldown_minutes: int = 5,
        env_file: Optional[Path] = None
    ) -> 'TokenRotator':
        """
        Auto-detect tokens from environment variables.

        Loads from .env file if available, then checks environment.

        Looks for:
        - CLAUDE_CODE_OAUTH_TOKEN, CLAUDE_CODE_OAUTH_TOKEN_1, CLAUDE_CODE_OAUTH_TOKEN_2, etc.
        - ANTHROPIC_API_KEY, ANTHROPIC_API_KEY_1, ANTHROPIC_API_KEY_2, etc.

        Args:
            cooldown_minutes: Cooldown period for rate-limited tokens
            env_file: Optional path to .env file
        """
        # Load .env file if specified or exists
        if env_file is None:
            env_file = Path.cwd() / ".env"

        if env_file.exists():
            cls._load_env_file(env_file)
            logger.info(f"Loaded environment from {env_file}")

        tokens = []

        # Suffixes to check for backup tokens
        suffixes = [
            "",  # Primary (no suffix)
            "_1", "_2", "_3", "_4", "_5",
            "_BACKUP", "_BACKUP_1", "_BACKUP_2", "_BACKUP_3",
            "_PRIMARY", "_SECONDARY", "_TERTIARY",
        ]

        # Check for OAuth tokens first (preferred for Claude Code)
        for suffix in suffixes:
            key = f"CLAUDE_CODE_OAUTH_TOKEN{suffix}"
            value = os.getenv(key)
            if value and value.strip():
                name = suffix.strip("_") if suffix else "primary"
                tokens.append(Token(value.strip(), f"oauth-{name}", AuthType.OAUTH_TOKEN))
                logger.debug(f"Found OAuth token: {key}")

        # Then check for API keys
        for suffix in suffixes:
            key = f"ANTHROPIC_API_KEY{suffix}"
            value = os.getenv(key)
            if value and value.strip():
                name = suffix.strip("_") if suffix else "primary"
                tokens.append(Token(value.strip(), f"api-{name}", AuthType.API_KEY))
                logger.debug(f"Found API key: {key}")

        if not tokens:
            raise ValueError(
                "No API keys or OAuth tokens found.\n"
                "Set one of:\n"
                "  - CLAUDE_CODE_OAUTH_TOKEN (for Claude Max subscription)\n"
                "  - ANTHROPIC_API_KEY (for API credits)\n"
                "You can add backup tokens with suffixes: _1, _2, _BACKUP, etc."
            )

        logger.info(f"Auto-detected {len(tokens)} tokens from environment")
        for t in tokens:
            logger.info(f"  - {t.name} ({t.auth_type.value})")

        return cls(tokens, cooldown_minutes)

    @staticmethod
    def _load_env_file(env_file: Path):
        """Load environment variables from .env file."""
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    # Parse KEY=value
                    if '=' in line:
                        key, _, value = line.partition('=')
                        key = key.strip()
                        value = value.strip()
                        # Remove quotes if present
                        if value and value[0] == value[-1] and value[0] in '"\'':
                            value = value[1:-1]
                        # Don't override existing env vars
                        if key and not os.getenv(key):
                            os.environ[key] = value
        except Exception as e:
            logger.warning(f"Failed to load .env file: {e}")

    @property
    def current(self) -> Token:
        """Get the current active token."""
        return self.tokens[self.current_index]

    @property
    def current_name(self) -> str:
        """Get the name of the current token."""
        return self.current.name

    @property
    def available_count(self) -> int:
        """Count how many tokens are currently available."""
        return sum(1 for t in self.tokens if t.is_available)

    def rotate(self, reason: str = "manual") -> bool:
        """
        Rotate to the next available token.

        Args:
            reason: Reason for rotation (for logging)

        Returns:
            True if rotation was successful, False if no tokens available
        """
        now = datetime.now()
        old_token = self.current
        old_name = old_token.name

        # Mark current token as rate limited
        old_token.cooldown_until = now + timedelta(minutes=self.cooldown_minutes)
        old_token.rate_limit_hits += 1

        # Find next available token
        found = False
        for _ in range(len(self.tokens)):
            self.current_index = (self.current_index + 1) % len(self.tokens)
            token = self.tokens[self.current_index]

            if token.is_available:
                found = True
                break

        if not found:
            # All tokens on cooldown - use the one with shortest cooldown
            self.current_index = min(
                range(len(self.tokens)),
                key=lambda i: self.tokens[i].cooldown_remaining_seconds
            )
            logger.warning(
                f"All tokens on cooldown! Using {self.current_name} "
                f"(available in {self.current.cooldown_remaining_seconds:.0f}s)"
            )

        self.rotation_count += 1
        new_name = self.current_name

        logger.info(f"Token rotated ({reason}): {old_name} -> {new_name}")

        # Callback
        if self.on_rotate:
            try:
                self.on_rotate(old_name, new_name, reason)
            except Exception as e:
                logger.error(f"Rotation callback error: {e}")

        # Sync to environment
        self.sync_env()

        return found

    def sync_env(self):
        """Sync current token to the appropriate environment variable."""
        token = self.current

        # Clear both to avoid conflicts
        for env_var in [AuthType.API_KEY.value, AuthType.OAUTH_TOKEN.value]:
            if env_var in os.environ:
                del os.environ[env_var]

        # Set the appropriate one
        os.environ[token.auth_type.value] = token.value
        token.last_used = datetime.now()
        token.usage_count += 1

        logger.debug(f"Environment synced: {token.auth_type.value} = {token.name}")

    def check_response_for_rate_limit(self, response: str) -> bool:
        """
        Check if a response indicates a rate limit error.

        Args:
            response: Response text to check

        Returns:
            True if rate limit detected
        """
        response_lower = response.lower()

        for pattern in self.RATE_LIMIT_PATTERNS:
            if re.search(pattern, response_lower):
                return True

        return False

    def get_status(self) -> Dict[str, Any]:
        """Get current status of all tokens."""
        now = datetime.now()
        uptime = (now - self.started_at).total_seconds()

        return {
            "current": self.current_name,
            "auth_type": self.current.auth_type.value,
            "total_tokens": len(self.tokens),
            "available_tokens": self.available_count,
            "rotation_count": self.rotation_count,
            "uptime_seconds": uptime,
            "tokens": [
                {
                    "name": t.name,
                    "auth_type": t.auth_type.value,
                    "is_current": t == self.current,
                    "available": t.is_available,
                    "cooldown_remaining_seconds": t.cooldown_remaining_seconds,
                    "usage_count": t.usage_count,
                    "rate_limit_hits": t.rate_limit_hits,
                    "last_used": t.last_used.isoformat() if t.last_used else None,
                }
                for t in self.tokens
            ]
        }

    def print_status(self):
        """Print a formatted status report."""
        status = self.get_status()
        print(f"\n{'='*50}")
        print(f"Token Rotator Status")
        print(f"{'='*50}")
        print(f"Current: {status['current']} ({status['auth_type']})")
        print(f"Available: {status['available_tokens']}/{status['total_tokens']}")
        print(f"Rotations: {status['rotation_count']}")
        print(f"\nTokens:")
        for t in status['tokens']:
            current = " [ACTIVE]" if t['is_current'] else ""
            available = "available" if t['available'] else f"cooldown {t['cooldown_remaining_seconds']:.0f}s"
            print(f"  - {t['name']}: {available}, used {t['usage_count']}x, rate-limited {t['rate_limit_hits']}x{current}")
        print(f"{'='*50}\n")


def create_rate_limit_hooks(rotator: TokenRotator):
    """
    Create PreToolUse and PostToolUse hooks for Claude Agent SDK.

    These hooks:
    1. Ensure the correct environment variable is set before each tool use
    2. Detect rate limit errors in responses and rotate tokens

    Args:
        rotator: TokenRotator instance

    Returns:
        tuple: (pre_hook, post_hook) async functions for Claude SDK hooks

    Usage with Claude Agent SDK:
        from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

        rotator = TokenRotator.from_env()
        rotator.sync_env()

        pre_hook, post_hook = create_rate_limit_hooks(rotator)

        options = ClaudeCodeOptions(
            allowed_tools=["Bash", "Read", "Write", "Edit", "Glob", "Grep"],
        )

        # Note: Hooks are set via the hooks parameter in the client
    """

    async def pre_tool_hook(input_data, tool_use_id, context):
        """
        Hook called before each tool use.
        Ensures environment variable is synced to current token.
        """
        current = rotator.current
        env_value = os.environ.get(current.auth_type.value)

        # Sync if not matching
        if env_value != current.value:
            rotator.sync_env()
            logger.debug(f"Pre-hook: synced env to {current.name}")

        return {}

    async def post_tool_hook(input_data, tool_use_id, context):
        """
        Hook called after each tool use.
        Checks for rate limit errors and rotates token if needed.
        """
        # Get response from tool
        response = str(input_data.get("tool_response", ""))
        error = str(input_data.get("error", ""))

        # Check both response and error for rate limit indicators
        combined = f"{response} {error}".lower()

        if rotator.check_response_for_rate_limit(combined):
            old_name = rotator.current_name
            success = rotator.rotate(reason="rate limit detected in tool response")

            if success:
                return {
                    "systemMessage": (
                        f"Rate limit detected. Switched from {old_name} to "
                        f"{rotator.current_name} ({rotator.current.auth_type.value}). "
                        f"Retrying operation."
                    ),
                }
            else:
                return {
                    "systemMessage": (
                        f"Rate limit detected but all tokens on cooldown. "
                        f"Waiting for {rotator.current.cooldown_remaining_seconds:.0f}s."
                    ),
                }

        return {}

    return pre_tool_hook, post_tool_hook


def create_response_callback(rotator: TokenRotator):
    """
    Create a callback for monitoring responses from the Claude SDK.

    This can be used with the receive_response() method to detect
    rate limits in streaming responses.

    Returns:
        Callback function that checks for rate limits
    """

    def check_response(message):
        """Check a response message for rate limit errors."""
        content = str(message)

        if rotator.check_response_for_rate_limit(content):
            logger.warning(f"Rate limit detected in response")
            rotator.rotate(reason="rate limit in streaming response")
            return True

        return False

    return check_response


# =============================================================================
# Convenience Functions
# =============================================================================

_global_rotator: Optional[TokenRotator] = None


def get_rotator() -> TokenRotator:
    """Get the global token rotator instance."""
    global _global_rotator
    if _global_rotator is None:
        _global_rotator = TokenRotator.from_env()
        _global_rotator.sync_env()
    return _global_rotator


def set_rotator(rotator: TokenRotator):
    """Set the global token rotator instance."""
    global _global_rotator
    _global_rotator = rotator


def ensure_token_available():
    """
    Ensure a valid token is set in the environment.

    Call this before creating a Claude SDK client to ensure
    the environment is properly configured.
    """
    rotator = get_rotator()
    rotator.sync_env()
    return rotator.current_name


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """CLI interface for testing token rotator."""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(description="Token Rotator for Claude Agent SDK")
    parser.add_argument(
        "--env-file", "-e",
        type=Path,
        default=Path(".env"),
        help="Path to .env file"
    )
    parser.add_argument(
        "--status", "-s",
        action="store_true",
        help="Print status of all tokens"
    )
    parser.add_argument(
        "--rotate", "-r",
        action="store_true",
        help="Force rotation to next token"
    )
    parser.add_argument(
        "--test", "-t",
        action="store_true",
        help="Test token detection from environment"
    )

    args = parser.parse_args()

    try:
        rotator = TokenRotator.from_env(env_file=args.env_file)
        rotator.sync_env()

        if args.test:
            print("Token detection successful!")
            rotator.print_status()
            return

        if args.status:
            rotator.print_status()
            return

        if args.rotate:
            print(f"Current token: {rotator.current_name}")
            rotator.rotate(reason="manual CLI rotation")
            print(f"New token: {rotator.current_name}")
            return

        # Default: print status
        rotator.print_status()

    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
