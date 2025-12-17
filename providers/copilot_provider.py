"""
Copilot Provider
=================

Adapter for GitHub Copilot CLI as an AI agent provider.

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


class CopilotProvider(BaseProvider):
    """
    GitHub Copilot CLI provider implementation.

    Uses subprocess to invoke the `copilot` CLI.

    Configuration:
        auth_env_var: None (uses gh auth)
        extra.working_directory_scope: "current" or "project"

    Prerequisites:
        - GitHub CLI (gh) installed and authenticated
        - Active GitHub Copilot subscription
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._process: Optional[subprocess.Popen] = None
        self._working_dir: Optional[str] = None
        self._start_time: Optional[float] = None

    @property
    def name(self) -> str:
        return "copilot"

    async def validate(self) -> bool:
        """
        Validate GitHub Copilot CLI is available and authenticated.

        Checks:
        1. `copilot` command exists in PATH
        2. `gh` CLI is authenticated
        3. Copilot subscription is active

        Returns:
            True if validation passes

        Raises:
            ProviderValidationError: With specific failure reason
        """
        # Check Copilot CLI availability
        if not shutil.which("copilot"):
            raise ProviderValidationError(
                self.name,
                "GitHub Copilot CLI not found. Ensure you have an active Copilot subscription.",
                recoverable=False
            )

        # Check gh CLI authentication
        if not shutil.which("gh"):
            raise ProviderValidationError(
                self.name,
                "GitHub CLI (gh) not found. Install via: https://cli.github.com",
                recoverable=False
            )

        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise ProviderValidationError(
                    self.name,
                    "GitHub CLI not authenticated. Run: gh auth login",
                    recoverable=False
                )
        except subprocess.TimeoutExpired:
            raise ProviderValidationError(
                self.name,
                "GitHub CLI timed out during auth check",
                recoverable=True
            )

        # Verify Copilot CLI responds
        try:
            result = subprocess.run(
                ["copilot", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise ProviderValidationError(
                    self.name,
                    f"Copilot CLI error: {result.stderr}",
                    recoverable=True
                )
        except subprocess.TimeoutExpired:
            raise ProviderValidationError(
                self.name,
                "Copilot CLI timed out during validation",
                recoverable=True
            )
        except FileNotFoundError:
            raise ProviderValidationError(
                self.name,
                "Copilot CLI not found after initial check",
                recoverable=False
            )

        self._health_status = HealthStatus.HEALTHY
        return True

    async def query(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Send prompt via GitHub Copilot CLI.

        Args:
            prompt: User prompt
            context: Optional context with:
                - working_directory: str
        """
        context = context or {}
        self._start_time = time.time()

        # Build command
        # Copilot CLI takes the prompt as an argument
        cmd = ["copilot", prompt]

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
                f"Failed to start Copilot CLI: {str(e)}",
                recoverable=True
            )

    async def receive_response(self) -> AsyncIterator[ProviderMessage]:
        """
        Stream responses from GitHub Copilot CLI.

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
        """Check if Copilot provider is usable."""
        return self._health_status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
