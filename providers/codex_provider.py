"""
Codex Provider
===============

Adapter for OpenAI Codex CLI as an AI agent provider.

Feature: 002-multi-sdk
"""

import asyncio
import shutil
import subprocess
import time
from typing import AsyncIterator, Optional, Dict, Any
import os

from .base import (
    BaseProvider,
    ProviderConfig,
    ProviderMessage,
    ProviderValidationError,
    ProviderQueryError,
    ProviderResponseError,
    HealthStatus,
)


class CodexProvider(BaseProvider):
    """
    OpenAI Codex CLI provider implementation.

    Uses subprocess to invoke the `codex` CLI in exec mode.

    Configuration:
        auth_env_var: OPENAI_API_KEY (optional, can use ChatGPT auth)
        extra.reasoning_level: "low", "medium", "high"

    Prerequisites:
        - Codex CLI installed (npm install -g @openai/codex)
        - ChatGPT subscription or OpenAI API key
    """

    DEFAULT_AUTH_ENV = "OPENAI_API_KEY"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._process: Optional[subprocess.Popen] = None
        self._working_dir: Optional[str] = None
        self._start_time: Optional[float] = None

    @property
    def name(self) -> str:
        return "codex"

    async def validate(self) -> bool:
        """
        Validate OpenAI Codex CLI is available and authenticated.

        Checks:
        1. `codex` command exists in PATH
        2. Authentication is configured (ChatGPT or API key)
        3. Basic command execution works

        Returns:
            True if validation passes

        Raises:
            ProviderValidationError: With specific failure reason
        """
        # Check Codex CLI availability
        if not shutil.which("codex"):
            raise ProviderValidationError(
                self.name,
                "OpenAI Codex CLI not found. Install via: npm install -g @openai/codex",
                recoverable=False
            )

        # Check authentication
        # Codex can use ChatGPT auth (stored in ~/.codex/) or API key
        auth_var = self.config.auth_env_var or self.DEFAULT_AUTH_ENV
        api_key = os.environ.get(auth_var)

        # Check for config file as alternative auth
        codex_config = os.path.expanduser("~/.codex/config.toml")
        has_config = os.path.exists(codex_config)

        if not api_key and not has_config:
            raise ProviderValidationError(
                self.name,
                f"No authentication configured. Set {auth_var} or run: codex (to sign in with ChatGPT)",
                recoverable=False
            )

        # Verify CLI responds
        try:
            result = subprocess.run(
                ["codex", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise ProviderValidationError(
                    self.name,
                    f"Codex CLI error: {result.stderr}",
                    recoverable=True
                )
        except subprocess.TimeoutExpired:
            raise ProviderValidationError(
                self.name,
                "Codex CLI timed out during validation",
                recoverable=True
            )
        except FileNotFoundError:
            raise ProviderValidationError(
                self.name,
                "Codex CLI not found in PATH",
                recoverable=False
            )

        self._health_status = HealthStatus.HEALTHY
        return True

    async def query(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Send prompt via OpenAI Codex CLI.

        Uses `codex exec` for non-interactive execution.

        Args:
            prompt: User prompt
            context: Optional context with:
                - working_directory: str
                - reasoning_level: str (low/medium/high)
        """
        context = context or {}
        self._start_time = time.time()

        # Build command using exec mode for automation
        cmd = ["codex", "exec", prompt]

        # Set working directory
        self._working_dir = context.get("working_directory", os.getcwd())

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self._working_dir
            )
        except Exception as e:
            self.mark_degraded(str(e))
            raise ProviderQueryError(
                self.name,
                f"Failed to start Codex CLI: {str(e)}",
                recoverable=True
            )

    async def receive_response(self) -> AsyncIterator[ProviderMessage]:
        """
        Stream responses from OpenAI Codex CLI.

        Yields:
            ProviderMessage for each response chunk
        """
        if not self._process:
            raise ProviderQueryError(
                self.name,
                "No active process. Call query() first.",
                recoverable=False
            )

        try:
            # Read stdout line by line
            while True:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, self._process.stdout.readline
                )

                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                yield ProviderMessage(
                    role="assistant",
                    content=line,
                    provider=self.name
                )

            # Check for errors
            stderr = self._process.stderr.read()
            returncode = self._process.wait()

            if returncode != 0:
                error_msg = f"Exit code {returncode}"
                if stderr:
                    error_msg += f": {stderr}"
                self.mark_degraded(error_msg)
            else:
                # Record success
                if self._start_time:
                    elapsed_ms = (time.time() - self._start_time) * 1000
                    self.record_success(elapsed_ms)

        except Exception as e:
            self.mark_unhealthy(str(e))
            raise ProviderResponseError(
                self.name,
                f"Error reading response: {str(e)}",
                recoverable=True
            )
        finally:
            if self._process:
                self._process = None
            self._start_time = None

    def is_healthy(self) -> bool:
        """Check if Codex provider is usable."""
        return self._health_status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
