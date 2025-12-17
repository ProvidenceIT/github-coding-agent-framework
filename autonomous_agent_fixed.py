"""
Autonomous GitHub Coding Agent - Fixed Version
===============================================

Key fixes:
1. Create client ONCE at start, reuse for all sessions
2. Use single-line system_prompt (multiline prompts cause initialization timeout)
3. Multi-provider support via ProviderPool (002-multi-sdk)

Usage:
    set CLAUDE_CODE_OAUTH_TOKEN=your-token-here
    python autonomous_agent_fixed.py --project-dir ./my_project [--max-iterations 5]

    # Use specific provider
    python autonomous_agent_fixed.py --project-dir ./my_project --provider gemini
"""

import asyncio
import os
import sys
import subprocess
from pathlib import Path
import argparse
from datetime import datetime
import io
import logging
import time
import traceback

# Fix Windows console encoding
if sys.platform == 'win32' and sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
from github_cache import GitHubCache

# Multi-provider support (002-multi-sdk)
try:
    from providers import (
        ProviderPool,
        create_default_pool,
        NoProvidersAvailableError,
        ProviderValidationError,
    )
    MULTI_PROVIDER_AVAILABLE = True
except ImportError:
    MULTI_PROVIDER_AVAILABLE = False
from github_enhanced import create_enhanced_integration
from git_utils import create_git_manager
from prompts import get_initializer_prompt, get_coding_prompt, copy_spec_to_project, set_project_context
from github_config import save_repo_info, get_repo_info, DEFAULT_GITHUB_ORG, GITHUB_ISSUE_LIST_LIMIT, MAX_NO_ISSUES_ROUNDS
from token_rotator import TokenRotator, get_rotator, set_rotator
import re
import json

# Load .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def setup_session_logger(project_dir: Path) -> logging.Logger:
    """
    Create a comprehensive session logger that writes to ./logs/session_TIMESTAMP.log

    Returns:
        Logger instance configured for verbose session logging
    """
    # Create logs directory
    logs_dir = project_dir / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Create timestamped log file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = logs_dir / f"session_{timestamp}.log"

    # Create logger
    logger = logging.getLogger('autonomous_agent')
    logger.setLevel(logging.DEBUG)

    # Remove any existing handlers
    logger.handlers.clear()

    # Create file handler with verbose formatting
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)

    # Create detailed formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Also log to console with less verbose format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    logger.info("="*80)
    logger.info(f"SESSION LOGGER INITIALIZED - Log file: {log_file}")
    logger.info("="*80)

    return logger




