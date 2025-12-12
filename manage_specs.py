#!/usr/bin/env python3
"""
Project Spec Manager
====================

Helper tool for managing project specifications in prompts/{project_name}/ directories.

Usage:
    python manage_specs.py list                          # List all available project specs
    python manage_specs.py create my-project            # Create new project spec
    python manage_specs.py view my-project              # View project spec content
    python manage_specs.py edit my-project              # Open spec in default editor
"""

import sys
import subprocess
from pathlib import Path
from prompts import list_available_projects, create_project_spec, PROMPTS_DIR


def list_specs():
    """List all available project specifications."""
    projects = list_available_projects()

    if not projects:
        print("No project specs found!")
        print("\nCreate one with: python manage_specs.py create my-project")
        return

    print("\nAvailable Project Specifications:")
    print("=" * 60)

    for project in projects:
        if project == "(default)":
            spec_path = PROMPTS_DIR / "app_spec.txt"
            print(f"  * {project:<30} [LEGACY]")
        else:
            spec_path = PROMPTS_DIR / project / "app_spec.txt"
            # Try to get first line as title
            try:
                with open(spec_path, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip().lstrip('#').strip()
                    if first_line:
                        print(f"  * {project:<30} {first_line[:40]}")
                    else:
                        print(f"  * {project}")
            except:
                print(f"  * {project}")

    print("=" * 60)
    print(f"\nTotal: {len(projects)} project(s)")
    print(f"\nUsage: python autonomous_agent_fixed.py --project-dir ./generations/my-project --project-name <name>")


def create_spec(project_name: str):
    """Create a new project specification."""
    if not project_name:
        print("ERROR: Project name required")
        print("Usage: python manage_specs.py create <project-name>")
        sys.exit(1)

    # Check if already exists
    spec_file = PROMPTS_DIR / project_name / "app_spec.txt"
    if spec_file.exists():
        print(f"WARNING: Project spec '{project_name}' already exists at:")
        print(f"   {spec_file}")
        response = input("\nOverwrite? [y/N]: ")
        if response.lower() != 'y':
            print("Cancelled")
            sys.exit(0)

    print(f"\nCreating project spec: {project_name}")
    created_file = create_project_spec(project_name)
    print(f"SUCCESS: Created {created_file}")
    print(f"\nNext steps:")
    print(f"   1. Edit the spec: {created_file}")
    print(f"   2. Run agent: python autonomous_agent_fixed.py --project-dir ./generations/{project_name} --project-name {project_name}")


def view_spec(project_name: str):
    """View a project specification."""
    if not project_name:
        print("ERROR: Project name required")
        print("Usage: python manage_specs.py view <project-name>")
        sys.exit(1)

    spec_file = PROMPTS_DIR / project_name / "app_spec.txt"
    if not spec_file.exists():
        print(f"ERROR: Project spec '{project_name}' not found at: {spec_file}")
        print(f"\nAvailable projects:")
        list_specs()
        sys.exit(1)

    print(f"\nProject Spec: {project_name}")
    print("=" * 70)
    with open(spec_file, 'r', encoding='utf-8') as f:
        content = f.read()
        print(content)
    print("=" * 70)


def edit_spec(project_name: str):
    """Open project specification in default editor."""
    if not project_name:
        print("ERROR: Project name required")
        print("Usage: python manage_specs.py edit <project-name>")
        sys.exit(1)

    spec_file = PROMPTS_DIR / project_name / "app_spec.txt"
    if not spec_file.exists():
        print(f"ERROR: Project spec '{project_name}' not found at: {spec_file}")
        print(f"\nCreate it first: python manage_specs.py create {project_name}")
        sys.exit(1)

    print(f"Opening {spec_file} in default editor...")

    # Try to open in default editor
    try:
        if sys.platform == 'win32':
            subprocess.run(['notepad', str(spec_file)])
        elif sys.platform == 'darwin':
            subprocess.run(['open', str(spec_file)])
        else:
            # Linux
            subprocess.run(['xdg-open', str(spec_file)])
    except Exception as e:
        print(f"ERROR: Could not open editor: {e}")
        print(f"Manually edit: {spec_file}")


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == 'list':
        list_specs()
    elif command == 'create':
        project_name = sys.argv[2] if len(sys.argv) > 2 else None
        create_spec(project_name)
    elif command == 'view':
        project_name = sys.argv[2] if len(sys.argv) > 2 else None
        view_spec(project_name)
    elif command == 'edit':
        project_name = sys.argv[2] if len(sys.argv) > 2 else None
        edit_spec(project_name)
    else:
        print(f"ERROR: Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
