"""
Prompt Loading Utilities
========================

Functions for loading prompt templates from the prompts directory.
"""

import shutil
from pathlib import Path


PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(name: str) -> str:
    """Load a prompt template from the prompts directory."""
    prompt_path = PROMPTS_DIR / f"{name}.md"
    return prompt_path.read_text(encoding='utf-8')


def get_initializer_prompt() -> str:
    """Load the initializer prompt."""
    return load_prompt("initializer_prompt")


def get_coding_prompt() -> str:
    """Load the coding agent prompt."""
    return load_prompt("coding_prompt")


def copy_spec_to_project(project_dir: Path, project_name: str = None) -> None:
    """
    Copy the app spec file into the project directory for the agent to read.

    Lookup order:
    1. prompts/{project_name}/app_spec.txt (if project_name provided)
    2. prompts/{project_dir.name}/app_spec.txt (using directory name)
    3. prompts/app_spec.txt (legacy fallback)

    Args:
        project_dir: Target project directory
        project_name: Optional project name to look up spec from prompts/{project_name}/
    """
    spec_dest = project_dir / "app_spec.txt"

    # If spec already exists in project, don't overwrite
    if spec_dest.exists():
        print(f"✓ app_spec.txt already exists in project directory")
        return

    # Determine which project name to use
    lookup_name = project_name if project_name else project_dir.name

    # Try to find spec in order of preference
    possible_sources = [
        PROMPTS_DIR / lookup_name / "app_spec.txt",  # Project-specific spec
        PROMPTS_DIR / project_dir.name / "app_spec.txt",  # Directory name fallback
        PROMPTS_DIR / "app_spec.txt"  # Legacy location
    ]

    spec_source = None
    for source in possible_sources:
        if source.exists():
            spec_source = source
            break

    if spec_source is None:
        print(f"❌ ERROR: Could not find app_spec.txt in any of these locations:")
        for source in possible_sources:
            print(f"   - {source}")
        print(f"\n💡 TIP: Create a spec at: {PROMPTS_DIR / lookup_name / 'app_spec.txt'}")
        raise FileNotFoundError(f"No app_spec.txt found for project '{lookup_name}'")

    # Copy the spec to project directory
    shutil.copy(spec_source, spec_dest)
    print(f"✅ Copied app_spec.txt from: {spec_source.relative_to(Path.cwd())}")


def list_available_projects() -> list:
    """
    List all available project specs in the prompts directory.

    Returns:
        List of project names that have app_spec.txt files
    """
    projects = []

    # Find all subdirectories in prompts/ that contain app_spec.txt
    for item in PROMPTS_DIR.iterdir():
        if item.is_dir():
            spec_file = item / "app_spec.txt"
            if spec_file.exists():
                projects.append(item.name)

    # Also check for legacy location
    if (PROMPTS_DIR / "app_spec.txt").exists():
        projects.append("(default)")

    return sorted(projects)


def create_project_spec(project_name: str, template: str = None) -> Path:
    """
    Create a new project spec directory structure.

    Args:
        project_name: Name of the project
        template: Optional template content for app_spec.txt

    Returns:
        Path to the created app_spec.txt file
    """
    project_dir = PROMPTS_DIR / project_name
    project_dir.mkdir(parents=True, exist_ok=True)

    spec_file = project_dir / "app_spec.txt"

    if template:
        spec_file.write_text(template, encoding='utf-8')
    elif not spec_file.exists():
        # Create a basic template
        default_template = f"""# {project_name.upper().replace('-', ' ')}

## PROJECT OVERVIEW

### Vision
[Describe the vision and purpose of this project]

### Core Value Proposition
- [Key benefit 1]
- [Key benefit 2]
- [Key benefit 3]

### Primary Users
- [User type 1]
- [User type 2]

### Success Metrics
- [Metric 1]
- [Metric 2]
- [Metric 3]

## TECHNICAL STACK

### Frontend
- [Framework/libraries]

### Backend
- [Framework/libraries]

### Database
- [Database system]

### Infrastructure
- [Hosting/deployment]

## FEATURES

### Phase 1 - MVP
1. [Feature 1]
2. [Feature 2]
3. [Feature 3]

### Phase 2 - Enhancement
1. [Feature 1]
2. [Feature 2]

### Phase 3 - Scale
1. [Feature 1]
2. [Feature 2]

## DETAILED REQUIREMENTS

[Add detailed requirements here. The agent will create 50 GitHub issues from this spec.]
"""
        spec_file.write_text(default_template, encoding='utf-8')

    return spec_file