def check_session_mandatory_outcomes(
    project_dir: Path,
    session_start_time: datetime,
    logger: logging.Logger = None,
    issues_worked: list = None  # T034: Add issues_worked parameter
) -> dict:
    """
    Check if a session achieved its mandatory outcomes (T034):
    1. At least one issue was closed
    2. META issue was updated
    3. Changes were pushed (or attempted)

    Enhanced to check SPECIFIC issues worked on by this session,
    not time-based queries that count other sessions' work.

    Args:
        project_dir: Project directory
        session_start_time: When the session started
        logger: Optional logger
        issues_worked: List of issue numbers THIS session worked on (T034)

    Returns:
        dict with keys:
            - issues_worked: list of issues this session worked on
            - issues_closed: int
            - issues_closed_list: list of closed issue numbers
            - meta_updated: bool
            - git_pushed: bool
            - success: bool
            - failures: list of failure messages
    """
    import subprocess

    result = {
        'issues_worked': issues_worked or [],  # T034: Include issues_worked
        'issues_closed': 0,
        'issues_closed_list': [],  # T034: Include list of closed issues
        'meta_updated': False,
        'git_pushed': False,
        'success': False,
        'failures': []
    }

    try:
        # T034: Check SPECIFIC issues worked on, not time-based
        if issues_worked:
            for issue_num in issues_worked:
                try:
                    # Check if this specific issue is now closed
                    check = subprocess.run(
                        ['gh', 'issue', 'view', str(issue_num), '--json', 'state', '-q', '.state'],
                        cwd=project_dir,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if check.returncode == 0 and check.stdout.strip().upper() == 'CLOSED':
                        result['issues_closed'] += 1
                        result['issues_closed_list'].append(issue_num)
                        if logger:
                            logger.info(f"Issue #{issue_num} confirmed closed")
                except Exception as e:
                    if logger:
                        logger.warning(f"Failed to check issue #{issue_num}: {e}")

            # T034: Log outcome summary
            if logger:
                logger.info(
                    f"Outcome validation: worked={result['issues_worked']}, "
                    f"closed={result['issues_closed_list']}"
                )
        else:
            # Fallback to time-based check if issues_worked not provided
            check_result = subprocess.run(
                ['gh', 'issue', 'list', '--state', 'closed', '--json', 'number,closedAt', '--limit', str(GITHUB_ISSUE_LIST_LIMIT)],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=30
            )

            if check_result.returncode == 0:
                import json as json_mod
                try:
                    issues = json_mod.loads(check_result.stdout)
                    # Count issues closed in the last hour
                    from datetime import timedelta
                    one_hour_ago = datetime.now() - timedelta(hours=1)

                    for issue in issues:
                        closed_at = issue.get('closedAt', '')
                        if closed_at:
                            try:
                                # Parse ISO format datetime
                                closed_time = datetime.fromisoformat(closed_at.replace('Z', '+00:00'))
                                if closed_time.replace(tzinfo=None) > one_hour_ago:
                                    result['issues_closed'] += 1
                                    result['issues_closed_list'].append(issue['number'])
                            except:
                                pass

                except json_mod.JSONDecodeError:
                    pass

        if result['issues_closed'] == 0:
            if issues_worked:
                result['failures'].append(
                    f"Worked on {len(issues_worked)} issue(s) but none closed: {issues_worked}"
                )
            else:
                result['failures'].append("No issues were closed this session")

        # Check if META issue was updated (look for recent comments)
        meta_check = subprocess.run(
            ['gh', 'issue', 'list', '--search', '[META]', '--json', 'number', '-q', '.[0].number'],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=30
        )

        if meta_check.returncode == 0 and meta_check.stdout.strip():
            meta_number = meta_check.stdout.strip()
            # Check for recent comments (we can't easily check timestamp, but presence is good)
            comment_check = subprocess.run(
                ['gh', 'issue', 'view', meta_number, '--json', 'comments', '-q', '.comments | length'],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            if comment_check.returncode == 0:
                # If there are comments, assume META was updated
                # (In production, you'd want to check comment timestamps)
                comment_count = int(comment_check.stdout.strip() or '0')
                result['meta_updated'] = comment_count > 0
        else:
            result['failures'].append("META issue not found")

        if not result['meta_updated']:
            result['failures'].append("META issue was not updated this session")

        # Check git status
        git_status = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Check if we're ahead of remote
        git_log = subprocess.run(
            ['git', 'log', '--oneline', 'origin/main..HEAD'],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=30
        )

        if git_status.returncode == 0:
            has_uncommitted = bool(git_status.stdout.strip())
            has_unpushed = bool(git_log.stdout.strip()) if git_log.returncode == 0 else False

            if not has_uncommitted and not has_unpushed:
                result['git_pushed'] = True
            elif has_uncommitted:
                result['failures'].append("Uncommitted changes remain")
            elif has_unpushed:
                result['failures'].append("Commits not pushed to remote")

        # Overall success
        result['success'] = (
            result['issues_closed'] >= 1 and
            result['meta_updated'] and
            result['git_pushed']
        )

        if logger:
            logger.info(f"Session outcome check: {result}")

    except Exception as e:
        result['failures'].append(f"Error checking outcomes: {str(e)}")
        if logger:
            logger.error(f"Error in check_session_mandatory_outcomes: {e}")

    return result


def calculate_productivity_score(
    tool_count: int,
    files_changed: int = 0,
    issues_closed: int = 0
) -> float:
    """
    Calculate productivity score based on session metrics (T053).

    Formula: (files_changed * 2 + issues_closed * 5) / max(tool_count, 1)

    A high tool count with low file changes or issue closures indicates
    low productivity (agent is spinning without making progress).

    Args:
        tool_count: Number of tool calls in session
        files_changed: Number of files created or modified
        issues_closed: Number of issues closed

    Returns:
        Productivity score (higher is better, 0.1 is minimum threshold)
    """
    if tool_count <= 0:
        return 0.0

    # Weight files changed (2 points) and issues closed (5 points)
    numerator = (files_changed * 2) + (issues_closed * 5)
    score = numerator / max(tool_count, 1)

    return round(score, 3)


def analyze_session_health(
    response: str,
    session_id: str,
    logger: logging.Logger = None,
    tool_count: int = None,
    files_changed: int = 0,  # T052: Add files_changed parameter
    issues_closed: int = 0    # T052: Add issues_closed parameter
) -> dict:
    """
    Analyze the session response to detect if the agent is doing meaningful work.

    Enhanced with productivity scoring (US6) to detect sessions that run
    many tools but don't accomplish meaningful work.

    Args:
        response: The text response from the agent
        session_id: Session identifier for logging
        logger: Logger instance
        tool_count: Actual number of tool calls made (from SDK). If provided, this
                   overrides pattern-based detection and is more accurate.
        files_changed: Number of files modified this session (T052)
        issues_closed: Number of issues closed this session (T052)

    Returns:
        dict with keys:
            - is_healthy: bool
            - warnings: list of warning messages
            - tool_calls_count: int
            - response_length: int
            - has_content: bool
            - productivity_score: float (T055)
            - files_changed: int
            - issues_closed: int
    """
    health_status = {
        'is_healthy': True,
        'warnings': [],
        'tool_calls_count': 0,
        'response_length': len(str(response)) if response else 0,
        'has_content': bool(response and str(response).strip()),
        'productivity_score': 0.0,  # T055: Add productivity_score
        'files_changed': files_changed,
        'issues_closed': issues_closed,
    }

    response_str = str(response) if response else ""

    # Check 1: Empty or near-empty response
    if not response_str or len(response_str.strip()) < 10:
        health_status['is_healthy'] = False
        health_status['warnings'].append("Response is empty or too short (< 10 chars)")
        if logger:
            logger.warning(f"Health check failed: Empty or near-empty response")
        return health_status

    # Check 2: Count tool usage evidence
    # If actual tool count provided from SDK, use it directly (more accurate)
    if tool_count is not None:
        health_status['tool_calls_count'] = tool_count
        if logger:
            logger.debug(f"Health check: Using actual tool count from SDK: {tool_count}")
    else:
        # Fall back to pattern matching (less accurate, for legacy support)
        tool_patterns = [
            r'<invoke name="(\w+)"',  # XML-style tool invocations
            r'Tool:\s*(\w+)',  # Tool: Read, Tool: Write, etc.
            r'Using tool:\s*(\w+)',  # Using tool: Read
            r'Calling (\w+) tool',  # Calling Read tool
            r'Reading file:',  # Common tool operation indicators
            r'Writing to file:',
            r'Editing file:',
            r'Searching for:',
            r'Running command:',
            r'Executing:',
            r'<invoke',  # ANTML tool invocations
            r'function_call',  # Function call indicators
            r'<function_calls>',  # Function calls wrapper
        ]

        tool_matches = []
        for pattern in tool_patterns:
            matches = re.findall(pattern, response_str, re.IGNORECASE)
            tool_matches.extend(matches)

        health_status['tool_calls_count'] = len(tool_matches)
        if logger:
            logger.debug(f"Health check: Found {len(tool_matches)} tool usage indicators via pattern matching")

    # Check 3: No tool usage detected
    if health_status['tool_calls_count'] == 0:
        health_status['is_healthy'] = False
        health_status['warnings'].append("No tool usage detected - agent may not be doing any work")
        if logger:
            logger.warning("Health check failed: No tool usage detected")

    # T053-T054: Calculate and check productivity score
    productivity_score = calculate_productivity_score(
        tool_count=health_status['tool_calls_count'],
        files_changed=files_changed,
        issues_closed=issues_closed
    )
    health_status['productivity_score'] = productivity_score

    # T054: Productivity warning check (high tool count but low productivity)
    PRODUCTIVITY_TOOL_THRESHOLD = 30  # Tool count threshold
    PRODUCTIVITY_SCORE_THRESHOLD = 0.1  # Minimum acceptable score

    if health_status['tool_calls_count'] >= PRODUCTIVITY_TOOL_THRESHOLD and productivity_score < PRODUCTIVITY_SCORE_THRESHOLD:
        health_status['warnings'].append(
            f"Low productivity: {health_status['tool_calls_count']} tool calls but score={productivity_score:.3f} "
            f"(files_changed={files_changed}, issues_closed={issues_closed})"
        )
        # T057: Log productivity warning
        if logger:
            logger.warning(
                f"Productivity warning: {health_status['tool_calls_count']} tools, "
                f"score={productivity_score:.3f}, files={files_changed}, issues={issues_closed}"
            )

    # Check 4: Very short response with few tool calls
    if health_status['response_length'] < 200 and health_status['tool_calls_count'] < 2:
        health_status['is_healthy'] = False
        health_status['warnings'].append(
            f"Response too short ({health_status['response_length']} chars) with minimal tool usage ({health_status['tool_calls_count']} calls)"
        )
        if logger:
            logger.warning(f"Health check failed: Short response ({health_status['response_length']} chars) with {health_status['tool_calls_count']} tool calls")

    # Check 5: Look for error indicators
    error_patterns = [
        r'(?i)error:?\s*unable to',
        r'(?i)failed to',
        r'(?i)could not',
        r'(?i)cannot find',
        r'(?i)permission denied',
        r'(?i)access denied',
    ]

    for pattern in error_patterns:
        if re.search(pattern, response_str):
            health_status['warnings'].append(f"Potential error detected in response: {pattern}")
            if logger:
                logger.warning(f"Health check: Potential error detected matching pattern: {pattern}")
            break

    # Check 6: Look for common "giving up" phrases
    stall_patterns = [
        r'(?i)i cannot proceed',
        r'(?i)unable to continue',
        r'(?i)nothing (more )?to do',
        r'(?i)no changes (needed|required)',
        r'(?i)all tasks (are )?complete',
    ]

    for pattern in stall_patterns:
        if re.search(pattern, response_str):
            health_status['warnings'].append(f"Agent may have stalled: matched pattern {pattern}")
            if logger:
                logger.warning(f"Health check: Stall indicator detected matching pattern: {pattern}")
            break

    # Check 7: Look for rate limit indicators
    rate_limit_patterns = [
        r'(?i)rate.?limit',
        r'(?i)\b429\b',
        r'(?i)too many requests',
        r'(?i)quota.*exceeded',
        r'(?i)exceeded.*quota',
        r'(?i)usage.?limit',
        r'(?i)capacity',
        r'(?i)overloaded',
        r'(?i)approaching.*limit',
        r'(?i)limit.*reached',
    ]

    health_status['rate_limit_detected'] = False
    for pattern in rate_limit_patterns:
        if re.search(pattern, response_str):
            health_status['rate_limit_detected'] = True
            health_status['warnings'].append(f"Rate limit detected in response: {pattern}")
            if logger:
                logger.warning(f"Health check: Rate limit indicator detected matching pattern: {pattern}")

            # Trigger token rotation
            try:
                rotator = get_rotator()
                old_token = rotator.current_name
                rotator.rotate(reason="rate limit detected in response text")
                if logger:
                    logger.warning(f"Token rotated: {old_token} -> {rotator.current_name}")
                print(f"\n⚠️  Rate limit detected in response! Switched token: {old_token} -> {rotator.current_name}")
            except Exception as e:
                if logger:
                    logger.error(f"Failed to rotate token after rate limit detection: {e}")
            break

    if logger and health_status['is_healthy']:
        logger.info(f"Health check PASSED: {health_status['tool_calls_count']} tool calls, {health_status['response_length']} chars")

    return health_status


def log_health_warnings(health_status: dict, session_id: str, logger: logging.Logger):
    """Log health warnings to console and logger (T057)."""
    if not health_status['is_healthy'] or health_status['warnings']:
        warning_msg = f"\n⚠️  SESSION HEALTH WARNING ({session_id}):"
        print(warning_msg)
        logger.warning("="*80)
        logger.warning(f"SESSION HEALTH WARNING: {session_id}")
        logger.warning("="*80)

        # Include productivity metrics (T057)
        details = [
            f"   Response length: {health_status['response_length']} chars",
            f"   Tool calls detected: {health_status['tool_calls_count']}",
            f"   Has content: {health_status['has_content']}",
            f"   Productivity score: {health_status.get('productivity_score', 0.0):.3f}",
            f"   Files changed: {health_status.get('files_changed', 0)}",
            f"   Issues closed: {health_status.get('issues_closed', 0)}",
        ]

        for detail in details:
            print(detail)
            logger.warning(detail)

        for warning in health_status['warnings']:
            msg = f"   - {warning}"
            print(msg)
            logger.warning(msg)

        logger.warning("="*80)
        print()
async def run_agent_session(client: ClaudeSDKClient, prompt: str, project_dir: Path, logger: logging.Logger, session_id: str):
    """Run a single agent session with the client.

    CRITICAL FIX: Properly uses client.receive_response() to capture Claude's actual responses.
    The SDK's client.query() returns None - responses must be retrieved via receive_response().
    """
    logger.info("="*80)
    logger.info(f"STARTING AGENT SESSION: {session_id}")
    logger.info("="*80)

    print("Sending prompt to agent...\n")

    # Log prompt (first 500 chars)
    prompt_preview = prompt[:500] + "..." if len(prompt) > 500 else prompt
    logger.debug(f"PROMPT SENT ({len(prompt)} chars):\n{prompt_preview}")

    # Change to project directory for command execution
    original_dir = Path.cwd()
    os.chdir(project_dir)

    session_start_time = time.time()

    try:
        # CRITICAL FIX: client.query() returns None, not the response!
        # We must use receive_response() to actually get Claude's output
        logger.debug("Calling client.query() to send prompt...")
        await client.query(prompt, session_id=session_id)

        logger.debug("Receiving response from Claude via receive_response()...")

        # Collect all messages from Claude
        messages = []
        result_message = None
        tool_count = 0
        response_text_parts = []

        # CRITICAL: Actually receive the response!
        async for msg in client.receive_response():
            messages.append(msg)
            msg_type = type(msg).__name__
            logger.debug(f"Received message type: {msg_type}")

            # Process different message types
            if hasattr(msg, 'content') and hasattr(msg, '__class__'):
                # AssistantMessage with content blocks
                if hasattr(msg.content, '__iter__'):
                    for block in msg.content:
                        block_type = type(block).__name__

                        if hasattr(block, 'text'):
                            # TextBlock or ThinkingBlock
                            text_preview = block.text[:200] + "..." if len(block.text) > 200 else block.text
                            logger.info(f"Claude ({block_type}): {text_preview}")
                            response_text_parts.append(block.text)

                        elif hasattr(block, 'name'):
                            # ToolUseBlock
                            tool_count += 1
                            logger.info(f"Tool #{tool_count}: {block.name}")
                            logger.debug(f"Tool input: {getattr(block, 'input', 'N/A')}")

                        elif hasattr(block, 'tool_use_id'):
                            # ToolResultBlock
                            logger.debug(f"Tool result for: {block.tool_use_id}")

            # Check for ResultMessage (final message with cost/usage data)
            if msg_type == 'ResultMessage' or (hasattr(msg, 'total_cost_usd') and hasattr(msg, 'num_turns')):
                result_message = msg
                cost = getattr(msg, 'total_cost_usd', 0)
                turns = getattr(msg, 'num_turns', 0)
                logger.info(f"Session complete - Cost: ${cost:.4f}, Turns: {turns}")

        session_duration = time.time() - session_start_time

        # Combine all text responses
        full_response_text = "\n".join(response_text_parts) if response_text_parts else ""

        # Log comprehensive response info
        logger.info(f"AGENT RESPONSE RECEIVED (duration: {session_duration:.2f}s)")
        logger.info(f"Messages received: {len(messages)}")
        logger.info(f"Tool calls detected: {tool_count}")
        logger.info(f"Response text length: {len(full_response_text)} chars")

        logger.debug("="*80)
        logger.debug("FULL AGENT RESPONSE TEXT:")
        logger.debug(full_response_text if full_response_text else "(No text response)")
        logger.debug("="*80)
        logger.debug(f"All messages ({len(messages)} total):")
        for i, msg in enumerate(messages):
            logger.debug(f"  Message {i+1}: {type(msg).__name__}")
        logger.debug("="*80)

        logger.info(f"SESSION TIMING: {session_duration:.2f} seconds")

        # Perform session health check on the collected response
        logger.info("Performing session health check...")
        # Pass actual tool count from SDK for accurate detection
        health_status = analyze_session_health(full_response_text, session_id, logger, tool_count=tool_count)

        # Log any health warnings
        log_health_warnings(health_status, session_id, logger)

        print("\n✅ Agent session complete")

        # Return the full response data
        response_data = {
            'messages': messages,
            'result': result_message,
            'text': full_response_text,
            'tool_count': tool_count,
            'duration': session_duration
        }

        return "success", response_data, health_status

    except Exception as e:
        session_duration = time.time() - session_start_time
        error_str = str(e).lower()

        logger.error("="*80)
        logger.error(f"ERROR DURING SESSION (duration: {session_duration:.2f}s)")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("Stack trace:")
        logger.error(traceback.format_exc())
        logger.error("="*80)

        # Check for rate limit errors and rotate token if needed
        rate_limit_indicators = [
            "rate limit", "rate_limit", "429", "too many requests",
            "quota exceeded", "usage limit", "overloaded", "capacity"
        ]
        is_rate_limit = any(indicator in error_str for indicator in rate_limit_indicators)

        if is_rate_limit:
            try:
                rotator = get_rotator()
                old_token = rotator.current_name
                rotator.rotate(reason="rate limit error in session")
                logger.warning(f"Rate limit detected! Rotated token: {old_token} -> {rotator.current_name}")
                print(f"\n⚠️  Rate limit hit! Switched to: {rotator.current_name}")
            except Exception as rotate_error:
                logger.error(f"Failed to rotate token: {rotate_error}")

        print(f"\n❌ Error during session: {e}")

        # Create unhealthy status for error cases
        error_health_status = {
            'is_healthy': False,
            'warnings': [f"Session exception: {type(e).__name__}: {str(e)}"],
            'tool_calls_count': 0,
            'response_length': 0,
            'has_content': False,
            'rate_limit_detected': is_rate_limit
        }

        return "error", str(e), error_health_status

    finally:
        os.chdir(original_dir)
        logger.debug(f"Session {session_id} completed, changed back to: {original_dir}")


async def ensure_git_and_github_repo(project_dir: Path, logger: logging.Logger):
    """
    Ensure git repository is initialized and GitHub repo exists.

    - Checks if git is initialized in project directory
    - If not, creates a GitHub repository in Providence IT organization
    - Initializes git locally and sets up remote
    - Handles GitHub authentication and permissions
    """
    logger.info("Checking git repository status...")

    # Check if git is initialized
    git_dir = project_dir / ".git"
    if git_dir.exists():
        logger.info("Git repository already initialized")

        # Check if remote is set up
        try:
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                cwd=project_dir,
                capture_output=True,
                text=True,
                check=True
            )
            remote_url = result.stdout.strip()
            logger.info(f"Remote origin configured: {remote_url}")

            # Extract and save repo info from remote URL
            # URL format: https://github.com/org/repo.git or git@github.com:org/repo.git
            repo_match = re.search(r'github\.com[:/]([^/]+/[^/\.]+)', remote_url)
            if repo_match:
                repo_name = repo_match.group(1)
                save_repo_info(project_dir, repo_name)
                logger.info(f"Saved repo info: {repo_name}")

            return
        except subprocess.CalledProcessError:
            logger.warning("No remote origin configured, will try to set one up")
    else:
        logger.info("Git repository not initialized")

    # Git not initialized - need to create GitHub repo and initialize
    print("\n" + "="*70)
    print("  GIT REPOSITORY INITIALIZATION")
    print("="*70)
    print(f"  No git repository found in {project_dir.name}")
    print(f"  Creating new GitHub repository in Providence IT organization...")
    print("="*70 + "\n")

    # Read app_spec.txt to intelligently extract project information
    spec_file = project_dir / "app_spec.txt"
    project_name = project_dir.name
    project_description = "Software project managed by autonomous agent"

    if spec_file.exists():
        try:
            spec_content = spec_file.read_text(encoding='utf-8')
            lines = [line.strip() for line in spec_content.split('\n') if line.strip()]

            # Extract title (first H1 or title-like line)
            title_parts = []
            brands = []
            project_type = None

            for i, line in enumerate(lines[:20]):  # Look at first 20 lines
                # Remove markdown formatting
                clean_line = line.lstrip('#').strip()

                # First major heading is likely the project name
                if i < 5 and (line.startswith('#') or line.isupper()):
                    if clean_line and len(clean_line) > 3:
                        title_parts.append(clean_line)

                # Look for brand names (common patterns)
                if any(indicator in clean_line.lower() for indicator in ['.nl', '.com', 'brand']):
                    # Extract domain-like names
                    domain_matches = re.findall(r'\b([A-Za-z]+(?:\.nl|\.com|\.io))\b', clean_line)
                    brands.extend(domain_matches)

                # Detect project type
                lower = clean_line.lower()
                if 'dashboard' in lower or 'analytics' in lower:
                    project_type = 'dashboard'
                elif 'automation' in lower or 'workflow' in lower:
                    project_type = 'automation'
                elif 'api' in lower:
                    project_type = 'api'
                elif 'website' in lower or 'landing' in lower:
                    project_type = 'website'
                elif 'app' in lower or 'application' in lower:
                    project_type = 'app'

            # Build descriptive project name
            if title_parts:
                # Use the first title, but limit length
                main_title = title_parts[0][:60]
                project_name = main_title

                # If we found brands, potentially shorten and add context
                if brands:
                    # Remove duplicates and limit
                    unique_brands = list(dict.fromkeys(brands))[:2]
                    brands_str = '-'.join([b.replace('.nl', '').replace('.com', '') for b in unique_brands])

                    # If title is very long, create concise name with brands
                    if len(main_title) > 40:
                        if project_type:
                            project_name = f"{brands_str}-{project_type}"
                        else:
                            # Extract key words from title
                            key_words = [w for w in main_title.lower().split() if len(w) > 4 and w not in ['powered', 'platform', 'system']][:3]
                            project_name = f"{brands_str}-{'-'.join(key_words)}"
                    else:
                        project_name = main_title

                # Extract description from project overview or vision
                for i, line in enumerate(lines):
                    if any(keyword in line.lower() for keyword in ['overview', 'vision', 'description', 'about']):
                        # Get next non-empty line as description
                        for j in range(i+1, min(i+5, len(lines))):
                            if lines[j] and not lines[j].startswith('#') and len(lines[j]) > 20:
                                project_description = lines[j][:100]
                                break
                        break

            logger.debug(f"Extracted project name: {project_name}")
            logger.debug(f"Extracted brands: {brands}")
            logger.debug(f"Detected project type: {project_type}")
            logger.debug(f"Description: {project_description}")

        except Exception as e:
            logger.warning(f"Failed to parse app_spec.txt intelligently: {e}")
            # Fallback to simple extraction
            try:
                spec_content = spec_file.read_text(encoding='utf-8')
                lines = spec_content.split('\n')
                for line in lines[:10]:
                    if line.strip() and not line.startswith('#'):
                        project_name = line.strip()[:50]
                        break
            except:
                pass

    # Sanitize project name for GitHub (lowercase, hyphens, alphanumeric)
    repo_name = re.sub(r'[^a-zA-Z0-9\-_]', '-', project_name.lower())
    repo_name = re.sub(r'-+', '-', repo_name)  # Remove duplicate hyphens
    repo_name = repo_name.strip('-')  # Remove leading/trailing hyphens

    # Ensure reasonable length (GitHub limit is 100 chars)
    if len(repo_name) > 80:
        repo_name = repo_name[:80].rstrip('-')

    logger.info(f"Final repository name: {repo_name}")
    print(f"   Repository name: {repo_name}")

    # Check GitHub authentication
    try:
        result = subprocess.run(
            ['gh', 'auth', 'status'],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print("⚠️  GitHub CLI not authenticated. Please run: gh auth login")
            logger.error("GitHub CLI not authenticated")
            raise Exception("GitHub authentication required. Run: gh auth login")
        logger.info("GitHub CLI authenticated")
    except FileNotFoundError:
        print("❌ GitHub CLI (gh) not found. Please install: https://cli.github.com/")
        logger.error("GitHub CLI not found")
        raise Exception("GitHub CLI not installed")

    # Create GitHub repository in Providence IT organization
    org_name = "ProvidenceIT"
    print(f"📦 Creating repository: {org_name}/{repo_name}")
    logger.info(f"Creating GitHub repository: {org_name}/{repo_name}")

    try:
        # Create private repository in organization
        result = subprocess.run(
            [
                'gh', 'repo', 'create',
                f'{org_name}/{repo_name}',
                '--private',
                '--description', project_description,
                '--clone=false'  # Don't clone, we'll init locally
            ],
            capture_output=True,
            text=True,
            cwd=project_dir
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip()
            if "already exists" in error_msg.lower():
                print(f"✓ Repository {org_name}/{repo_name} already exists")
                logger.info(f"Repository already exists: {org_name}/{repo_name}")
            else:
                print(f"❌ Failed to create repository: {error_msg}")
                logger.error(f"Failed to create repository: {error_msg}")
                raise Exception(f"Failed to create GitHub repository: {error_msg}")
        else:
            print(f"✅ Created repository: {org_name}/{repo_name}")
            logger.info(f"Successfully created repository: {org_name}/{repo_name}")

        # Save repo info for use in prompts (prevents wrong repo issues)
        full_repo_name = f"{org_name}/{repo_name}"
        save_repo_info(project_dir, full_repo_name, org_name)
        logger.info(f"Saved repo info: {full_repo_name}")

    except Exception as e:
        print(f"❌ Error creating GitHub repository: {e}")
        logger.error(f"Error creating GitHub repository: {e}")
        raise

    # Initialize git locally
    print("\n📝 Initializing local git repository...")
    logger.info("Initializing local git repository")

    try:
        # Initialize git
        subprocess.run(
            ['git', 'init'],
            cwd=project_dir,
            check=True,
            capture_output=True
        )
        logger.info("Git initialized")

        # Configure git user
        subprocess.run(
            ['git', 'config', 'user.name', 'Autonomous Agent'],
            cwd=project_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ['git', 'config', 'user.email', 'agent@providence.it'],
            cwd=project_dir,
            check=True,
            capture_output=True
        )
        logger.info("Git user configured")

        # Set up remote
        remote_url = f"https://github.com/{org_name}/{repo_name}.git"
        subprocess.run(
            ['git', 'remote', 'add', 'origin', remote_url],
            cwd=project_dir,
            check=True,
            capture_output=True
        )
        logger.info(f"Remote origin added: {remote_url}")

        # Create initial commit with .gitignore
        gitignore_content = """# Dependencies
node_modules/
.pnp
.pnp.js

# Next.js
.next/
out/
build/
dist/

# Large binary files (CRITICAL - prevent GitHub push failures)
*.node
*.exe
*.dll
*.so
*.dylib

# Python
__pycache__/
*.py[cod]
*$py.class
.Python
env/
venv/
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo
*.sublime-*

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
Thumbs.db
ehthumbs.db

# Logs
logs/
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Testing
coverage/
.nyc_output/

# Misc
*.pem
.cache/
.turbo/

# Project specific
.initialized
.github_project.json
.github_cache.json
"""
        gitignore_path = project_dir / ".gitignore"
        gitignore_path.write_text(gitignore_content, encoding='utf-8')
        logger.info("Created .gitignore")

        subprocess.run(
            ['git', 'add', '.gitignore', 'app_spec.txt'],
            cwd=project_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ['git', 'commit', '-m', 'Initial commit: Project setup'],
            cwd=project_dir,
            check=True,
            capture_output=True
        )
        logger.info("Initial commit created")

        # Set default branch to main
        subprocess.run(
            ['git', 'branch', '-M', 'main'],
            cwd=project_dir,
            check=True,
            capture_output=True
        )

        # Push to remote
        print("📤 Pushing to GitHub...")
        subprocess.run(
            ['git', 'push', '-u', 'origin', 'main'],
            cwd=project_dir,
            check=True,
            capture_output=True
        )
        logger.info("Pushed to remote")

        print(f"✅ Git repository initialized and pushed to {org_name}/{repo_name}")
        print(f"   URL: https://github.com/{org_name}/{repo_name}\n")

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        print(f"❌ Error initializing git: {error_msg}")
        logger.error(f"Error initializing git: {error_msg}")
        raise Exception(f"Failed to initialize git repository: {error_msg}")


async def main(project_dir: Path, model: str, max_iterations: int = None, project_name: str = None, provider_name: str = None):
    """Main autonomous agent loop.

    Args:
        project_dir: Project directory path
        model: Model to use (for Claude provider)
        max_iterations: Maximum iterations to run (None for unlimited)
        project_name: Project spec name
        provider_name: Specific provider to use (None for priority-based selection)
    """
    run_start_time = time.time()

    # Ensure absolute path
    project_dir = project_dir.resolve()
    project_dir.mkdir(parents=True, exist_ok=True)

    # Initialize logger FIRST
    logger = setup_session_logger(project_dir)
    logger.info(f"Starting autonomous agent run")
    logger.info(f"Project directory: {project_dir}")
    logger.info(f"Project name: {project_name if project_name else project_dir.name}")
    logger.info(f"Model: {model}")
    logger.info(f"Max iterations: {max_iterations if max_iterations else 'unlimited'}")
    logger.info(f"Provider: {provider_name if provider_name else 'auto (priority-based)'}")

    # Initialize provider pool (002-multi-sdk)
    provider_pool = None
    selected_provider_name = "claude"  # Default for backward compatibility

    if MULTI_PROVIDER_AVAILABLE:
        try:
            provider_pool = create_default_pool(project_dir)
            logger.info(f"Provider pool initialized with {provider_pool.provider_count} provider(s)")

            # Validate providers
            validation_results = await provider_pool.validate_providers()
            for name, valid in validation_results.items():
                status = "OK" if valid else "FAILED"
                logger.info(f"  Provider {name}: {status}")
                if not valid and name in provider_pool.validation_errors:
                    logger.warning(f"    Error: {provider_pool.validation_errors[name]}")

            # Get selected provider
            try:
                provider = provider_pool.get_provider(provider_name)
                selected_provider_name = provider.name
                logger.info(f"Selected provider: {selected_provider_name}")
            except NoProvidersAvailableError as e:
                logger.warning(f"No providers available: {e}. Falling back to Claude SDK directly.")
                provider_pool = None

        except Exception as e:
            logger.warning(f"Failed to initialize provider pool: {e}. Using Claude SDK directly.")
            provider_pool = None
    else:
        logger.info("Multi-provider support not available. Using Claude SDK directly.")

    # Copy app_spec.txt to project directory
    logger.debug("Copying app_spec.txt to project directory")
    copy_spec_to_project(project_dir, project_name=project_name)

    # Check and initialize git repository if needed
    logger.debug("Checking git repository status")
    await ensure_git_and_github_repo(project_dir, logger)

    # Set project context for prompt injection (CRITICAL for correct repo targeting)
    repo_info = get_repo_info(project_dir)
    if repo_info.get('repo'):
        set_project_context(
            project_dir=project_dir,
            repo=repo_info['repo'],
            repo_url=repo_info.get('repo_url')
        )
        logger.info(f"Project context set: repo={repo_info['repo']}")
    else:
        set_project_context(project_dir=project_dir)
        logger.warning("No repo info found - gh commands may target wrong repo!")

    # Initialize GitHub integration
    logger.debug("Initializing GitHub cache and integration")
    cache = GitHubCache(project_dir)
    integration = create_enhanced_integration(project_dir, cache)
    git_mgr = create_git_manager(project_dir, auto_push=True)

    # Check if first run (use separate marker file, not the data file)
    init_marker = project_dir / ".initialized"
    is_first_run = not init_marker.exists()
    logger.info(f"First run: {is_first_run}")

    # Print banner
    print("\n" + "="*70)
    print("  AUTONOMOUS GITHUB CODING AGENT (FIXED)")
    print("="*70)
    print(f"  Project: {project_dir.name}")
    print(f"  Location: {project_dir}")
    print(f"  Model: {model}")
    print(f"  Provider: {selected_provider_name}")
    print(f"  Mode: {'Initializer (first run)' if is_first_run else 'Coding agent'}")
    print("="*70 + "\n")

    # Show progress if not first run
    if not is_first_run:
        print(integration.generate_progress_report())
        print()

    # KEY FIX: Change to project directory BEFORE creating client
    print(f"Changing to project directory: {project_dir}\n")
    logger.debug(f"Changing working directory to: {project_dir}")
    os.chdir(project_dir)

    # CRITICAL FIX: Create client options ONCE, but create NEW client each iteration
    # This prevents context accumulation that causes "API Error: 400 tool use concurrency"
    client_options = ClaudeCodeOptions(
        model=model,
        system_prompt="You are an expert full-stack developer. Use GitHub Issues and GitHub Projects for project management via gh CLI. Build production-quality code with tests.",
        allowed_tools=["Read", "Write", "Edit", "Glob", "Grep", "Bash"],
        max_turns=50  # Sufficient for: orientation (15-20) + implementation (20-30) + verification (5-10)
    )

    logger.debug(f"Client options:")
    logger.debug(f"  Model: {model}")
    logger.debug(f"  System prompt: {client_options.system_prompt}")
    logger.debug(f"  Allowed tools: {client_options.allowed_tools}")
    logger.debug(f"  Max turns: {client_options.max_turns}")

    iteration = 0
    # T028: Graceful termination tracking for empty backlog
    consecutive_no_issues = 0

    while True:
            iteration += 1
            iteration_start_time = time.time()

            if max_iterations and iteration > max_iterations:
                logger.info(f"Reached maximum iterations ({max_iterations})")
                print(f"\n✅ Reached maximum iterations ({max_iterations})")
                break

            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{iteration:03d}"

            print(f"\n{'='*70}")
            print(f"  SESSION {iteration}: {session_id}")
            print(f"{'='*70}\n")

            logger.info("="*80)
            logger.info(f"ITERATION {iteration} - SESSION ID: {session_id}")
            logger.info("="*80)

            try:
                # Choose prompt based on mode
                if is_first_run:
                    prompt = get_initializer_prompt()
                    mode_name = "Initializer"
                else:
                    prompt = get_coding_prompt()
                    mode_name = "Coding"

                logger.info(f"Mode: {mode_name}")
                logger.debug(f"Full prompt length: {len(prompt)} chars")
                print(f"📝 Running {mode_name} agent\n")

                # CRITICAL FIX: Create FRESH client for each iteration
                # This prevents context accumulation that causes API 400 errors
                print("Creating fresh Claude Code client for this session...")
                logger.info(f"Creating new client for iteration {iteration}")

                # Sync token to environment before creating client
                try:
                    rotator = get_rotator()
                    rotator.sync_env()
                    token_suffix = rotator.current.value[-5:] if len(rotator.current.value) >= 5 else rotator.current.value
                    logger.info(f"Using token: {rotator.current_name} ({rotator.current.auth_type.value}) [...{token_suffix}]")
                except Exception as e:
                    logger.warning(f"Token sync failed: {e}")

                client_creation_start = time.time()
                client = ClaudeSDKClient(options=client_options)
                client_creation_duration = time.time() - client_creation_start
                logger.info(f"Client created in {client_creation_duration:.2f}s")

                # Run session with fresh client (context is clean)
                async with client:
                    logger.info("Connected to Claude Code CLI")
                    status, response, health_status = await run_agent_session(client, prompt, project_dir, logger, session_id)

                # Client is now closed, context is cleared

                # Check if rate limit was detected and retry with new token
                retry_attempted = False
                if health_status.get('rate_limit_detected', False):
                    logger.warning("Rate limit detected in session. Token already rotated. Retrying with new token...")
                    print("\n⚠️  Rate limit hit! Retrying with new token...\n")
                    retry_attempted = True

                    # Wait a bit to let rate limit cooldown
                    await asyncio.sleep(3)

                    # Retry with the same prompt but new token (already rotated in health check)
                    retry_session_id = f"{session_id}_ratelimit_retry"

                    # Create fresh client with new token
                    logger.info("Creating fresh client with rotated token for rate limit retry")
                    retry_client = ClaudeSDKClient(options=client_options)
                    async with retry_client:
                        status, response, health_status = await run_agent_session(retry_client, prompt, project_dir, logger, retry_session_id)

                    if health_status.get('rate_limit_detected', False):
                        logger.error("Rate limit hit again after token rotation. All tokens may be exhausted.")
                        print("\n❌ Rate limit hit again. All tokens may be rate limited.\n")
                    else:
                        logger.info("Rate limit retry succeeded with new token")
                        print("\n✅ Retry with new token successful\n")

                # Check if session is unhealthy and retry once if needed
                elif not health_status['is_healthy'] and status != "error":
                    logger.warning("Session appears unhealthy. Attempting one retry...")
                    print("\n⚠️  Session appears to have stalled. Retrying once...\n")
                    retry_attempted = True

                    # Wait a bit before retry
                    await asyncio.sleep(2)

                    # Retry with a modified prompt emphasizing action AND a fresh client
                    retry_prompt = prompt + "\n\nIMPORTANT: Please take concrete action using tools. Read files, write code, run commands, etc. Do not just provide suggestions."
                    retry_session_id = f"{session_id}_retry"

                    # Create another fresh client for the retry
                    logger.info("Creating fresh client for retry attempt")
                    retry_client = ClaudeSDKClient(options=client_options)
                    async with retry_client:
                        status, response, health_status = await run_agent_session(retry_client, retry_prompt, project_dir, logger, retry_session_id)

                    if health_status['is_healthy']:
                        logger.info("Retry succeeded - session now healthy")
                        print("\n✅ Retry successful - session now healthy\n")
                    else:
                        logger.warning("Retry failed - session still unhealthy")
                        print("\n⚠️  Retry failed - session still appears unhealthy\n")

                # Log final health status to session metrics
                session_metrics = {
                    'status': status,
                    'retry_attempted': retry_attempted,
                    'is_healthy': health_status['is_healthy'],
                    'tool_calls_count': health_status['tool_calls_count'],
                    'response_length': health_status['response_length']
                }

                # Commit changes
                print("\n📝 Committing changes...")
                logger.debug("Committing and pushing changes to git")
                commit_success, commit_msg = git_mgr.commit_and_push(
                    issues_completed=[],
                    issues_attempted=[],
                    session_metrics=session_metrics,
                    session_id=session_id
                )

                if commit_success:
                    logger.info(f"Git commit successful: {commit_msg}")
                    print(f"✅ {commit_msg}")
                else:
                    logger.warning(f"Git commit failed or no changes: {commit_msg}")
                    print(f"⚠️  {commit_msg}")

                # Check mandatory session outcomes (skip for initializer sessions)
                if not is_first_run:
                    print("\n📊 Checking session outcomes...")
                    session_start = datetime.fromtimestamp(iteration_start_time)
                    outcomes = check_session_mandatory_outcomes(project_dir, session_start, logger)

                    if outcomes['success']:
                        print(f"✅ SESSION SUCCESS!")
                        print(f"   - Issues closed: {outcomes['issues_closed']}")
                        print(f"   - META updated: {'Yes' if outcomes['meta_updated'] else 'No'}")
                        print(f"   - Git pushed: {'Yes' if outcomes['git_pushed'] else 'No'}")
                        logger.info(f"Session outcomes PASSED: {outcomes}")
                    else:
                        print(f"⚠️  SESSION INCOMPLETE - Missing mandatory outcomes:")
                        for failure in outcomes['failures']:
                            print(f"   - {failure}")
                        logger.warning(f"Session outcomes FAILED: {outcomes}")

                        # Log outcome failures for tracking
                        if 'outcome_failures' not in session_metrics:
                            session_metrics['outcome_failures'] = []
                        session_metrics['outcome_failures'] = outcomes['failures']

                # After first run, switch modes
                if is_first_run:
                    is_first_run = False
                    init_marker.write_text(f"Initialized: {datetime.now().isoformat()}")
                    logger.info("Initialization complete! Switching to coding agent mode.")
                    print("\n✅ Initialization complete! Next session will use coding agent.\n")

                iteration_duration = time.time() - iteration_start_time
                logger.info(f"ITERATION {iteration} COMPLETED in {iteration_duration:.2f}s")

                # T028: Check for graceful termination (empty backlog)
                if not is_first_run:
                    # Check if session found no issues to work on
                    no_issues_detected = False
                    if outcomes and outcomes.get('issues_closed', 0) == 0:
                        # Check if there are any open issues remaining
                        try:
                            result = subprocess.run(
                                ['gh', 'issue', 'list', '--repo', repo_info.get('repo', ''),
                                 '--state', 'open', '--json', 'number,title', '--limit', '5'],
                                capture_output=True, text=True, cwd=project_dir, timeout=30
                            )
                            if result.returncode == 0:
                                open_issues = json.loads(result.stdout)
                                # Filter out META issue
                                non_meta_issues = [i for i in open_issues if '[META]' not in i.get('title', '').upper()]
                                if len(non_meta_issues) == 0:
                                    no_issues_detected = True
                        except Exception:
                            pass

                    if no_issues_detected:
                        consecutive_no_issues += 1
                        logger.info(f"No issues found - consecutive count: {consecutive_no_issues}/{MAX_NO_ISSUES_ROUNDS}")
                        print(f"\n⚠️  No issues to work on ({consecutive_no_issues}/{MAX_NO_ISSUES_ROUNDS} consecutive rounds)")

                        if consecutive_no_issues >= MAX_NO_ISSUES_ROUNDS:
                            print(f"\n{'='*70}")
                            print(f"  ALL ISSUES COMPLETE - Stopping agent")
                            print(f"  ({consecutive_no_issues} consecutive rounds with no issues)")
                            print(f"{'='*70}\n")
                            logger.info("Graceful termination: All issues complete")
                            break
                    else:
                        # Reset counter if work was found
                        if consecutive_no_issues > 0:
                            logger.info("Work found - resetting consecutive_no_issues counter")
                        consecutive_no_issues = 0

            except Exception as e:
                iteration_duration = time.time() - iteration_start_time
                logger.error("="*80)
                logger.error(f"EXCEPTION IN ITERATION {iteration} (duration: {iteration_duration:.2f}s)")
                logger.error(f"Error type: {type(e).__name__}")
                logger.error(f"Error message: {str(e)}")
                logger.error("Stack trace:")
                logger.error(traceback.format_exc())
                logger.error("="*80)
                print(f"\n❌ Error: {e}")
                print("Continuing to next iteration...\n")

            # Delay before next iteration
            if max_iterations is None or iteration < max_iterations:
                logger.debug("Waiting 3 seconds before next session...")
                print("\n⏸️  Waiting 3 seconds before next session...\n")
                await asyncio.sleep(3)

    # Final summary (after client closes)
    total_run_duration = time.time() - run_start_time
    logger.info("="*80)
    logger.info("AGENT RUN COMPLETE")
    logger.info(f"Total duration: {total_run_duration:.2f}s ({total_run_duration/60:.2f} minutes)")
    logger.info(f"Total iterations: {iteration}")
    if iteration > 0:
        logger.info(f"Average iteration time: {total_run_duration/iteration:.2f}s")
    logger.info("="*80)

    print("\n" + "="*70)
    print("  AGENT RUN COMPLETE")
    print("="*70)
    print(integration.generate_progress_report())
    print("="*70 + "\n")

    logger.info("Session log file written successfully")
    logger.info("Shutting down logger")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Autonomous GitHub Coding Agent (Fixed)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run agent - initializes project and works on issues
  python autonomous_agent_fixed.py --project-dir ./my_project

  # Run for 5 iterations
  python autonomous_agent_fixed.py --project-dir ./my_project --max-iterations 5

  # Use Opus model (more capable)
  python autonomous_agent_fixed.py --project-dir ./my_project --model claude-opus-4-5-20251101
        """
    )

    parser.add_argument("--project-dir", type=Path, required=True, help="Project directory")
    parser.add_argument("--project-name", type=str, default=None, help="Project spec name (looks in prompts/{project_name}/app_spec.txt)")
    parser.add_argument("--max-iterations", type=int, default=None, help="Max iterations (default: unlimited)")
    parser.add_argument("--model", type=str, default="claude-opus-4-5-20251101", help="Claude model")
    parser.add_argument("--provider", type=str, default=None,
                       help="AI provider to use (claude, gemini, copilot, codex). Defaults to priority-based selection from provider_config.json")

    args = parser.parse_args()

    # Initialize token rotator (supports multiple tokens for rate limit handling)
    try:
        rotator = TokenRotator.from_env(env_file=Path.cwd() / ".env")
        rotator.sync_env()
        set_rotator(rotator)
        print(f"✓ Token rotator initialized with {len(rotator.tokens)} token(s)")
        print(f"  Current: {rotator.current_name} ({rotator.current.auth_type.value})")
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("\nSet one of:")
        print("  - CLAUDE_CODE_OAUTH_TOKEN (for Claude Max subscription)")
        print("  - ANTHROPIC_API_KEY (for API credits)")
        print("\nSee .env.example for backup token naming conventions")
        sys.exit(1)

    # Validate gh CLI
    try:
        result = subprocess.run(["gh", "auth", "status"], capture_output=True, shell=(sys.platform=='win32'))
        if result.returncode != 0:
            print("❌ Error: GitHub CLI not authenticated")
            print("Run: gh auth login")
            sys.exit(1)
        print("✓ GitHub CLI authenticated\n")
    except:
        print("❌ Error: GitHub CLI not found")
        sys.exit(1)

    # Setup project directory
    project_dir = args.project_dir.resolve()
    if "generations" not in str(project_dir):
        project_dir = Path.cwd() / "generations" / project_dir.name

    project_dir.mkdir(parents=True, exist_ok=True)

    # Run agent
    asyncio.run(main(project_dir, args.model, args.max_iterations, args.project_name, args.provider))
