#!/usr/bin/env python3
"""
Log Viewer Utility for Autonomous Agent
========================================

Quick utility to view and analyze agent session logs.

Usage:
    python view_logs.py <project_dir>                    # View latest log
    python view_logs.py <project_dir> --all              # List all logs
    python view_logs.py <project_dir> --errors           # Show only errors
    python view_logs.py <project_dir> --timing           # Show timing info
    python view_logs.py <project_dir> --tools            # Show tool usage
    python view_logs.py <project_dir> --sessions         # Show session summaries
"""

import sys
import argparse
from pathlib import Path
import re
from datetime import datetime


def get_log_files(project_dir: Path):
    """Get all log files sorted by timestamp (newest first)."""
    logs_dir = project_dir / "logs"
    if not logs_dir.exists():
        return []

    log_files = sorted(
        logs_dir.glob("session_*.log"),
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )
    return log_files


def list_logs(project_dir: Path):
    """List all available log files."""
    log_files = get_log_files(project_dir)

    if not log_files:
        print(f"No log files found in {project_dir / 'logs'}")
        return

    print(f"\n{'='*80}")
    print(f"Log Files in {project_dir / 'logs'}")
    print(f"{'='*80}\n")

    for i, log_file in enumerate(log_files, 1):
        size_kb = log_file.stat().st_size / 1024
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        print(f"{i:2d}. {log_file.name:<35} {size_kb:>8.1f} KB  {mtime.strftime('%Y-%m-%d %H:%M:%S')}")

    print()


def view_log(project_dir: Path, filter_type: str = None):
    """View the latest log file with optional filtering."""
    log_files = get_log_files(project_dir)

    if not log_files:
        print(f"No log files found in {project_dir / 'logs'}")
        return

    latest_log = log_files[0]
    print(f"\n{'='*80}")
    print(f"Viewing: {latest_log.name}")
    print(f"{'='*80}\n")

    with open(latest_log, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if filter_type == 'errors':
        # Show only error and warning lines with context
        for i, line in enumerate(lines):
            if 'ERROR' in line or 'WARNING' in line or 'EXCEPTION' in line:
                # Print with some context
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                print(''.join(lines[start:end]))
                print('-' * 80)

    elif filter_type == 'timing':
        # Show timing information
        for line in lines:
            if 'duration' in line.lower() or 'timing' in line.lower() or 'COMPLETED' in line:
                print(line.rstrip())

    elif filter_type == 'tools':
        # Show tool usage information
        for line in lines:
            if 'TOOL' in line.upper() or 'tool_calls' in line:
                print(line.rstrip())

    elif filter_type == 'sessions':
        # Show session summaries
        current_session = []
        for line in lines:
            if 'STARTING AGENT SESSION' in line:
                if current_session:
                    print(''.join(current_session))
                    print('-' * 80)
                current_session = [line]
            elif any(marker in line for marker in ['COMPLETED', 'ERROR', 'duration', 'TOOL USAGE']):
                current_session.append(line)

        if current_session:
            print(''.join(current_session))

    else:
        # Show full log
        print(''.join(lines))


def analyze_log(project_dir: Path):
    """Analyze the latest log and show statistics."""
    log_files = get_log_files(project_dir)

    if not log_files:
        print(f"No log files found in {project_dir / 'logs'}")
        return

    latest_log = log_files[0]

    with open(latest_log, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract statistics
    sessions = len(re.findall(r'STARTING AGENT SESSION', content))
    errors = len(re.findall(r'\| ERROR', content))
    warnings = len(re.findall(r'\| WARNING', content))

    # Extract timing
    durations = re.findall(r'duration: ([\d.]+)s', content)
    total_duration = re.search(r'Total duration: ([\d.]+)s', content)

    # Extract tool usage
    tool_counts = re.findall(r'TOOL USAGE COUNT: (\d+)', content)

    print(f"\n{'='*80}")
    print(f"Log Analysis: {latest_log.name}")
    print(f"{'='*80}\n")

    print(f"Sessions:     {sessions}")
    print(f"Errors:       {errors}")
    print(f"Warnings:     {warnings}")

    if durations:
        durations_float = [float(d) for d in durations]
        print(f"\nSession Durations:")
        print(f"  Average:    {sum(durations_float) / len(durations_float):.2f}s")
        print(f"  Min:        {min(durations_float):.2f}s")
        print(f"  Max:        {max(durations_float):.2f}s")

    if total_duration:
        print(f"\nTotal Duration: {total_duration.group(1)}s")

    if tool_counts:
        tool_counts_int = [int(t) for t in tool_counts]
        print(f"\nTool Usage:")
        print(f"  Total:      {sum(tool_counts_int)}")
        print(f"  Average:    {sum(tool_counts_int) / len(tool_counts_int):.1f} per session")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="View and analyze autonomous agent logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # View latest log
  python view_logs.py ./generations/my_project

  # List all logs
  python view_logs.py ./generations/my_project --all

  # Show only errors
  python view_logs.py ./generations/my_project --errors

  # Show timing information
  python view_logs.py ./generations/my_project --timing

  # Show session summaries
  python view_logs.py ./generations/my_project --sessions

  # Analyze log statistics
  python view_logs.py ./generations/my_project --analyze
        """
    )

    parser.add_argument('project_dir', type=Path, help='Project directory')
    parser.add_argument('--all', action='store_true', help='List all log files')
    parser.add_argument('--errors', action='store_true', help='Show only errors')
    parser.add_argument('--timing', action='store_true', help='Show timing information')
    parser.add_argument('--tools', action='store_true', help='Show tool usage')
    parser.add_argument('--sessions', action='store_true', help='Show session summaries')
    parser.add_argument('--analyze', action='store_true', help='Analyze log statistics')

    args = parser.parse_args()

    project_dir = args.project_dir.resolve()

    if not project_dir.exists():
        print(f"Error: Project directory not found: {project_dir}")
        sys.exit(1)

    if args.all:
        list_logs(project_dir)
    elif args.analyze:
        analyze_log(project_dir)
    elif args.errors:
        view_log(project_dir, 'errors')
    elif args.timing:
        view_log(project_dir, 'timing')
    elif args.tools:
        view_log(project_dir, 'tools')
    elif args.sessions:
        view_log(project_dir, 'sessions')
    else:
        view_log(project_dir)


if __name__ == '__main__':
    main()
