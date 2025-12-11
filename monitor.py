#!/usr/bin/env python3
"""
Progress Monitoring Dashboard
==============================

Real-time monitoring and visualization of agent progress.

Features:
- Live progress tracking from GitHub
- Session history and metrics
- API usage monitoring
- Error tracking
- Health status visualization

Usage:
    python monitor.py ./my_project
    python monitor.py ./my_project --watch  # Auto-refresh every 30s
"""

import argparse
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import sys


class ProgressMonitor:
    """Monitor and display agent progress."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.project_file = project_dir / ".github_project.json"
        self.cache_file = project_dir / ".github_cache.json"
        self.log_dir = project_dir / "logs"

    def load_project_data(self) -> Optional[Dict]:
        """Load project metadata."""
        if not self.project_file.exists():
            return None

        with open(self.project_file, 'r') as f:
            return json.load(f)

    def load_cache_data(self) -> Optional[Dict]:
        """Load cache data."""
        if not self.cache_file.exists():
            return None

        with open(self.cache_file, 'r') as f:
            return json.load(f)

    def count_log_lines(self) -> Dict[str, int]:
        """Count lines in log files."""
        counts = {}

        if not self.log_dir.exists():
            return counts

        # Count daily log
        daily_log = self.log_dir / "agent_daily.log"
        if daily_log.exists():
            with open(daily_log, 'r') as f:
                counts['daily'] = sum(1 for _ in f)

        # Count error log
        error_log = self.log_dir / "errors.log"
        if error_log.exists():
            with open(error_log, 'r') as f:
                counts['errors'] = sum(1 for _ in f)

        # Count session logs
        session_logs = list(self.log_dir.glob("session_*.jsonl"))
        counts['sessions'] = len(session_logs)

        # Count total session log lines
        total_session_lines = 0
        for log_file in session_logs:
            with open(log_file, 'r') as f:
                total_session_lines += sum(1 for _ in f)
        counts['session_lines'] = total_session_lines

        return counts

    def parse_recent_session_logs(self, limit: int = 5) -> List[Dict]:
        """Parse recent session logs."""
        if not self.log_dir.exists():
            return []

        session_logs = sorted(
            self.log_dir.glob("session_*.jsonl"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        recent_sessions = []
        for log_file in session_logs[:limit]:
            session_data = {
                'file': log_file.name,
                'entries': 0,
                'github_calls': 0,
                'cached_calls': 0,
                'errors': 0,
                'tools': set()
            }

            try:
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            session_data['entries'] += 1

                            if entry.get('category') == 'github_api':
                                if entry.get('cached'):
                                    session_data['cached_calls'] += 1
                                else:
                                    session_data['github_calls'] += 1

                            if entry.get('category') == 'tool_use':
                                tool_name = entry.get('tool_name', 'unknown')
                                session_data['tools'].add(tool_name)

                            if entry.get('level') == 'ERROR':
                                session_data['errors'] += 1

                        except json.JSONDecodeError:
                            continue

                session_data['tools'] = list(session_data['tools'])
                recent_sessions.append(session_data)

            except Exception as e:
                print(f"Error reading {log_file}: {e}")

        return recent_sessions

    def generate_dashboard(self) -> str:
        """Generate comprehensive dashboard."""
        project_data = self.load_project_data()
        cache_data = self.load_cache_data()
        log_counts = self.count_log_lines()
        recent_sessions = self.parse_recent_session_logs()

        dashboard = f"""
