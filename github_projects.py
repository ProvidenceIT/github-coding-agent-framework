"""
GitHub Projects v2 Integration
==============================

Manages GitHub Projects (v2) for visual Kanban-style issue tracking.

Features:
- Create/get project boards for repositories
- Move issues through columns (Todo -> In Progress -> Done)
- Sync all issues to project board
- Store project metadata in .github_project.json

Uses GitHub CLI (gh) and GraphQL API for Projects v2 operations.
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from github_cache import execute_gh_command, GitHubAPIError


# Default column names for Kanban board
DEFAULT_COLUMNS = {
    'todo': 'Todo',
    'in_progress': 'In Progress',
    'done': 'Done',
}


class GitHubProjectsManager:
    """
    Manages GitHub Projects v2 for repository issue tracking (T059).

    Provides:
    - Project board creation/retrieval
    - Issue-to-project linking
    - Column status updates (Todo -> In Progress -> Done)
    - Batch sync of existing issues
    """

    def __init__(
        self,
        project_dir: Path,
        repo: str,
        logger: logging.Logger = None
    ):
        """
        Initialize projects manager.

        Args:
            project_dir: Local project directory
            repo: GitHub repository in owner/name format
            logger: Optional logger for operations
        """
        self.project_dir = project_dir
        self.repo = repo
        self.owner, self.repo_name = repo.split('/')
        self.logger = logger
        self.project_file = project_dir / ".github_project.json"

        # Cache for project/field IDs
        self._project_id: Optional[str] = None
        self._status_field_id: Optional[str] = None
        self._status_options: Dict[str, str] = {}  # column_name -> option_id

    def _log(self, message: str, level: str = "info"):
        """Log message if logger available."""
        if self.logger:
            getattr(self.logger, level)(message, extra={'category': 'github_projects'})
        else:
            print(f"[Projects] {message}")

    def _run_graphql(self, query: str, variables: Dict = None) -> Tuple[bool, Dict]:
        """
        Execute a GraphQL query via gh api.

        Args:
            query: GraphQL query string
            variables: Optional variables dict

        Returns:
            Tuple of (success, response_data)
        """
        try:
            cmd = ['gh', 'api', 'graphql']

            # Build query body
            body = {'query': query}
            if variables:
                body['variables'] = variables

            cmd.extend(['-f', f"query={query}"])

            if variables:
                for key, value in variables.items():
                    cmd.extend(['-F', f"{key}={value}"])

            success, stdout, stderr = execute_gh_command(
                cmd=cmd,
                cwd=self.project_dir,
                timeout=60,
                logger=self.logger
            )

            if success:
                return True, json.loads(stdout)
            else:
                self._log(f"GraphQL query failed: {stderr}", "warning")
                return False, {}

        except GitHubAPIError as e:
            self._log(f"GraphQL error: {e.message}", "error")
            return False, {}
        except json.JSONDecodeError as e:
            self._log(f"Failed to parse GraphQL response: {e}", "error")
            return False, {}

    def get_or_create_project(
        self,
        project_name: str = None,
        description: str = None
    ) -> Optional[str]:
        """
        Get existing project or create new one (T060).

        Args:
            project_name: Name for the project (defaults to repo name)
            description: Project description

        Returns:
            Project ID if successful, None otherwise
        """
        project_name = project_name or f"{self.repo_name} Board"
        description = description or f"Automated project board for {self.repo}"

        # Check if we have cached project ID
        if self._project_id:
            return self._project_id

        # Check metadata file
        metadata = self._load_metadata()
        if metadata.get('project_id'):
            self._project_id = metadata['project_id']
            self._status_field_id = metadata.get('status_field_id')
            self._status_options = metadata.get('status_options', {})
            self._log(f"Using cached project ID: {self._project_id}")
            return self._project_id

        # List existing projects
        try:
            cmd = [
                'gh', 'project', 'list',
                '--owner', self.owner,
                '--format', 'json'
            ]
            success, stdout, stderr = execute_gh_command(
                cmd=cmd,
                cwd=self.project_dir,
                timeout=30,
                logger=self.logger
            )

            if success:
                projects = json.loads(stdout)
                # Find matching project
                for project in projects.get('projects', []):
                    if project.get('title') == project_name:
                        self._project_id = str(project.get('number'))
                        self._log(f"Found existing project: {project_name} (#{self._project_id})")
                        self._cache_project_metadata()
                        return self._project_id

        except (GitHubAPIError, json.JSONDecodeError) as e:
            self._log(f"Error listing projects: {e}", "warning")

        # Create new project
        self._log(f"Creating new project: {project_name}")
        try:
            cmd = [
                'gh', 'project', 'create',
                '--owner', self.owner,
                '--title', project_name,
                '--format', 'json'
            ]
            success, stdout, stderr = execute_gh_command(
                cmd=cmd,
                cwd=self.project_dir,
                timeout=60,
                logger=self.logger
            )

            if success:
                result = json.loads(stdout)
                self._project_id = str(result.get('number'))
                self._log(f"Created project: {project_name} (#{self._project_id})")
                self._cache_project_metadata()
                return self._project_id

        except (GitHubAPIError, json.JSONDecodeError) as e:
            self._log(f"Error creating project: {e}", "error")

        return None

    def _get_project_field_ids(self) -> bool:
        """
        Get Status field ID and option IDs for the project.

        Returns:
            True if successful
        """
        if not self._project_id:
            return False

        if self._status_field_id and self._status_options:
            return True

        # Query project fields
        query = """
        query($owner: String!, $number: Int!) {
          user(login: $owner) {
            projectV2(number: $number) {
              id
              fields(first: 20) {
                nodes {
                  ... on ProjectV2SingleSelectField {
                    id
                    name
                    options {
                      id
                      name
                    }
                  }
                }
              }
            }
          }
        }
        """

        # Try user first, then organization
        for owner_type in ['user', 'organization']:
            try:
                if owner_type == 'organization':
                    query = query.replace('user(login:', 'organization(login:')

                cmd = [
                    'gh', 'api', 'graphql',
                    '-f', f'query={query}',
                    '-F', f'owner={self.owner}',
                    '-F', f'number={self._project_id}'
                ]

                success, stdout, stderr = execute_gh_command(
                    cmd=cmd,
                    cwd=self.project_dir,
                    timeout=30,
                    logger=self.logger
                )

                if success:
                    data = json.loads(stdout)
                    owner_data = data.get('data', {}).get(owner_type, {})
                    project = owner_data.get('projectV2', {})

                    if project:
                        # Find Status field
                        for field in project.get('fields', {}).get('nodes', []):
                            if field and field.get('name') == 'Status':
                                self._status_field_id = field.get('id')
                                # Map option names to IDs
                                for option in field.get('options', []):
                                    name_lower = option.get('name', '').lower()
                                    self._status_options[name_lower] = option.get('id')

                                self._log(f"Found Status field with options: {list(self._status_options.keys())}")
                                self._cache_project_metadata()
                                return True

            except (GitHubAPIError, json.JSONDecodeError) as e:
                continue

        self._log("Could not find Status field in project", "warning")
        return False

    def add_issue_to_project(self, issue_number: int) -> Optional[str]:
        """
        Add an issue to the project board (T061).

        Args:
            issue_number: GitHub issue number

        Returns:
            Item ID if successful, None otherwise
        """
        if not self._project_id:
            self._log("No project ID set", "warning")
            return None

        try:
            cmd = [
                'gh', 'project', 'item-add', self._project_id,
                '--owner', self.owner,
                '--url', f"https://github.com/{self.repo}/issues/{issue_number}",
                '--format', 'json'
            ]

            success, stdout, stderr = execute_gh_command(
                cmd=cmd,
                cwd=self.project_dir,
                timeout=30,
                logger=self.logger
            )

            if success:
                result = json.loads(stdout)
                item_id = result.get('id')
                self._log(f"Added issue #{issue_number} to project (item: {item_id})")
                return item_id

        except (GitHubAPIError, json.JSONDecodeError) as e:
            self._log(f"Error adding issue #{issue_number} to project: {e}", "warning")

        return None

    def update_issue_status(
        self,
        issue_number: int,
        status: str
    ) -> bool:
        """
        Update issue status column in project (T062).

        Args:
            issue_number: GitHub issue number
            status: Status name (todo, in_progress, done)

        Returns:
            True if successful
        """
        if not self._project_id:
            self._log("No project ID set", "warning")
            return False

        # Ensure we have field IDs
        if not self._get_project_field_ids():
            self._log("Could not get project field IDs", "warning")
            return False

        # Get status option ID
        status_lower = status.lower().replace(' ', '_').replace('-', '_')
        option_id = self._status_options.get(status_lower)

        # Try common variations
        if not option_id:
            variations = {
                'todo': ['todo', 'to do', 'backlog'],
                'in_progress': ['in_progress', 'in progress', 'doing', 'active'],
                'done': ['done', 'complete', 'completed', 'closed']
            }
            for key in variations.get(status_lower, [status_lower]):
                option_id = self._status_options.get(key.lower())
                if option_id:
                    break

        if not option_id:
            self._log(f"Unknown status: {status}. Available: {list(self._status_options.keys())}", "warning")
            return False

        # Get item ID for this issue
        item_id = self._get_item_id_for_issue(issue_number)
        if not item_id:
            # Try adding the issue first
            item_id = self.add_issue_to_project(issue_number)
            if not item_id:
                return False

        # Update status via GraphQL
        mutation = """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
          updateProjectV2ItemFieldValue(input: {
            projectId: $projectId
            itemId: $itemId
            fieldId: $fieldId
            value: { singleSelectOptionId: $optionId }
          }) {
            projectV2Item {
              id
            }
          }
        }
        """

        try:
            # Need to get the actual project node ID (not number)
            project_node_id = self._get_project_node_id()
            if not project_node_id:
                return False

            cmd = [
                'gh', 'api', 'graphql',
                '-f', f'query={mutation}',
                '-f', f'projectId={project_node_id}',
                '-f', f'itemId={item_id}',
                '-f', f'fieldId={self._status_field_id}',
                '-f', f'optionId={option_id}'
            ]

            success, stdout, stderr = execute_gh_command(
                cmd=cmd,
                cwd=self.project_dir,
                timeout=30,
                logger=self.logger
            )

            if success:
                self._log(f"Updated issue #{issue_number} status to: {status}")
                return True

        except GitHubAPIError as e:
            self._log(f"Error updating issue #{issue_number} status: {e.message}", "warning")

        return False

    def move_to_in_progress(self, issue_number: int) -> bool:
        """Move issue to In Progress column (T063)."""
        return self.update_issue_status(issue_number, 'in_progress')

    def move_to_done(self, issue_number: int) -> bool:
        """Move issue to Done column (T063)."""
        return self.update_issue_status(issue_number, 'done')

    def move_to_todo(self, issue_number: int) -> bool:
        """Move issue to Todo column."""
        return self.update_issue_status(issue_number, 'todo')

    def sync_all_issues(self, include_closed: bool = False) -> Tuple[int, int]:
        """
        Add all repository issues to project board (T068).

        Args:
            include_closed: Whether to include closed issues

        Returns:
            Tuple of (added_count, failed_count)
        """
        if not self._project_id:
            self._log("No project ID set", "warning")
            return (0, 0)

        # Get all issues
        state = 'all' if include_closed else 'open'
        try:
            cmd = [
                'gh', 'issue', 'list',
                '--repo', self.repo,
                '--state', state,
                '--json', 'number,state',
                '--limit', '10000'
            ]

            success, stdout, stderr = execute_gh_command(
                cmd=cmd,
                cwd=self.project_dir,
                timeout=60,
                logger=self.logger
            )

            if not success:
                return (0, 0)

            issues = json.loads(stdout)
            added = 0
            failed = 0

            for issue in issues:
                number = issue.get('number')
                state = issue.get('state', 'OPEN').upper()

                # Add to project
                item_id = self.add_issue_to_project(number)
                if item_id:
                    added += 1
                    # Set initial status based on state
                    if state == 'CLOSED':
                        self.update_issue_status(number, 'done')
                    else:
                        self.update_issue_status(number, 'todo')
                else:
                    failed += 1

            self._log(f"Synced {added} issues to project ({failed} failed)")
            return (added, failed)

        except (GitHubAPIError, json.JSONDecodeError) as e:
            self._log(f"Error syncing issues: {e}", "error")
            return (0, 0)

    def _get_item_id_for_issue(self, issue_number: int) -> Optional[str]:
        """Get project item ID for an issue."""
        if not self._project_id:
            return None

        try:
            cmd = [
                'gh', 'project', 'item-list', self._project_id,
                '--owner', self.owner,
                '--format', 'json'
            ]

            success, stdout, stderr = execute_gh_command(
                cmd=cmd,
                cwd=self.project_dir,
                timeout=30,
                logger=self.logger
            )

            if success:
                data = json.loads(stdout)
                for item in data.get('items', []):
                    content = item.get('content', {})
                    if content.get('number') == issue_number:
                        return item.get('id')

        except (GitHubAPIError, json.JSONDecodeError):
            pass

        return None

    def _get_project_node_id(self) -> Optional[str]:
        """Get the GraphQL node ID for the project."""
        if not self._project_id:
            return None

        # Check cache first
        metadata = self._load_metadata()
        if metadata.get('project_node_id'):
            return metadata['project_node_id']

        # Query for project node ID
        for owner_type in ['user', 'organization']:
            query = f"""
            query($owner: String!, $number: Int!) {{
              {owner_type}(login: $owner) {{
                projectV2(number: $number) {{
                  id
                }}
              }}
            }}
            """

            try:
                cmd = [
                    'gh', 'api', 'graphql',
                    '-f', f'query={query}',
                    '-F', f'owner={self.owner}',
                    '-F', f'number={self._project_id}'
                ]

                success, stdout, stderr = execute_gh_command(
                    cmd=cmd,
                    cwd=self.project_dir,
                    timeout=30,
                    logger=self.logger
                )

                if success:
                    data = json.loads(stdout)
                    project = data.get('data', {}).get(owner_type, {}).get('projectV2', {})
                    if project and project.get('id'):
                        node_id = project['id']
                        # Cache it
                        metadata['project_node_id'] = node_id
                        self._save_metadata(metadata)
                        return node_id

            except (GitHubAPIError, json.JSONDecodeError):
                continue

        return None

    def _load_metadata(self) -> Dict:
        """Load project metadata from file (T064)."""
        if self.project_file.exists():
            try:
                data = json.loads(self.project_file.read_text(encoding='utf-8'))
                return data.get('projects_v2', {})
            except (json.JSONDecodeError, KeyError):
                pass
        return {}

    def _save_metadata(self, projects_data: Dict):
        """Save project metadata to file (T064)."""
        # Load existing file
        data = {}
        if self.project_file.exists():
            try:
                data = json.loads(self.project_file.read_text(encoding='utf-8'))
            except json.JSONDecodeError:
                pass

        # Update projects section
        data['projects_v2'] = projects_data
        data['projects_v2']['updated_at'] = datetime.now().isoformat()

        # Write back
        self.project_file.write_text(
            json.dumps(data, indent=2),
            encoding='utf-8'
        )

    def _cache_project_metadata(self):
        """Cache current project metadata."""
        metadata = self._load_metadata()
        metadata.update({
            'project_id': self._project_id,
            'status_field_id': self._status_field_id,
            'status_options': self._status_options,
        })
        self._save_metadata(metadata)


def create_projects_manager(
    project_dir: Path,
    repo: str,
    logger: logging.Logger = None
) -> GitHubProjectsManager:
    """
    Factory function to create GitHubProjectsManager.

    Usage:
        manager = create_projects_manager(project_dir, "owner/repo")
        project_id = manager.get_or_create_project()
        manager.move_to_in_progress(42)
        manager.move_to_done(42)
    """
    return GitHubProjectsManager(project_dir, repo, logger)
