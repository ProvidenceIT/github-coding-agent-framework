# Contract: GitHubProjectsManager

**Module**: `github_projects.py` (NEW)
**Class**: `GitHubProjectsManager`

## Interface

### Constructor

```python
def __init__(self, repo: str, owner: str, project_dir: Path)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| repo | str | Yes | Repository name (without owner) |
| owner | str | Yes | Repository owner |
| project_dir | Path | Yes | Project directory for metadata storage |

---

### create_project

Create a new GitHub Project board.

```python
def create_project(self, title: str) -> int
```

**Input**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| title | str | Yes | Project board title |

**Output**: `int` - Project number

**Side Effects**:
- Creates project via GraphQL API
- Stores project_id, number in `.github_project.json`
- Initializes status field metadata

**Raises**: `RuntimeError` if creation fails

---

### link_repo

Link repository to project board.

```python
def link_repo(self) -> bool
```

**Output**: `bool` - Success status

---

### setup_status_field

Discover or create Status field with standard columns.

```python
def setup_status_field(self) -> bool
```

**Behavior**:
1. Query project for existing "Status" field
2. If not found, create single-select field
3. Ensure "Todo", "In Progress", "Done" options exist
4. Store field_id and option_ids in metadata

**Output**: `bool` - Success status

---

### add_issue_to_project

Add an issue to the project board.

```python
def add_issue_to_project(self, issue_number: int) -> Optional[str]
```

**Input**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| issue_number | int | Yes | GitHub issue number |

**Output**: `Optional[str]` - Item ID if successful, None otherwise

**Behavior**:
1. Get issue node ID via `gh issue view`
2. Add to project via GraphQL `addProjectV2ItemById`
3. Set initial status to "Todo"
4. Store item mapping in metadata

---

### update_item_status

Update issue status on the board.

```python
def update_item_status(self, issue_number: int, status: str) -> bool
```

**Input**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| issue_number | int | Yes | GitHub issue number |
| status | str | Yes | Target status: "Todo", "In Progress", "Done" |

**Output**: `bool` - Success status

**Raises**: `ValueError` if status not in valid options

---

### get_project_url

Get URL to project board.

```python
def get_project_url(self) -> str
```

**Output**: `str` - Full URL to GitHub Projects board

---

## Metadata File Format

**Location**: `{project_dir}/.github_project.json`

```json
{
  "repo": "owner/repo-name",
  "project_id": "PVT_kwDOABC123",
  "project_number": 1,
  "project_url": "https://github.com/orgs/owner/projects/1",
  "status_field_id": "PVTSSF_abc123",
  "status_options": {
    "Todo": "98f5c4e7-...",
    "In Progress": "47d3e2f1-...",
    "Done": "f7a2b3c4-..."
  },
  "items": {
    "42": {
      "item_id": "PVTI_abc123",
      "status": "In Progress",
      "added_at": "2025-12-17T14:00:00",
      "updated_at": "2025-12-17T14:30:22"
    }
  }
}
```

---

## Integration Points

### In Initializer (`initializer_prompt.md`)

```python
# After creating repository and issues
projects_mgr = GitHubProjectsManager(repo, owner, project_dir)
projects_mgr.create_project(f"{repo_name} Development")
projects_mgr.link_repo()
projects_mgr.setup_status_field()

# Add all open issues to board
for issue in open_issues:
    projects_mgr.add_issue_to_project(issue['number'])
```

### In Claim (`parallel_agent.py`)

```python
# After claiming issue
projects_mgr.update_item_status(issue_num, "In Progress")
```

### In Close (`parallel_agent.py`)

```python
# After closing issue
projects_mgr.update_item_status(issue_num, "Done")
```

---

## GraphQL Operations

### Create Project
```graphql
mutation CreateProject($ownerId: ID!, $title: String!) {
  createProjectV2(input: {ownerId: $ownerId, title: $title}) {
    projectV2 { id number url }
  }
}
```

### Add Item
```graphql
mutation AddItem($projectId: ID!, $contentId: ID!) {
  addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
    item { id }
  }
}
```

### Update Status
```graphql
mutation UpdateStatus($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
  updateProjectV2ItemFieldValue(input: {
    projectId: $projectId,
    itemId: $itemId,
    fieldId: $fieldId,
    value: {singleSelectOptionId: $optionId}
  }) { projectV2Item { id } }
}
```

---

## Error Handling

| Scenario | Handling |
|----------|----------|
| Project already exists | Find by title, use existing |
| Status field missing | Create with default columns |
| Column renamed | Detect missing option, warn operator |
| Permission denied | Log error, disable project updates |
| Rate limited | Queue updates, batch later |
