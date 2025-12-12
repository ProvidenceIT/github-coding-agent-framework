"""
Git Utilities for Autonomous Agents
====================================

Automatic git operations for agent sessions including:
- Intelligent commit message generation
- Automatic commit on session completion
- Push to remote repository
- Branch management
- Large file detection and cleanup
- Git history sanitization

Features:
- Generates descriptive commit messages from session data
- Handles Linear issue tracking in commits
- Automatic push with error handling
- Configurable auto-commit behavior
- Pre-push validation for large files
- Git history cleanup for failed pushes
"""

import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import os


class GitManager:
    """
    Manages git operations for autonomous agents.

    Features:
    - Smart commit message generation
    - Automatic commits on session completion
    - Push to remote with error handling
    - Linear issue tracking in commits
    """

    def __init__(self, project_dir: Path, auto_push: bool = True):
        self.project_dir = project_dir
        self.auto_push = auto_push

    def check_git_configured(self) -> bool:
        """Check if git is properly configured."""
        try:
            # Check if git user is configured
            result = subprocess.run(
                ['git', 'config', 'user.name'],
                cwd=self.project_dir,
                capture_output=True,
                text=True
            )

            if result.returncode != 0 or not result.stdout.strip():
                return False

            result = subprocess.run(
                ['git', 'config', 'user.email'],
                cwd=self.project_dir,
                capture_output=True,
                text=True
            )

            return result.returncode == 0 and result.stdout.strip()

        except Exception:
            return False

    def configure_git(self, name: str = "Autonomous Agent", email: str = "agent@providence.it"):
        """Configure git if not already configured."""
        try:
            subprocess.run(
                ['git', 'config', 'user.name', name],
                cwd=self.project_dir,
                check=True
            )

            subprocess.run(
                ['git', 'config', 'user.email', email],
                cwd=self.project_dir,
                check=True
            )

            return True
        except Exception as e:
            print(f"⚠️  Failed to configure git: {e}")
            return False

    def has_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True
            )

            return bool(result.stdout.strip())
        except Exception:
            return False

    def find_large_files(self, max_size_mb: float = 100) -> List[Tuple[str, float]]:
        """
        Find files larger than max_size_mb that are staged or tracked.

        Returns:
            List of (filepath, size_in_mb) tuples
        """
        large_files = []
        max_size_bytes = max_size_mb * 1024 * 1024

        try:
            # Check staged files
            result = subprocess.run(
                ['git', 'diff', '--cached', '--name-only'],
                cwd=self.project_dir,
                capture_output=True,
                text=True
            )
            staged_files = result.stdout.strip().split('\n') if result.stdout.strip() else []

            # Check all tracked files
            result = subprocess.run(
                ['git', 'ls-files'],
                cwd=self.project_dir,
                capture_output=True,
                text=True
            )
            tracked_files = result.stdout.strip().split('\n') if result.stdout.strip() else []

            all_files = set(staged_files + tracked_files)

            for filepath in all_files:
                if not filepath:
                    continue
                full_path = self.project_dir / filepath
                if full_path.exists():
                    size = full_path.stat().st_size
                    if size > max_size_bytes:
                        size_mb = size / (1024 * 1024)
                        large_files.append((filepath, size_mb))

            return large_files
        except Exception as e:
            print(f"⚠️  Error checking for large files: {e}")
            return []

    def check_history_for_large_files(self, max_size_mb: float = 100) -> List[str]:
        """
        Check git history for large files that may have been committed.

        Returns:
            List of large file paths found in history
        """
        try:
            # Use git rev-list to find large objects in history
            result = subprocess.run(
                ['git', 'rev-list', '--objects', '--all'],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                return []

            large_files = []
            max_size_bytes = max_size_mb * 1024 * 1024

            # Parse output and check sizes
            for line in result.stdout.split('\n'):
                parts = line.split(' ', 1)
                if len(parts) == 2:
                    obj_hash, filepath = parts
                    # Check if file is in problematic paths
                    if any(pattern in filepath for pattern in ['node_modules/', '.next/', '*.node']):
                        large_files.append(filepath)

            return list(set(large_files))
        except Exception as e:
            print(f"⚠️  Error checking history for large files: {e}")
            return []

    def ensure_gitignore_has_entries(self, entries: List[str]) -> bool:
        """
        Ensure .gitignore has required entries.

        Args:
            entries: List of patterns to ensure are in .gitignore

        Returns:
            True if .gitignore was modified
        """
        gitignore_path = self.project_dir / ".gitignore"

        existing_entries = set()
        if gitignore_path.exists():
            existing_entries = set(
                line.strip() for line in gitignore_path.read_text().split('\n')
                if line.strip() and not line.startswith('#')
            )

        missing = [e for e in entries if e not in existing_entries]

        if missing:
            with open(gitignore_path, 'a') as f:
                f.write('\n# Added by autonomous agent\n')
                for entry in missing:
                    f.write(f'{entry}\n')
            print(f"✅ Added to .gitignore: {', '.join(missing)}")
            return True

        return False

    def remove_from_tracking(self, patterns: List[str]) -> Tuple[bool, str]:
        """
        Remove files matching patterns from git tracking (but keep on disk).

        Args:
            patterns: List of file patterns to remove from tracking

        Returns:
            (success, message)
        """
        try:
            removed_count = 0
            for pattern in patterns:
                result = subprocess.run(
                    ['git', 'rm', '-r', '--cached', pattern],
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    removed_count += 1

            if removed_count > 0:
                return True, f"Removed {removed_count} patterns from tracking"
            return True, "No files to remove"

        except Exception as e:
            return False, f"Failed to remove from tracking: {e}"

    def clean_large_files_from_history(self) -> Tuple[bool, str]:
        """
        Attempt to clean large files from git history using filter-branch.
        This is a nuclear option - use with caution!

        Returns:
            (success, message)
        """
        print("🧹 Attempting to clean large files from git history...")

        # First, ensure .gitignore is updated
        critical_ignores = [
            'node_modules/',
            '.next/',
            '*.node',
            'out/',
            'build/',
            'dist/',
        ]
        self.ensure_gitignore_has_entries(critical_ignores)

        # Remove from tracking
        for pattern in ['node_modules', '.next']:
            subprocess.run(
                ['git', 'rm', '-r', '--cached', '--ignore-unmatch', pattern],
                cwd=self.project_dir,
                capture_output=True
            )

        try:
            # Try using git filter-repo if available (preferred)
            result = subprocess.run(
                ['git', 'filter-repo', '--version'],
                capture_output=True,
                text=True
            )
            has_filter_repo = result.returncode == 0
        except FileNotFoundError:
            has_filter_repo = False

        if has_filter_repo:
            # Use git-filter-repo (modern, faster)
            try:
                subprocess.run(
                    ['git', 'filter-repo', '--path', 'node_modules/', '--invert-paths', '--force'],
                    cwd=self.project_dir,
                    check=True,
                    capture_output=True
                )
                return True, "Cleaned history with git-filter-repo"
            except Exception as e:
                return False, f"git-filter-repo failed: {e}"

        # Fall back to git filter-branch (slower but more available)
        try:
            # Remove node_modules from all commits
            result = subprocess.run(
                [
                    'git', 'filter-branch', '--force', '--index-filter',
                    'git rm -rf --cached --ignore-unmatch node_modules .next',
                    '--prune-empty', '--', '--all'
                ],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                # Clean up refs
                subprocess.run(
                    ['git', 'reflog', 'expire', '--expire=now', '--all'],
                    cwd=self.project_dir,
                    capture_output=True
                )
                subprocess.run(
                    ['git', 'gc', '--prune=now', '--aggressive'],
                    cwd=self.project_dir,
                    capture_output=True
                )
                return True, "Cleaned history with git-filter-branch"
            else:
                return False, f"filter-branch failed: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, "History cleanup timed out"
        except Exception as e:
            return False, f"History cleanup failed: {e}"

    def reset_to_clean_state(self) -> Tuple[bool, str]:
        """
        Nuclear option: Reset repository to a clean state by:
        1. Creating a new orphan branch
        2. Adding current (clean) files
        3. Force pushing

        This loses all git history but guarantees push will work.

        Returns:
            (success, message)
        """
        print("🔄 Resetting to clean state (this will lose git history)...")

        try:
            # Ensure .gitignore is proper first
            critical_ignores = [
                'node_modules/',
                '.next/',
                '*.node',
            ]
            self.ensure_gitignore_has_entries(critical_ignores)

            # Create orphan branch
            subprocess.run(
                ['git', 'checkout', '--orphan', 'clean-main'],
                cwd=self.project_dir,
                check=True,
                capture_output=True
            )

            # Add all files (respecting .gitignore)
            subprocess.run(
                ['git', 'add', '-A'],
                cwd=self.project_dir,
                check=True,
                capture_output=True
            )

            # Check for any remaining large files
            large_files = self.find_large_files()
            if large_files:
                # Remove them from staging
                for filepath, size in large_files:
                    subprocess.run(
                        ['git', 'reset', 'HEAD', filepath],
                        cwd=self.project_dir,
                        capture_output=True
                    )
                    print(f"⚠️  Excluded large file: {filepath} ({size:.1f}MB)")

            # Commit
            subprocess.run(
                ['git', 'commit', '-m', 'Clean repository restart\n\n🤖 Generated by autonomous coding agent\nCo-Authored-By: Claude <noreply@anthropic.com>'],
                cwd=self.project_dir,
                check=True,
                capture_output=True
            )

            # Delete old main and rename
            subprocess.run(
                ['git', 'branch', '-D', 'main'],
                cwd=self.project_dir,
                capture_output=True  # May fail if no main exists
            )

            subprocess.run(
                ['git', 'branch', '-m', 'main'],
                cwd=self.project_dir,
                check=True,
                capture_output=True
            )

            return True, "Repository reset to clean state"

        except Exception as e:
            # Try to recover
            subprocess.run(
                ['git', 'checkout', 'main'],
                cwd=self.project_dir,
                capture_output=True
            )
            return False, f"Reset failed: {e}"

    def get_changed_files(self) -> List[str]:
        """Get list of changed files."""
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True
            )

            files = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    # Format: "XY filename" where XY is status code
                    files.append(line[3:])

            return files
        except Exception:
            return []

    def generate_commit_message(
        self,
        issues_completed: List[str],
        issues_attempted: List[str],
        session_metrics: Dict,
        session_id: str
    ) -> str:
        """
        Generate intelligent commit message from session data.

        Format:
        feat: Implement [features from issues]

        Session: [session_id]
        Issues completed: [list]
        Duration: [time]

        - [file changes summary]

        🤖 Generated by autonomous coding agent
        Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
        """
        # Determine commit type
        if len(issues_completed) == 0:
            commit_type = "chore"
            summary = "Work in progress - session incomplete"
        elif len(issues_completed) == 1:
            commit_type = "feat"
            summary = f"Implement {issues_completed[0]}"
        else:
            commit_type = "feat"
            summary = f"Implement {len(issues_completed)} features"

        # Build commit message
        message_parts = [
            f"{commit_type}: {summary}",
            "",
            f"Session: {session_id}",
        ]

        # Add completed issues
        if issues_completed:
            message_parts.append("")
            message_parts.append("Completed:")
            for issue in issues_completed:
                message_parts.append(f"  - {issue}")

        # Add session metrics
        if session_metrics:
            message_parts.append("")
            message_parts.append("Session Metrics:")

            duration = session_metrics.get('duration_minutes', 'N/A')
            message_parts.append(f"  - Duration: {duration} minutes")

            api_calls = session_metrics.get('linear_api_calls', 0)
            cached = session_metrics.get('linear_api_cached', 0)
            message_parts.append(f"  - Linear API: {api_calls} calls ({cached} cached)")

            tools = len(session_metrics.get('tools_used', {}))
            message_parts.append(f"  - Tools used: {tools}")

            errors = session_metrics.get('errors', 0)
            if errors > 0:
                message_parts.append(f"  - Errors: {errors}")

        # Add changed files summary
        changed_files = self.get_changed_files()
        if changed_files and len(changed_files) <= 10:
            message_parts.append("")
            message_parts.append("Files changed:")
            for file in changed_files[:10]:
                message_parts.append(f"  - {file}")
        elif changed_files:
            message_parts.append("")
            message_parts.append(f"Files changed: {len(changed_files)} files")

        # Add footer
        message_parts.extend([
            "",
            "🤖 Generated by autonomous coding agent",
            "",
            "Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
        ])

        return '\n'.join(message_parts)

    def commit(
        self,
        issues_completed: List[str],
        issues_attempted: List[str],
        session_metrics: Dict,
        session_id: str
    ) -> Tuple[bool, str]:
        """
        Commit changes with generated message.

        Returns:
            (success: bool, message: str)
        """
        # Check if git is configured
        if not self.check_git_configured():
            print("📝 Configuring git for first time...")
            if not self.configure_git():
                return False, "Failed to configure git"

        # Check for changes
        if not self.has_changes():
            return True, "No changes to commit"

        try:
            # Stage all changes
            subprocess.run(
                ['git', 'add', '-A'],
                cwd=self.project_dir,
                check=True
            )

            # Generate commit message
            commit_msg = self.generate_commit_message(
                issues_completed,
                issues_attempted,
                session_metrics,
                session_id
            )

            # Commit
            subprocess.run(
                ['git', 'commit', '-m', commit_msg],
                cwd=self.project_dir,
                check=True,
                capture_output=True
            )

            print(f"✅ Committed changes for session {session_id}")
            return True, f"Committed {len(self.get_changed_files())} files"

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to commit: {e.stderr.decode() if e.stderr else str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def pull_rebase(self, branch: str = "main") -> Tuple[bool, str]:
        """
        Pull latest changes from remote with rebase.

        Returns:
            (success: bool, message: str)
        """
        try:
            print(f"📥 Pulling latest changes from origin/{branch}...")
            result = subprocess.run(
                ['git', 'pull', '--rebase', 'origin', branch],
                cwd=self.project_dir,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print(f"✅ Pull successful")
                return True, "Pulled latest changes"
            else:
                error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()

                # Check for merge conflicts
                if "conflict" in error_msg.lower():
                    print(f"⚠️  Merge conflict detected, aborting rebase...")
                    subprocess.run(
                        ['git', 'rebase', '--abort'],
                        cwd=self.project_dir,
                        capture_output=True
                    )
                    return False, "Merge conflict - rebase aborted"

                return False, f"Pull failed: {error_msg}"

        except Exception as e:
            return False, f"Pull error: {str(e)}"

    def push(self, branch: str = "main") -> Tuple[bool, str]:
        """
        Push commits to remote repository.
        Automatically pulls with rebase first to handle remote changes.
        Handles large file errors by attempting cleanup.

        Returns:
            (success: bool, message: str)
        """
        if not self.auto_push:
            return True, "Auto-push disabled"

        try:
            # Check if remote exists
            result = subprocess.run(
                ['git', 'remote'],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True
            )

            if not result.stdout.strip():
                return False, "No git remote configured"

            # Check for large files BEFORE attempting push
            large_files = self.find_large_files()
            if large_files:
                print("⚠️  Large files detected that would fail push:")
                for filepath, size in large_files:
                    print(f"   - {filepath}: {size:.1f}MB")
                print("Attempting to fix...")

                # Ensure .gitignore is updated
                self.ensure_gitignore_has_entries([
                    'node_modules/', '.next/', '*.node', 'out/', 'build/', 'dist/'
                ])

                # Remove from tracking
                for filepath, _ in large_files:
                    subprocess.run(
                        ['git', 'rm', '-r', '--cached', '--ignore-unmatch', filepath],
                        cwd=self.project_dir,
                        capture_output=True
                    )

                # Recommit
                if self.has_changes():
                    subprocess.run(
                        ['git', 'commit', '-m', 'chore: Remove large files from tracking\n\n🤖 Generated by autonomous coding agent'],
                        cwd=self.project_dir,
                        capture_output=True
                    )

            # ALWAYS pull before push to avoid rejection
            pull_success, pull_msg = self.pull_rebase(branch)
            if not pull_success:
                print(f"⚠️  Pull failed: {pull_msg}, attempting push anyway...")

            # Push to remote
            print(f"📤 Pushing to remote ({branch})...")
            push_result = subprocess.run(
                ['git', 'push', 'origin', branch],
                cwd=self.project_dir,
                capture_output=True,
                text=True
            )

            if push_result.returncode == 0:
                print(f"✅ Successfully pushed to origin/{branch}")
                return True, f"Pushed to origin/{branch}"

            error_msg = push_result.stderr if push_result.stderr else push_result.stdout

            # Handle large file errors (file already in history)
            if "exceeds" in error_msg.lower() and "file size limit" in error_msg.lower():
                print("🔴 Large files in git history are blocking push")
                print("   Attempting to clean git history...")

                # Try to clean history
                clean_success, clean_msg = self.clean_large_files_from_history()

                if clean_success:
                    # Retry push with force (history was rewritten)
                    print("📤 Retrying push after history cleanup...")
                    retry_result = subprocess.run(
                        ['git', 'push', '--force', 'origin', branch],
                        cwd=self.project_dir,
                        capture_output=True,
                        text=True
                    )
                    if retry_result.returncode == 0:
                        return True, "Pushed after cleaning git history"
                    else:
                        # Last resort: reset to clean state
                        print("⚠️  History cleanup didn't work. Using nuclear option...")
                        reset_success, reset_msg = self.reset_to_clean_state()
                        if reset_success:
                            # Force push clean state
                            final_result = subprocess.run(
                                ['git', 'push', '--force', 'origin', branch],
                                cwd=self.project_dir,
                                capture_output=True,
                                text=True
                            )
                            if final_result.returncode == 0:
                                return True, "Pushed after repository reset (history was lost)"
                            return False, f"Even reset failed: {final_result.stderr}"
                        return False, f"Reset failed: {reset_msg}"
                else:
                    return False, f"Could not clean history: {clean_msg}"

            # Handle rejection - try pull and push again
            if "rejected" in error_msg.lower() or "non-fast-forward" in error_msg.lower():
                print(f"⚠️  Push rejected, pulling and retrying...")
                pull_success, pull_msg = self.pull_rebase(branch)

                if pull_success:
                    # Retry push
                    retry_result = subprocess.run(
                        ['git', 'push', 'origin', branch],
                        cwd=self.project_dir,
                        capture_output=True,
                        text=True
                    )

                    if retry_result.returncode == 0:
                        print(f"✅ Successfully pushed to origin/{branch} after pull")
                        return True, f"Pushed to origin/{branch} (after pull)"
                    else:
                        return False, f"Push failed after pull: {retry_result.stderr}"
                else:
                    return False, f"Cannot push - pull failed: {pull_msg}"

            # Handle authentication errors
            if "authentication" in error_msg.lower() or "permission" in error_msg.lower():
                print(f"⚠️  Push failed: Authentication required")
                print(f"   Run: gh auth login")
                print(f"   Or set up SSH keys")
                return False, "Authentication required"

            print(f"❌ Push failed: {error_msg}")
            return False, error_msg

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            print(f"❌ Push failed: {error_msg}")
            return False, error_msg

    def commit_and_push(
        self,
        issues_completed: List[str],
        issues_attempted: List[str],
        session_metrics: Dict,
        session_id: str,
        branch: str = "main"
    ) -> Tuple[bool, str]:
        """
        Commit changes and push to remote in one operation.

        Returns:
            (success: bool, message: str)
        """
        # Commit
        commit_success, commit_msg = self.commit(
            issues_completed,
            issues_attempted,
            session_metrics,
            session_id
        )

        if not commit_success:
            return False, commit_msg

        if commit_msg == "No changes to commit":
            return True, commit_msg

        # Push
        push_success, push_msg = self.push(branch)

        if not push_success:
            return False, f"Committed but push failed: {push_msg}"

        return True, f"{commit_msg}, {push_msg}"


def create_git_manager(project_dir: Path, auto_push: bool = True) -> GitManager:
    """
    Factory function to create GitManager instance.

    Usage:
        git_mgr = create_git_manager(project_dir, auto_push=True)

        # At end of session
        success, msg = git_mgr.commit_and_push(
            issues_completed=['PRO-56: Auth flow'],
            issues_attempted=['PRO-56'],
            session_metrics=logger.metrics,
            session_id='session_001'
        )

        if success:
            print(f"✅ {msg}")
        else:
            print(f"⚠️  {msg}")
    """
    return GitManager(project_dir, auto_push)
