"""
Comprehensive Structured Logging System
========================================

Production-grade logging for autonomous agents with:
- Structured JSON logging to files
- Rotating file handlers
- Real-time console output
- Session tracking
- Performance metrics
- Error tracking
- GitHub API call logging

Features:
- Multi-level logging (DEBUG, INFO, WARNING, ERROR)
- Automatic log rotation (daily + size-based)
- JSON structured format for parsing
- Session-based log files
- Performance timing
- API call tracking
"""

import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import time
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import sys


class StructuredLogger:
    """
    Structured logging system with JSON output and multiple handlers.

    Log Structure:
    {
        "timestamp": "2025-12-11T10:30:45.123Z",
        "level": "INFO",
        "session_id": "session_001",
        "agent_type": "coding",
        "category": "github_api",
        "message": "Created issue #56",
        "metadata": {
            "issue_number": 56,
            "title": "Auth - Login flow",
            "duration_ms": 245
        }
    }
    """

    def __init__(
        self,
        project_dir: Path,
        session_id: str,
        agent_type: str = "coding",
        log_level: str = "INFO"
    ):
        self.project_dir = project_dir
        self.session_id = session_id
        self.agent_type = agent_type
        self.log_dir = project_dir / "logs"
        self.log_dir.mkdir(exist_ok=True)

        # Create loggers
        self.logger = self._setup_logger(log_level)

        # Performance tracking
        self.timers: Dict[str, float] = {}
        self.metrics = {
            'github_api_calls': 0,
            'github_api_cached': 0,
            'tools_used': {},
            'errors': 0,
            'session_start': datetime.now().isoformat(),
            # T058: Productivity metrics
            'productivity': {
                'tool_count': 0,
                'files_changed': 0,
                'issues_closed': 0,
                'score': 0.0,
                'warnings': []
            }
        }

    def _setup_logger(self, log_level: str) -> logging.Logger:
        """Set up multi-handler logger with structured output."""
        logger = logging.getLogger(f"agent_{self.session_id}")
        logger.setLevel(getattr(logging, log_level.upper()))
        logger.handlers = []  # Clear existing handlers

        # 1. Session-specific JSON log file (detailed)
        session_log_file = self.log_dir / f"session_{self.session_id}.jsonl"
        session_handler = logging.FileHandler(session_log_file, mode='a')
        session_handler.setLevel(logging.DEBUG)
        session_handler.setFormatter(StructuredFormatter(self.session_id, self.agent_type))
        logger.addHandler(session_handler)

        # 2. Daily rotating log file (all sessions)
        daily_log_file = self.log_dir / "agent_daily.log"
        daily_handler = TimedRotatingFileHandler(
            daily_log_file,
            when='midnight',
            interval=1,
            backupCount=30
        )
        daily_handler.setLevel(logging.INFO)
        daily_handler.setFormatter(StructuredFormatter(self.session_id, self.agent_type))
        logger.addHandler(daily_handler)

        # 3. Error log file (errors only, size-based rotation)
        error_log_file = self.log_dir / "errors.log"
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(StructuredFormatter(self.session_id, self.agent_type))
        logger.addHandler(error_handler)

        # 4. Console handler (human-readable)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(ConsoleFormatter())
        logger.addHandler(console_handler)

        return logger

    def start_timer(self, operation: str):
        """Start timing an operation."""
        self.timers[operation] = time.time()

    def end_timer(self, operation: str) -> float:
        """End timing and return duration in ms."""
        if operation not in self.timers:
            return 0.0
        duration_ms = (time.time() - self.timers[operation]) * 1000
        del self.timers[operation]
        return duration_ms

    def log_github_api_call(
        self,
        operation: str,
        cached: bool = False,
        **metadata
    ):
        """Log GitHub API call with caching info."""
        if cached:
            self.metrics['github_api_cached'] += 1
            self.logger.info(
                f"GitHub API (cached): {operation}",
                extra={
                    'category': 'github_api',
                    'cached': True,
                    'operation': operation,
                    'metadata': metadata
                }
            )
        else:
            self.metrics['github_api_calls'] += 1
            self.logger.info(
                f"GitHub API: {operation}",
                extra={
                    'category': 'github_api',
                    'cached': False,
                    'operation': operation,
                    'metadata': metadata
                }
            )

    def log_tool_use(self, tool_name: str, **metadata):
        """Log tool usage."""
        self.metrics['tools_used'][tool_name] = self.metrics['tools_used'].get(tool_name, 0) + 1

        self.logger.info(
            f"Tool: {tool_name}",
            extra={
                'category': 'tool_use',
                'tool_name': tool_name,
                'metadata': metadata
            }
        )

    def log_issue_claimed(self, issue_id: str, issue_title: str, priority: int):
        """Log when agent claims an issue."""
        self.logger.info(
            f"Claimed issue: {issue_title}",
            extra={
                'category': 'issue_lifecycle',
                'action': 'claimed',
                'issue_id': issue_id,
                'issue_title': issue_title,
                'priority': priority
            }
        )

    def log_issue_completed(
        self,
        issue_id: str,
        issue_title: str,
        duration_minutes: float,
        files_changed: int
    ):
        """Log when agent completes an issue."""
        self.logger.info(
            f"Completed issue: {issue_title}",
            extra={
                'category': 'issue_lifecycle',
                'action': 'completed',
                'issue_id': issue_id,
                'issue_title': issue_title,
                'duration_minutes': duration_minutes,
                'files_changed': files_changed
            }
        )

    def log_verification_test(
        self,
        issue_id: str,
        passed: bool,
        test_type: str,
        **metadata
    ):
        """Log verification test results."""
        level = logging.INFO if passed else logging.WARNING
        self.logger.log(
            level,
            f"Verification {'passed' if passed else 'failed'}: {issue_id}",
            extra={
                'category': 'verification',
                'issue_id': issue_id,
                'passed': passed,
                'test_type': test_type,
                'metadata': metadata
            }
        )

    def log_error(self, error_type: str, error_message: str, **metadata):
        """Log error with metadata."""
        self.metrics['errors'] += 1
        self.logger.error(
            f"Error: {error_type} - {error_message}",
            extra={
                'category': 'error',
                'error_type': error_type,
                'error_message': error_message,
                'metadata': metadata
            },
            exc_info=True
        )

    def log_session_start(self):
        """Log session start."""
        self.logger.info(
            f"Session started: {self.session_id}",
            extra={
                'category': 'session',
                'action': 'start',
                'agent_type': self.agent_type
            }
        )

    def log_productivity_metrics(
        self,
        tool_count: int,
        files_changed: int,
        issues_closed: int,
        productivity_score: float,
        warnings: list = None
    ):
        """
        Log productivity metrics for the session (T058).

        Args:
            tool_count: Total tool calls in session
            files_changed: Files created or modified
            issues_closed: Issues closed this session
            productivity_score: Calculated productivity score
            warnings: List of productivity warning messages
        """
        # Update metrics
        self.metrics['productivity'] = {
            'tool_count': tool_count,
            'files_changed': files_changed,
            'issues_closed': issues_closed,
            'score': productivity_score,
            'warnings': warnings or []
        }

        # Log with appropriate level based on productivity
        level = logging.INFO
        message = f"Productivity: score={productivity_score:.3f}, tools={tool_count}, files={files_changed}, issues={issues_closed}"

        if productivity_score < 0.1 and tool_count >= 30:
            level = logging.WARNING
            message = f"LOW {message}"

        self.logger.log(
            level,
            message,
            extra={
                'category': 'productivity',
                'tool_count': tool_count,
                'files_changed': files_changed,
                'issues_closed': issues_closed,
                'productivity_score': productivity_score,
                'warnings': warnings or []
            }
        )

    def log_session_end(self, issues_completed: int, issues_attempted: int):
        """Log session end with summary."""
        self.metrics['session_end'] = datetime.now().isoformat()

        self.logger.info(
            f"Session completed: {issues_completed}/{issues_attempted} issues",
            extra={
                'category': 'session',
                'action': 'end',
                'issues_completed': issues_completed,
                'issues_attempted': issues_attempted,
                'metrics': self.metrics
            }
        )

    def get_session_summary(self) -> Dict[str, Any]:
        """Get session metrics summary."""
        return {
            'session_id': self.session_id,
            'agent_type': self.agent_type,
            'metrics': self.metrics,
            'log_files': {
                'session': str(self.log_dir / f"session_{self.session_id}.jsonl"),
                'daily': str(self.log_dir / "agent_daily.log"),
                'errors': str(self.log_dir / "errors.log")
            }
        }


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def __init__(self, session_id: str, agent_type: str):
        super().__init__()
        self.session_id = session_id
        self.agent_type = agent_type

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'session_id': self.session_id,
            'agent_type': self.agent_type,
            'message': record.getMessage(),
        }

        # Add extra fields from the record
        if hasattr(record, 'category'):
            log_data['category'] = record.category

        # Add any additional metadata
        extra_fields = ['cached', 'operation', 'tool_name', 'action',
                       'issue_id', 'issue_title', 'priority', 'duration_minutes',
                       'files_changed', 'passed', 'test_type', 'error_type',
                       'error_message', 'issues_completed', 'issues_attempted',
                       'metrics', 'metadata',
                       # T058: Productivity fields
                       'tool_count', 'issues_closed', 'productivity_score', 'warnings']

        for field in extra_fields:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class ConsoleFormatter(logging.Formatter):
    """Human-readable console formatter with colors."""

    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'
    }

    ICONS = {
        'github_api': '📡',
        'tool_use': '🔧',
        'issue_lifecycle': '📋',
        'verification': '✅',
        'error': '❌',
        'session': '🚀',
        'productivity': '📊',  # T058
        'default': 'ℹ️'
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record for console with colors and icons."""
        color = self.COLORS.get(record.levelname, '')
        reset = self.COLORS['RESET']

        # Get icon based on category
        category = getattr(record, 'category', 'default')
        icon = self.ICONS.get(category, self.ICONS['default'])

        # Format timestamp
        timestamp = datetime.now().strftime('%H:%M:%S')

        # Build message
        message = record.getMessage()

        # Add cached indicator
        if hasattr(record, 'cached') and record.cached:
            message = f"{message} [CACHED]"

        return f"{color}{icon} [{timestamp}] {message}{reset}"


def create_logger(
    project_dir: Path,
    session_id: Optional[str] = None,
    agent_type: str = "coding",
    log_level: str = "INFO"
) -> StructuredLogger:
    """
    Factory function to create structured logger.

    Usage:
        logger = create_logger(project_dir, session_id="session_001")
        logger.log_session_start()
        logger.log_github_api_call("gh issue list", cached=True)
        logger.log_issue_claimed("#56", "Auth flow", priority=1)
        logger.log_session_end(issues_completed=1, issues_attempted=1)

        summary = logger.get_session_summary()
        print(f"Logs saved to: {summary['log_files']['session']}")
    """
    if session_id is None:
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    return StructuredLogger(project_dir, session_id, agent_type, log_level)
