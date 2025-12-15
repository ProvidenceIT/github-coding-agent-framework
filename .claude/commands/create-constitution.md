---
name: create-constitution
description: Create or update a project constitution with deployment, secrets, and coding standards
tags: [constitution, configuration, governance, standards]
---

# Project Constitution Creation

**Usage:** `/create-constitution [project_name] [--template <template>]`

**Arguments:**
- `project_name` (optional) - Name of the project in `generations/` directory
- `--template` (optional) - Use a preset template: `plesk` (default), `minimal`

**Examples:**
```
/create-constitution serverwatch
/create-constitution serverwatch --template plesk
/create-constitution serverwatch --template minimal
/create-constitution                    # Interactive in current directory
```

---

## Step 0: Resolve Project Context

{{#if $ARGUMENTS}}
**Arguments:** `$ARGUMENTS`

```bash
# Parse arguments
ARGS="$ARGUMENTS"
PROJECT_NAME=$(echo "$ARGS" | awk '{print $1}')
TEMPLATE=$(echo "$ARGS" | grep -oP '(?<=--template\s)\w+' || echo "")

# Set project directory
PROJECT_DIR="./generations/$PROJECT_NAME"

# Check if project exists
if [ -d "$PROJECT_DIR" ]; then
    echo "Found project: $PROJECT_DIR"
else
    echo "ERROR: Project not found at $PROJECT_DIR"
    echo "Available projects:"
    ls -d ./generations/*/ 2>/dev/null | xargs -n1 basename
    exit 1
fi

echo "Project: $PROJECT_NAME"
echo "Template: ${TEMPLATE:-interactive}"
```
{{else}}
**No project specified** - Using current directory.

```bash
PROJECT_DIR="."
PROJECT_NAME=$(basename $(pwd))
TEMPLATE=""
echo "Using current directory: $PROJECT_DIR"
```
{{/if}}

---

## What is a Project Constitution?

A `project_constitution.json` file defines:
- **Deployment rules** - Where and how to deploy
- **Secret naming** - Use organization secrets, naming conventions
- **Coding standards** - Commit format, linting, testing requirements
- **Agent constraints** - How the AI agent should behave
- **TDD requirements** - Test-driven development settings

---

## Option 1: Use a Template

### Template A: Plesk + TDD (ProvidenceIT Standard) - **RECOMMENDED**

Full-featured configuration with Plesk deployment, organization secrets, and TDD with browser verification.

```bash
cat > $PROJECT_DIR/project_constitution.json << 'EOF'
{
  "version": "1.0",
  "name": "ProvidenceIT Standard",
  "description": "Plesk deployment with TDD and browser verification",

  "deployment": {
    "target_environment": "plesk",
    "deployment_host": "hetzner-dedicated.providence.it",
    "ci_cd_provider": "github-actions",
    "required_checks": ["build", "lint", "test", "e2e"]
  },

  "secrets": {
    "naming_convention": "SCREAMING_SNAKE_CASE",
    "use_organization_secrets": true,
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
    "require_tests": true,
    "test_framework": "vitest",
    "linting_required": true,
    "type_checking": true
  },

  "agent_constraints": {
    "max_turns_per_session": 50,
    "mandatory_outcomes": ["close_minimum_1_issue", "update_meta_issue", "push_to_remote"],
    "verify_before_close": true,
    "browser_testing": true
  },

  "tdd": {
    "enabled": true,
    "test_first": true,
    "coverage_minimum": 70,
    "browser_verification": true,
    "mcp_puppeteer": true,
    "verify_endpoints": ["http://localhost:3000/api/health"]
  }
}
EOF
echo "Created Plesk + TDD constitution at $PROJECT_DIR/project_constitution.json"
```

### Template B: Minimal (Defaults Only)

```bash
cat > $PROJECT_DIR/project_constitution.json << 'EOF'
{
  "version": "1.0",
  "name": "Minimal Configuration",
  "description": "Minimal constitution with sensible defaults",

  "deployment": {
    "target_environment": "auto"
  },

  "coding_standards": {
    "commit_format": "conventional",
    "require_tests": false
  },

  "tdd": {
    "enabled": false
  }
}
EOF
echo "Created minimal constitution at $PROJECT_DIR/project_constitution.json"
```

---

## Option 2: Interactive Creation

Answer these questions to create a custom constitution:

### Deployment Configuration
1. What is your deployment target? (plesk/vercel/aws/digitalocean/other)
2. What CI/CD provider do you use? (github-actions/vercel/jenkins/other)
3. What deployment host? (e.g., server.example.com)

### Secrets Configuration
4. Do you use GitHub organization secrets? (yes/no)
5. What prefix for secrets? (e.g., MYORG_, PROD_)
6. What secrets are required? (e.g., DATABASE_URL, API_KEY)

### Coding Standards
7. Commit message format? (conventional/freeform)
8. Require tests? (yes/no)
9. Test framework? (vitest/jest/pytest/auto)

### TDD Configuration
10. Enable TDD mode? (yes/no)
11. Minimum test coverage? (e.g., 70)
12. Require browser verification? (yes/no)

---

## Option 3: Python API

```python
from constitution import create_constitution_template
from pathlib import Path

constitution = create_constitution_template(
    project_dir=Path("$PROJECT_DIR"),
    name="$PROJECT_NAME",
    deployment_target="plesk",           # plesk, vercel, aws, etc.
    organization_prefix="PROVIDENCE_",   # Secret naming prefix
    enable_tdd=True,                     # Enable TDD mode
    browser_testing=False                # Require browser verification
)

print(f"Constitution created: {constitution.constitution_file}")
```

---

## Validating Constitution

After creating, validate it:

```bash
python -c "
from constitution import ProjectConstitution
from pathlib import Path

c = ProjectConstitution(Path('$PROJECT_DIR'))
print('Constitution loaded successfully')
print(f'Name: {c.data.get(\"name\")}')
print(f'TDD Enabled: {c.is_tdd_enabled()}')
print(f'Required Checks: {c.get_required_checks()}')
print(f'Deployment Target: {c.get_deployment().get(\"target_environment\")}')
"
```

---

## Constitution Schema Reference

```json
{
  "version": "1.0",
  "name": "Project Name",
  "description": "Project description",

  "deployment": {
    "target_environment": "plesk|vercel|aws|digitalocean|auto",
    "deployment_host": "server.example.com",
    "ci_cd_provider": "github-actions|vercel|jenkins",
    "required_checks": ["build", "lint", "test", "e2e"]
  },

  "secrets": {
    "naming_convention": "SCREAMING_SNAKE_CASE",
    "use_organization_secrets": true,
    "organization_prefix": "ORG_",
    "required_secrets": ["DATABASE_URL", "API_KEY"],
    "forbidden_patterns": [".*PASSWORD$", ".*_PLAIN$"]
  },

  "coding_standards": {
    "commit_format": "conventional|freeform",
    "require_tests": true,
    "test_framework": "vitest|jest|pytest|auto",
    "linting_required": true,
    "type_checking": true
  },

  "agent_constraints": {
    "max_turns_per_session": 50,
    "mandatory_outcomes": ["close_minimum_1_issue", "update_meta_issue", "push_to_remote"],
    "verify_before_close": true
  },

  "tdd": {
    "enabled": false,
    "test_first": true,
    "coverage_minimum": 70,
    "browser_verification": false,
    "mcp_puppeteer": false,
    "verify_endpoints": []
  }
}
```

---

## Checklist

- [ ] Project directory confirmed
- [ ] Template selected or interactive answers provided
- [ ] Constitution file created
- [ ] Constitution validated
- [ ] Ready for agent to use governance rules
