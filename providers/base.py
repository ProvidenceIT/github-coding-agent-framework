"""
Provider Base Classes
=====================

Abstract base class and common types for all AI agent providers.

Feature: 002-multi-sdk
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import AsyncIterator, Optional, List, Dict, Any


class HealthStatus(Enum):
    """Provider health states for selection logic."""
    UNKNOWN = "unknown"      # Not yet validated
    HEALTHY = "healthy"      # Available and working
    DEGRADED = "degraded"    # Experiencing issues
    UNHEALTHY = "unhealthy"  # Failed recently


@dataclass
class ProviderConfig:
    """Provider-specific configuration settings."""
    model: Optional[str] = None
    max_turns: int = 50
    timeout_seconds: int = 300
    auth_env_var: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderMessage:
    """Unified message format across all providers."""
    role: str  # "assistant", "user", "system"
    content: str
    provider: str
    timestamp: datetime = field(default_factory=datetime.now)
    tool_calls: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderStats:
    """Runtime statistics for a single provider."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens: int = 0
    last_response_time_ms: float = 0.0
    error_counts: Dict[str, int] = field(default_factory=dict)


class BaseProvider(ABC):
    """
    Abstract base class for AI agent providers.

    All provider implementations must inherit from this class
    and implement all abstract methods.

    Usage:
        class MyProvider(BaseProvider):
            @property
            def name(self) -> str:
                return "myprovider"

            async def validate(self) -> bool:
                # Check if provider is available
                return True

            # ... implement other abstract methods
    """

    def __init__(self, config: ProviderConfig):
        self.config = config
        self._health_status = HealthStatus.UNKNOWN
        self._last_error: Optional[str] = None
        self._last_used: Optional[datetime] = None
        self._stats = ProviderStats()

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Provider identifier.

        Returns:
            One of: "claude", "gemini", "copilot", "codex"
        """
        pass

    @property
    def health_status(self) -> HealthStatus:
        """Current health status."""
        return self._health_status

    @property
    def last_error(self) -> Optional[str]:
        """Most recent error message."""
        return self._last_error

    @property
    def stats(self) -> ProviderStats:
        """Runtime statistics."""
        return self._stats

    @abstractmethod
    async def validate(self) -> bool:
        """
        Check if provider is available and properly authenticated.

        Should check:
        - CLI/SDK is installed
        - Authentication credentials are present
        - Basic connectivity works

        Returns:
            True if provider is ready to use

        Raises:
            ProviderValidationError: If validation fails with details
        """
        pass

    @abstractmethod
    async def query(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Send a prompt to the provider.

        Args:
            prompt: The user prompt to send
            context: Optional context including:
                - working_directory: Path for file operations
                - system_prompt: Override system instructions
                - allowed_tools: List of permitted tools

        Raises:
            ProviderQueryError: If the query fails to send
        """
        pass

    @abstractmethod
    async def receive_response(self) -> AsyncIterator[ProviderMessage]:
        """
        Stream responses from the provider.

        Yields:
            ProviderMessage objects as they arrive

        Raises:
            ProviderResponseError: If streaming fails
        """
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        """
        Quick check if provider is currently usable.

        Returns:
            True if health_status is HEALTHY or DEGRADED
        """
        pass

    def mark_healthy(self) -> None:
        """Mark provider as healthy after successful operation."""
        self._health_status = HealthStatus.HEALTHY
        self._last_error = None
        self._last_used = datetime.now()

    def mark_degraded(self, error: str) -> None:
        """Mark provider as degraded after minor issue."""
        self._health_status = HealthStatus.DEGRADED
        self._last_error = error
        self._stats.error_counts[error] = self._stats.error_counts.get(error, 0) + 1

    def mark_unhealthy(self, error: str) -> None:
        """Mark provider as unhealthy after failure."""
        self._health_status = HealthStatus.UNHEALTHY
        self._last_error = error
        self._stats.failed_requests += 1
        self._stats.error_counts[error] = self._stats.error_counts.get(error, 0) + 1

    def record_success(self, response_time_ms: float, tokens: int = 0) -> None:
        """Record successful request metrics."""
        self._stats.total_requests += 1
        self._stats.successful_requests += 1
        self._stats.last_response_time_ms = response_time_ms
        self._stats.total_tokens += tokens
        self.mark_healthy()


# =============================================================================
# Provider Exceptions
# =============================================================================

class ProviderError(Exception):
    """Base exception for provider errors."""
    def __init__(self, provider: str, message: str, recoverable: bool = False):
        self.provider = provider
        self.message = message
        self.recoverable = recoverable
        super().__init__(f"[{provider}] {message}")


class ProviderValidationError(ProviderError):
    """Raised when provider validation fails."""
    pass


class ProviderQueryError(ProviderError):
    """Raised when sending a query fails."""
    pass


class ProviderResponseError(ProviderError):
    """Raised when receiving response fails."""
    pass


class NoProvidersAvailableError(Exception):
    """Raised when no providers are available for use."""
    def __init__(self, message: str = "No providers are available"):
        self.message = message
        super().__init__(message)
