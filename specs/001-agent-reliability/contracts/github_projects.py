"""
GitHub Projects v2 Integration Contract
=======================================

Interface contract for GitHub Projects v2 Kanban board integration.

This is a contract/interface definition - not the implementation.
Implementation goes in the root-level github_projects.py module.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class ProjectStatus(Enum):
    """
    Kanban column status matching GitHub Projects defaults.

    Values are the display names used in GitHub Projects UI.
    """
    TODO = "Todo"
    IN_PROGRESS = "In Progress"
    DONE = "Done"


@dataclass
class GitHubProjectItem:
    """
    Represents an issue's presence on a GitHub Projects v2 board.

    Attributes:
        item_id: Projects v2 item ID (PVTI_...)
        issue_number: GitHub issue number
        current_status: Current Kanban column
        last_updated: When status last changed
    """
    item_id: str                         # GraphQL node ID
    issue_number: int                    # GitHub issue number
    current_status: ProjectStatus        # Current column
    last_updated: datetime               # Last status change

    def to_dict(self) -> Dict:
        """Serialize for storage."""
        return {
            "item_id": self.item_id,
            "issue_number": self.issue_number,
            "current_status": self.current_status.value,
            "last_updated": self.last_updated.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "GitHubProjectItem":
        """Deserialize from storage."""
        return cls(
            item_id=data["item_id"],
            issue_number=data["issue_number"],
            current_status=ProjectStatus(data["current_status"]),
            last_updated=datetime.fromisoformat(data["last_updated"]),
        )


@dataclass
class ProjectMetadata:
    """
    Metadata for a GitHub Projects v2 board.

    Stored in .github_project.json alongside repo info.
    """
    project_id: str                      # GraphQL node ID (PVT_...)
    project_number: int                  # Human-readable project number
    title: str                           # Project title
    status_field_id: str                 # Field ID for Status column
    status_options: Dict[str, str]       # {display_name: option_id}
    items: Dict[int, GitHubProjectItem]  # {issue_number: item}
    created_at: datetime
    linked_repo: str                     # owner/repo format

    def get_option_id(self, status: ProjectStatus) -> Optional[str]:
        """Get GraphQL option ID for a status."""
        return self.status_options.get(status.value)

    def to_dict(self) -> Dict:
        """Serialize for storage."""
        return {
            "project_id": self.project_id,
            "project_number": self.project_number,
            "title": self.title,
            "status_field_id": self.status_field_id,
            "status_options": self.status_options,
            "items": {
                str(num): item.to_dict()
                for num, item in self.items.items()
            },
            "created_at": self.created_at.isoformat(),
            "linked_repo": self.linked_repo,
        }


class IGitHubProjectsManager(ABC):
    """
    Interface for GitHub Projects v2 integration.

    Implementations must handle:
    - Project discovery/creation
    - Issue-to-item mapping
    - Status updates (Todo -> In Progress -> Done)
    - Field ID caching
    """

    @abstractmethod
    def get_or_create_project(
        self,
        owner: str,
        repo: str,
        title: str = "Agent Progress"
    ) -> ProjectMetadata:
        """
        Get existing project or create new one.

        Steps:
        1. Check .github_project.json for cached project
        2. If not found, query GitHub for project by title
        3. If not found, create new project
        4. Discover Status field and options
        5. Link project to repository
        6. Cache metadata

        Args:
            owner: GitHub owner (org or user)
            repo: Repository name
            title: Project title to find/create

        Returns:
            ProjectMetadata for the project
        """
        pass

    @abstractmethod
    def add_issue_to_project(
        self,
        issue_number: int,
        status: ProjectStatus = ProjectStatus.TODO
    ) -> GitHubProjectItem:
        """
        Add an issue to the project board.

        GraphQL mutation: addProjectV2ItemById

        Args:
            issue_number: GitHub issue number
            status: Initial status column

        Returns:
            GitHubProjectItem representing the added item
        """
        pass

    @abstractmethod
    def update_issue_status(
        self,
        issue_number: int,
        status: ProjectStatus
    ) -> bool:
        """
        Update an issue's status on the project board.

        GraphQL mutation: updateProjectV2ItemFieldValue

        Args:
            issue_number: GitHub issue number
            status: New status column

        Returns:
            True if update successful
        """
        pass

    @abstractmethod
    def move_to_in_progress(self, issue_number: int) -> bool:
        """
        Move issue to "In Progress" column.

        Convenience method for claim_issue workflow.

        Args:
            issue_number: GitHub issue number

        Returns:
            True if moved successfully
        """
        pass

    @abstractmethod
    def move_to_done(self, issue_number: int) -> bool:
        """
        Move issue to "Done" column.

        Convenience method for close_issue workflow.

        Args:
            issue_number: GitHub issue number

        Returns:
            True if moved successfully
        """
        pass

    @abstractmethod
    def get_item(self, issue_number: int) -> Optional[GitHubProjectItem]:
        """
        Get project item for an issue.

        Args:
            issue_number: GitHub issue number

        Returns:
            GitHubProjectItem if on board, None otherwise
        """
        pass

    @abstractmethod
    def get_items_by_status(
        self,
        status: ProjectStatus
    ) -> List[GitHubProjectItem]:
        """
        Get all items in a status column.

        Args:
            status: Status column to filter

        Returns:
            List of items in that column
        """
        pass

    @abstractmethod
    def sync_all_issues(self) -> int:
        """
        Add all open issues to the project board.

        Used during initialization to populate board.

        Returns:
            Number of issues added
        """
        pass

    @abstractmethod
    def refresh_metadata(self) -> ProjectMetadata:
        """
        Refresh project metadata from GitHub.

        Useful if columns have been modified manually.

        Returns:
            Updated ProjectMetadata
        """
        pass


# GraphQL query templates
GRAPHQL_GET_PROJECT = """
query GetProject($owner: String!, $number: Int!) {
  organization(login: $owner) {
    projectV2(number: $number) {
      id
      title
      fields(first: 20) {
        nodes {
          ... on ProjectV2FieldCommon {
            id
            name
          }
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

GRAPHQL_CREATE_PROJECT = """
mutation CreateProject($ownerId: ID!, $title: String!) {
  createProjectV2(input: {ownerId: $ownerId, title: $title}) {
    projectV2 {
      id
      number
      title
    }
  }
}
"""

GRAPHQL_ADD_ITEM = """
mutation AddItem($projectId: ID!, $contentId: ID!) {
  addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
    item {
      id
    }
  }
}
"""

GRAPHQL_UPDATE_STATUS = """
mutation UpdateStatus($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
  updateProjectV2ItemFieldValue(input: {
    projectId: $projectId
    itemId: $itemId
    fieldId: $fieldId
    value: {singleSelectOptionId: $optionId}
  }) {
    projectV2Item {
      id
    }
  }
}
"""

# gh CLI command templates
GH_PROJECT_LIST = "gh project list --owner {owner} --format json"
GH_PROJECT_CREATE = "gh project create --owner {owner} --title \"{title}\""
GH_PROJECT_ITEM_ADD = "gh project item-add {number} --owner {owner} --url {issue_url}"
GH_PROJECT_FIELD_LIST = "gh project field-list {number} --owner {owner} --format json"
