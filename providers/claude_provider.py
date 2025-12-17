"""
Claude Provider
================

Adapter for Claude Code SDK as an AI agent provider.

Feature: 002-multi-sdk
"""

from typing import AsyncIterator, Optional, Dict, Any
import os
import time

from .base import (
    BaseProvider,
    ProviderConfig,
    ProviderMessage,
    ProviderValidationError,
    ProviderQueryError,
    HealthStatus,
)


class ClaudeProvider(BaseProvider):
    """
    Claude Code SDK provider implementation.

    Uses the existing claude-code-sdk package for communication.

    Configuration:
        auth_env_var: CLAUDE_CODE_OAUTH_TOKEN (default)
        model: claude-opus-4-5-20251101 (default)
        extra.allowed_tools: ["Read", "Write", "Edit", "Glob", "Grep", "Bash"]
    """

    DEFAULT_AUTH_ENV = "CLAUDE_CODE_OAUTH_TOKEN"
    DEFAULT_MODEL = "claude-opus-4-5-20251101"
    DEFAULT_TOOLS = ["Read", "Write", "Edit", "Glob", "Grep", "Bash"]

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._client = None
        self._session_active = False
        self._start_time: Optional[float] = None

    @property
    def name(self) -> str:
        return "claude"

    async def validate(self) -> bool:
        """
        Validate Claude Code SDK is available and authenticated.

        Checks:
        1. claude_code_sdk package is importable
        2. CLAUDE_CODE_OAUTH_TOKEN is set
        3. Token has valid format

        Returns:
            True if validation passes

        Raises:
            ProviderValidationError: With specific failure reason
        """
        # Check SDK availability
        try:
            from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
        except ImportError:
            raise ProviderValidationError(
                self.name,
                "claude-code-sdk package not installed. Run: pip install claude-code-sdk",
                recoverable=False
            )

        # Check authentication
        auth_var = self.config.auth_env_var or self.DEFAULT_AUTH_ENV
        token = os.environ.get(auth_var)
        if not token:
            raise ProviderValidationError(
                self.name,
                f"Environment variable {auth_var} not set",
                recoverable=False
            )

        # Basic token format check
        if len(token) < 20:
            raise ProviderValidationError(
                self.name,
                f"Token in {auth_var} appears invalid (too short)",
                recoverable=False
            )

        self._health_status = HealthStatus.HEALTHY
        return True

    async def query(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Send prompt via Claude Code SDK.

        Args:
            prompt: User prompt
            context: Optional context with:
                - system_prompt: str
                - allowed_tools: list[str]
                - max_turns: int
                - working_directory: str
        """
        from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

        context = context or {}
        self._start_time = time.time()

        # Build options
        system_prompt = context.get("system_prompt", "Autonomous coding agent")
        # Ensure single-line system prompt to avoid timeout issues
        if "\n" in system_prompt:
            system_prompt = system_prompt.replace("\n", " ").strip()

        options = ClaudeCodeOptions(
            system_prompt=system_prompt,
            max_turns=context.get("max_turns", self.config.max_turns),
            allowed_tools=context.get(
                "allowed_tools",
                self.config.extra.get("allowed_tools", self.DEFAULT_TOOLS)
            )
        )

        # Set model if specified
        if self.config.model:
            options.model = self.config.model

        try:
            self._client = ClaudeSDKClient(options=options)
            await self._client.query(prompt)
            self._session_active = True
        except Exception as e:
            self.mark_degraded(str(e))
            raise ProviderQueryError(
                self.name,
                f"Failed to send query: {str(e)}",
                recoverable=True
            )

    async def receive_response(self) -> AsyncIterator[ProviderMessage]:
        """
        Stream responses from Claude Code SDK.

        Yields:
            ProviderMessage for each SDK message
        """
        if not self._client or not self._session_active:
            raise ProviderQueryError(
                self.name,
                "No active session. Call query() first.",
                recoverable=False
            )

        try:
            async for message in self._client.receive_response():
                yield ProviderMessage(
                    role="assistant",
                    content=str(message),
                    provider=self.name,
                    metadata={"raw_message": message}
                )

            # Record success
            if self._start_time:
                elapsed_ms = (time.time() - self._start_time) * 1000
                self.record_success(elapsed_ms)

        except Exception as e:
            self.mark_degraded(str(e))
            raise
        finally:
            self._session_active = False
            self._client = None
            self._start_time = None

    def is_healthy(self) -> bool:
        """Check if Claude provider is usable."""
        return self._health_status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