╔══════════════════════════════════════════════════════════════════════╗
║          GITHUB CODING AGENT - MONITORING DASHBOARD                 ║
╚══════════════════════════════════════════════════════════════════════╝

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""

        # Project Overview
        if project_data:
            dashboard += """
┌─────────────────────────────────────────────────────────────────────┐
│ PROJECT OVERVIEW                                                    │
└─────────────────────────────────────────────────────────────────────┘

"""
            dashboard += f"  Project: {project_data.get('project_name', 'Unknown')}\n"
            dashboard += f"  Total Issues: {project_data.get('total_issues', 0)}\n"
            dashboard += f"  Sessions: {project_data.get('session_count', 0)}\n"
            dashboard += f"  Created: {project_data.get('created_at', 'Unknown')}\n"

            repo = project_data.get('repo', '')
            project_number = project_data.get('project_number', '')
            if repo and project_number:
                dashboard += f"\n  GitHub: https://github.com/{repo}\n"

        # Progress Metrics
        if project_data and 'health_history' in project_data:
            latest_health = project_data['health_history'][-1] if project_data['health_history'] else None

            if latest_health:
                dashboard += """

┌─────────────────────────────────────────────────────────────────────┐
│ PROGRESS METRICS                                                    │
└─────────────────────────────────────────────────────────────────────┘

"""
                health = latest_health.get('health', 'unknown')
                progress = latest_health.get('progress', 0)

                health_emoji = {
                    'on_track': '🟢',
                    'at_risk': '🟡',
                    'off_track': '🔴'
                }.get(health, '⚪')

                dashboard += f"  Status: {health_emoji} {health.replace('_', ' ').title()}\n"
                dashboard += f"  Progress: {progress}%\n"

                # Progress bar
                bar_length = 40
                filled = int(progress / 100 * bar_length)
                bar = '█' * filled + '░' * (bar_length - filled)
                dashboard += f"  [{bar}] {progress}%\n"

        # Velocity Trends
        if project_data and 'velocity_history' in project_data:
            velocity_history = project_data['velocity_history']
            if len(velocity_history) >= 3:
                recent_velocity = [v['velocity'] for v in velocity_history[-5:]]
                avg_velocity = sum(recent_velocity) / len(recent_velocity)

                dashboard += f"\n  Velocity: {avg_velocity:.2f} issues/session (avg last 5)\n"

        # Cache Statistics
        if cache_data:
            dashboard += """

┌─────────────────────────────────────────────────────────────────────┐
│ API USAGE & CACHING                                                 │
└─────────────────────────────────────────────────────────────────────┘

"""
            metadata = cache_data.get('metadata', {})
            api_stats = metadata.get('api_stats', {}) if isinstance(metadata, dict) else {}

            calls_last_hour = api_stats.get('calls_last_hour', 0)
            cached_issues = len(cache_data.get('permanent', {}).get('issues', {}))

            dashboard += f"  API Calls (last hour): {calls_last_hour}/5000\n"

            # API usage bar
            usage_pct = (calls_last_hour / 5000) * 100
            bar_length = 40
            filled = int(usage_pct / 100 * bar_length)

            if usage_pct > 80:
                bar = '█' * filled + '░' * (bar_length - filled)
                color = '🔴'
            elif usage_pct > 60:
                bar = '█' * filled + '░' * (bar_length - filled)
                color = '🟡'
            else:
                bar = '█' * filled + '░' * (bar_length - filled)
                color = '🟢'

            dashboard += f"  {color} [{bar}] {usage_pct:.1f}%\n"
            dashboard += f"\n  Cached Issues: {cached_issues}\n"

        # Log Statistics
        if log_counts:
            dashboard += """

┌─────────────────────────────────────────────────────────────────────┐
│ LOGGING                                                             │
└─────────────────────────────────────────────────────────────────────┘

"""
            dashboard += f"  Sessions Logged: {log_counts.get('sessions', 0)}\n"
            dashboard += f"  Total Log Lines: {log_counts.get('session_lines', 0):,}\n"
            dashboard += f"  Daily Log Lines: {log_counts.get('daily', 0):,}\n"
            dashboard += f"  Error Log Lines: {log_counts.get('errors', 0)}\n"

        # Recent Sessions
        if recent_sessions:
            dashboard += """

┌─────────────────────────────────────────────────────────────────────┐
│ RECENT SESSIONS (Last 5)                                            │
└─────────────────────────────────────────────────────────────────────┘

"""
            for i, session in enumerate(recent_sessions[:5], 1):
                dashboard += f"\n  Session {i}: {session['file']}\n"
                dashboard += f"    Log Entries: {session['entries']}\n"
                dashboard += f"    GitHub Calls: {session['github_calls']} (Cached: {session['cached_calls']})\n"
                dashboard += f"    Errors: {session['errors']}\n"
                dashboard += f"    Tools Used: {len(session['tools'])}\n"

        # Footer
        dashboard += """

╔══════════════════════════════════════════════════════════════════════╗
║ LOG FILES                                                            ║
╚══════════════════════════════════════════════════════════════════════╝

"""
        dashboard += f"  📁 Project: {self.project_dir}\n"
        dashboard += f"  📄 Project Data: {self.project_file}\n"
        dashboard += f"  📦 Cache: {self.cache_file}\n"
        dashboard += f"  📋 Logs: {self.log_dir}/\n"
        dashboard += f"    - agent_daily.log (all sessions)\n"
        dashboard += f"    - errors.log (errors only)\n"
        dashboard += f"    - session_*.jsonl (per-session logs)\n"

        dashboard += "\n" + "="*72 + "\n"

        return dashboard


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Monitor autonomous agent progress",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "project_dir",
        type=Path,
        help="Project directory to monitor"
    )

    parser.add_argument(
        "--watch",
        action="store_true",
        help="Auto-refresh every 30 seconds"
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Refresh interval in seconds (default: 30)"
    )

    args = parser.parse_args()

    project_dir = args.project_dir.resolve()

    if not project_dir.exists():
        print(f"❌ Error: Project directory not found: {project_dir}")
        sys.exit(1)

    monitor = ProgressMonitor(project_dir)

    if args.watch:
        print("🔄 Watch mode enabled (Ctrl+C to exit)")
        try:
            while True:
                # Clear screen (works on Unix and Windows)
                print("\033[2J\033[H", end="")

                dashboard = monitor.generate_dashboard()
                print(dashboard)

                print(f"⏳ Refreshing in {args.interval} seconds...")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n\n✋ Stopped monitoring")
    else:
        # One-time display
        dashboard = monitor.generate_dashboard()
        print(dashboard)


if __name__ == "__main__":
    main()
