"""
Gemini Provider
================

Adapter for Google Gemini CLI as an AI agent provider.

Feature: 002-multi-sdk
"""

import asyncio
import json
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


class GeminiProvider(BaseProvider):
    """
    Google Gemini CLI provider implementation.

    Uses subprocess to invoke the `gemini` CLI with JSON output.

    Configuration:
        auth_env_var: GEMINI_API_KEY (default)
        model: gemini-2.5-flash (default)
        extra.output_format: json (default)
        extra.include_directories: list of paths to include
    """

    DEFAULT_AUTH_ENV = "GEMINI_API_KEY"
    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._process: Optional[subprocess.Popen] = None
        self._working_dir: Optional[str] = None
        self._start_time: Optional[float] = None

    @property
    def name(self) -> str:
        return "gemini"

    async def validate(self) -> bool:
        """
        Validate Gemini CLI is available and authenticated.

        Checks:
        1. `gemini` command exists in PATH
        2. GEMINI_API_KEY is set (or Google OAuth configured)
        3. Basic command execution works

        Returns:
            True if validation passes

        Raises:
            ProviderValidationError: With specific failure reason
        """
        # Check CLI availability
        if not shutil.which("gemini"):
            raise ProviderValidationError(
                self.name,
                "Gemini CLI not found. Install via: npm install -g @google/gemini-cli",
                recoverable=False
            )

        # Check authentication (API key is preferred for automation)
        auth_var = self.config.auth_env_var or self.DEFAULT_AUTH_ENV
        token = os.environ.get(auth_var)

        # Also check alternative auth methods
        vertex_key = os.environ.get("GOOGLE_API_KEY")
        vertex_flag = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI")

        if not token and not (vertex_key and vertex_flag):
            raise ProviderValidationError(
                self.name,
                f"No authentication configured. Set {auth_var} or configure Vertex AI",
                recoverable=False
            )

        # Verify CLI responds
        try:
            result = subprocess.run(
                ["gemini", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise ProviderValidationError(
                    self.name,
                    f"Gemini CLI error: {result.stderr}",
                    recoverable=True
                )
        except subprocess.TimeoutExpired:
            raise ProviderValidationError(
                self.name,
                "Gemini CLI timed out during validation",
                recoverable=True
            )
        except FileNotFoundError:
            raise ProviderValidationError(
                self.name,
                "Gemini CLI not found in PATH",
                recoverable=False
            )

        self._health_status = HealthStatus.HEALTHY
        return True

    async def query(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Send prompt via Gemini CLI.

        Args:
            prompt: User prompt
            context: Optional context with:
                - working_directory: str
                - include_directories: list[str]
        """
        context = context or {}
        self._start_time = time.time()

        # Build command
        cmd = ["gemini", "-p", prompt]

        # Add model
        model = self.config.model or self.DEFAULT_MODEL
        cmd.extend(["-m", model])

        # Add JSON output for parsing
        output_format = self.config.extra.get("output_format", "json")
        cmd.extend(["--output-format", output_format])

        # Add directory includes
        include_dirs = context.get(
            "include_directories",
            self.config.extra.get("include_directories", [])
        )
        if include_dirs:
            cmd.extend(["--include-directories", ",".join(include_dirs)])

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
                f"Failed to start Gemini CLI: {str(e)}",
                recoverable=True
            )

    async def receive_response(self) -> AsyncIterator[ProviderMessage]:
        """
        Stream responses from Gemini CLI.

        Yields:
            ProviderMessage for each JSON response chunk
        """
        if not self._process:
            raise ProviderQueryError(
                self.name,
                "No active process. Call query() first.",
                recoverable=False
            )

        try:
            # Read stdout line by line (stream-json mode)
            while True:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, self._process.stdout.readline
                )

                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                # Parse JSON response
                try:
                    data = json.loads(line)
                    content = data.get("content", data.get("text", str(data)))

                    yield ProviderMessage(
                        role="assistant",
                        content=content,
                        provider=self.name,
                        metadata={"raw_response": data}
                    )
                except json.JSONDecodeError:
                    # Plain text response
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
        """Check if Gemini provider is usable."""
        return self._health_status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
