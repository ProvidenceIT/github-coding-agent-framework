"""
Project Constitution System
===========================

Load, validate, and enforce project governance rules.
Provides structured configuration for deployment, secrets, coding standards, and agent constraints.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime


class ProjectConstitution:
    """
    Load and manage project-specific governance rules.

    Constitution files define:
    - Deployment targets and CI/CD configuration
    - Secret naming conventions and required secrets
    - Coding standards and test requirements
    - Agent behavioral constraints
    - Integration requirements
    """

    DEFAULT_CONSTITUTION = {
        "version": "1.0",
        "name": "Default Constitution",
        "description": "Default project governance rules",

        "deployment": {
            "target_environment": "auto",
            "ci_cd_provider": "github-actions",
            "required_checks": ["build", "lint"]
        },

        "secrets": {
            "naming_convention": "SCREAMING_SNAKE_CASE",
            "use_organization_secrets": True,
            "organization_prefix": "",
            "required_secrets": [],
            "forbidden_patterns": []
        },

        "coding_standards": {
            "commit_format": "conventional",
            "require_tests": True,
            "test_framework": "auto",
            "linting_required": True,
            "type_checking": True
        },

        "agent_constraints": {
            "max_turns_per_session": 50,
            "mandatory_outcomes": [
                "close_minimum_1_issue",
                "update_meta_issue",
                "push_to_remote"
            ],
            "verify_before_close": True,
            "tdd_mode": False,
            "browser_testing": False
        },

        "tdd": {
            "enabled": False,
            "test_first": True,
            "coverage_minimum": 70,
            "browser_verification": False,
            "mcp_puppeteer": False,
            "mcp_devtools": False,
            "verify_endpoints": []
        },

        "integrations": {
            "required_services": [],
            "api_timeout_ms": 30000
        }
    }

    def __init__(self, project_dir: Path):
        """
        Initialize constitution for a project.

        Args:
            project_dir: Path to project directory
        """
        self.project_dir = Path(project_dir)
        self.constitution_file = self.project_dir / "project_constitution.json"
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load constitution from file or return defaults."""
        if self.constitution_file.exists():
            try:
                with open(self.constitution_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Merge with defaults (loaded values override defaults)
                    return self._merge_dicts(self.DEFAULT_CONSTITUTION.copy(), loaded)
            except Exception as e:
                print(f"Warning: Failed to load constitution: {e}")
        return self.DEFAULT_CONSTITUTION.copy()

    def _merge_dicts(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_dicts(result[key], value)
            else:
                result[key] = value
        return result

    def save(self):
        """Save current constitution to file."""
        with open(self.constitution_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2)

    def exists(self) -> bool:
        """Check if constitution file exists."""
        return self.constitution_file.exists()

    # === Section Accessors ===

    def get_deployment(self) -> Dict:
        """Get deployment configuration."""
        return self.data.get('deployment', {})

    def get_secrets(self) -> Dict:
        """Get secrets configuration."""
        return self.data.get('secrets', {})

    def get_coding_standards(self) -> Dict:
        """Get coding standards."""
        return self.data.get('coding_standards', {})

    def get_agent_constraints(self) -> Dict:
        """Get agent behavioral constraints."""
        return self.data.get('agent_constraints', {})

    def get_tdd_config(self) -> Dict:
        """Get TDD configuration."""
        return self.data.get('tdd', {})

    def get_integrations(self) -> Dict:
        """Get integration requirements."""
        return self.data.get('integrations', {})

    # === Validation Methods ===

    def validate_secret_name(self, secret_name: str) -> Tuple[bool, str]:
        """
        Validate a secret name against constitution rules.

        Args:
            secret_name: The secret name to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        rules = self.get_secrets()

        # Check naming convention
        convention = rules.get('naming_convention', 'SCREAMING_SNAKE_CASE')
        if convention == 'SCREAMING_SNAKE_CASE':
            if not re.match(r'^[A-Z][A-Z0-9_]*$', secret_name):
                return False, f"Secret '{secret_name}' must be SCREAMING_SNAKE_CASE"

        # Check forbidden patterns
        for pattern in rules.get('forbidden_patterns', []):
            if re.match(pattern, secret_name):
                return False, f"Secret '{secret_name}' matches forbidden pattern: {pattern}"

        # Check organization prefix if required
        prefix = rules.get('organization_prefix', '')
        if prefix and rules.get('use_organization_secrets', False):
            if not secret_name.startswith(prefix):
                return False, f"Secret '{secret_name}' should start with organization prefix: {prefix}"

        return True, ""

    def validate_commit_message(self, message: str) -> Tuple[bool, str]:
        """
        Validate a commit message against constitution rules.

        Args:
            message: The commit message to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        rules = self.get_coding_standards()
        commit_format = rules.get('commit_format', 'conventional')

        if commit_format == 'conventional':
            # Conventional Commits format: type(scope): description
            pattern = r'^(feat|fix|docs|style|refactor|test|chore|build|ci|perf|revert)(\(.+\))?: .+'
            if not re.match(pattern, message.split('\n')[0]):
                return False, "Commit message must follow Conventional Commits format: type(scope): description"

        return True, ""

    def get_required_checks(self) -> List[str]:
        """Get list of required CI checks before deployment."""
        deployment = self.get_deployment()
        return deployment.get('required_checks', ['build', 'lint'])

    def is_tdd_enabled(self) -> bool:
        """Check if TDD mode is enabled."""
        tdd = self.get_tdd_config()
        return tdd.get('enabled', False)

    def requires_browser_testing(self) -> bool:
        """Check if browser testing is required."""
        tdd = self.get_tdd_config()
        return tdd.get('browser_verification', False)

    # === Prompt Context Generation ===

    def get_prompt_context(self) -> str:
        """
        Generate markdown context to inject into agent prompts.

        Returns:
            Markdown-formatted constitution summary for prompts
        """
        sections = []

        sections.append("## PROJECT CONSTITUTION")
        sections.append("")
        sections.append(f"**Project:** {self.data.get('name', 'Unnamed')}")
        sections.append("")

        # Deployment rules
        deployment = self.get_deployment()
        if deployment.get('target_environment') and deployment['target_environment'] != 'auto':
            sections.append("### Deployment")
            sections.append(f"- **Target:** {deployment['target_environment']}")
            if deployment.get('deployment_host'):
                sections.append(f"- **Host:** {deployment['deployment_host']}")
            if deployment.get('ci_cd_provider'):
                sections.append(f"- **CI/CD:** {deployment['ci_cd_provider']}")
            sections.append("")

        # Secret naming rules
        secrets = self.get_secrets()
        if secrets.get('use_organization_secrets') or secrets.get('required_secrets'):
            sections.append("### Secrets")
            if secrets.get('use_organization_secrets'):
                sections.append("- **Use organization secrets** (not repo-level)")
            if secrets.get('organization_prefix'):
                sections.append(f"- **Prefix:** {secrets['organization_prefix']}")
            if secrets.get('required_secrets'):
                sections.append(f"- **Required:** {', '.join(secrets['required_secrets'])}")
            sections.append("")

        # Coding standards
        standards = self.get_coding_standards()
        sections.append("### Coding Standards")
        sections.append(f"- **Commit format:** {standards.get('commit_format', 'conventional')}")
        if standards.get('require_tests'):
            sections.append(f"- **Tests required:** Yes (framework: {standards.get('test_framework', 'auto')})")
        if standards.get('linting_required'):
            sections.append("- **Linting:** Required before commit")
        sections.append("")

        # TDD configuration
        tdd = self.get_tdd_config()
        if tdd.get('enabled'):
            sections.append("### TDD Requirements")
            sections.append("- **TDD Mode:** ENABLED - Write tests BEFORE implementation")
            if tdd.get('coverage_minimum'):
                sections.append(f"- **Minimum coverage:** {tdd['coverage_minimum']}%")
            if tdd.get('browser_verification'):
                sections.append("- **Browser verification:** Required")
            if tdd.get('mcp_puppeteer'):
                sections.append("- **Use MCP Puppeteer** for browser testing")
            if tdd.get('verify_endpoints'):
                sections.append(f"- **Verify endpoints:** {', '.join(tdd['verify_endpoints'])}")
            sections.append("")

        # Agent constraints
        constraints = self.get_agent_constraints()
        sections.append("### Agent Constraints")
        sections.append(f"- **Max turns:** {constraints.get('max_turns_per_session', 50)}")
        if constraints.get('mandatory_outcomes'):
            sections.append("- **Mandatory outcomes:**")
            for outcome in constraints['mandatory_outcomes']:
                sections.append(f"  - {outcome.replace('_', ' ')}")
        if constraints.get('verify_before_close'):
            sections.append("- **Verify implementation** before closing issues")
        sections.append("")

        return "\n".join(sections)


def create_constitution_template(
    project_dir: Path,
    name: str = "Project Constitution",
    deployment_target: str = None,
    organization_prefix: str = None,
    enable_tdd: bool = False,
    browser_testing: bool = False,
    preset: str = None
) -> ProjectConstitution:
    """
    Create a new constitution file with specified options.

    Args:
        project_dir: Project directory
        name: Project name
        deployment_target: Deployment target (e.g., "plesk", "aws")
        organization_prefix: Secret naming prefix
        enable_tdd: Whether to enable TDD mode
        browser_testing: Whether to require browser testing
        preset: Use a preset configuration ("plesk", "minimal")

    Returns:
        Configured ProjectConstitution instance
    """
    constitution = ProjectConstitution(project_dir)

    # Apply preset if specified
    if preset and preset.lower() == 'plesk':
        # ProvidenceIT Standard: Plesk + TDD + Browser Testing
        constitution.data = {
            "version": "1.0",
            "name": name or "ProvidenceIT Standard",
            "description": "Plesk deployment with TDD and browser verification",
            "created_at": datetime.now().isoformat(),

            "deployment": {
                "target_environment": "plesk",
                "deployment_host": "hetzner-dedicated.providence.it",
                "ci_cd_provider": "github-actions",
                "required_checks": ["build", "lint", "test", "e2e"]
            },

            "secrets": {
                "naming_convention": "SCREAMING_SNAKE_CASE",
                "use_organization_secrets": True,
                "organization_prefix": "",
                "required_secrets": [
                    "SSH_HOST",
                    "SSH_USERNAME",
                    "SSH_PRIVATE_KEY",
                    "SSH_PORT",
                    "SENDGRID_API_KEY"
                ],
                "forbidden_patterns": [".*_PLAIN$", "LOCAL_.*"]
            },

            "coding_standards": {
                "commit_format": "conventional",
                "require_tests": True,
                "test_framework": "vitest",
                "linting_required": True,
                "type_checking": True
            },

            "agent_constraints": {
                "max_turns_per_session": 50,
                "mandatory_outcomes": [
                    "close_minimum_1_issue",
                    "update_meta_issue",
                    "push_to_remote"
                ],
                "verify_before_close": True,
                "browser_testing": True
            },

            "tdd": {
                "enabled": True,
                "test_first": True,
                "coverage_minimum": 70,
                "browser_verification": True,
                "mcp_puppeteer": True,
                "verify_endpoints": ["http://localhost:3000/api/health"]
            },

            "integrations": {
                "required_services": [],
                "api_timeout_ms": 30000
            }
        }
        constitution.save()
        return constitution

    elif preset and preset.lower() == 'minimal':
        # Minimal preset
        constitution.data = {
            "version": "1.0",
            "name": name or "Minimal Configuration",
            "description": "Minimal constitution with sensible defaults",
            "created_at": datetime.now().isoformat(),

            "deployment": {
                "target_environment": "auto"
            },

            "coding_standards": {
                "commit_format": "conventional",
                "require_tests": False
            },

            "tdd": {
                "enabled": False
            }
        }
        constitution.save()
        return constitution

    # Manual configuration (no preset)
    constitution.data['name'] = name
    constitution.data['description'] = f"Constitution for {name}"
    constitution.data['created_at'] = datetime.now().isoformat()

    if deployment_target:
        constitution.data['deployment']['target_environment'] = deployment_target

        # Set common deployment presets
        if deployment_target.lower() == 'plesk':
            constitution.data['deployment']['ci_cd_provider'] = 'github-actions'
            constitution.data['deployment']['required_checks'] = ['build', 'lint', 'test', 'e2e']
            constitution.data['deployment']['deployment_host'] = 'hetzner-dedicated.providence.it'
        elif deployment_target.lower() == 'aws':
            constitution.data['deployment']['ci_cd_provider'] = 'github-actions'

    if organization_prefix:
        constitution.data['secrets']['organization_prefix'] = organization_prefix
        constitution.data['secrets']['use_organization_secrets'] = True

    if enable_tdd:
        constitution.data['tdd']['enabled'] = True
        constitution.data['tdd']['test_first'] = True
        constitution.data['agent_constraints']['verify_before_close'] = True

    if browser_testing:
        constitution.data['tdd']['browser_verification'] = True
        constitution.data['tdd']['mcp_puppeteer'] = True
        constitution.data['agent_constraints']['browser_testing'] = True

    constitution.save()
    return constitution


def load_constitution(project_dir: Path) -> Optional[ProjectConstitution]:
    """
    Load constitution for a project if it exists.

    Args:
        project_dir: Project directory

    Returns:
        ProjectConstitution if exists, None otherwise
    """
    constitution = ProjectConstitution(project_dir)
    if constitution.exists():
        return constitution
    return None
