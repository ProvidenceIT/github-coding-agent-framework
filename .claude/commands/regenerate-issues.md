---
name: regenerate-issues
description: Regenerate or expand GitHub issues when backlog is empty or spec changes
tags: [issues, workflow, planning, expansion]
---

# Issue Regeneration Workflow

**Usage:** `/regenerate-issues [project_name]`

**Arguments:**
- `project_name` (optional) - Name of the project in `generations/` directory
- If not provided, uses current directory context

**Example:**
```
/regenerate-issues serverwatch
/regenerate-issues bijbelwijs
/regenerate-issues              # Uses current project context
```

---

## Step 0: Resolve Project Context

{{#if $ARGUMENTS}}
**Project specified:** `$ARGUMENTS`

First, let's resolve the project:

```bash
# Set project directory
PROJECT_DIR="./generations/$ARGUMENTS"

# Check if project exists
if [ -d "$PROJECT_DIR" ]; then
    echo "Found project: $PROJECT_DIR"
else
    echo "ERROR: Project not found at $PROJECT_DIR"
    echo "Available projects:"
    ls -d ./generations/*/ 2>/dev/null | xargs -n1 basename
    exit 1
fi

# Load repo info
if [ -f "$PROJECT_DIR/.github_project.json" ]; then
    REPO=$(cat "$PROJECT_DIR/.github_project.json" | jq -r '.repo')
    echo "Repository: $REPO"
else
    echo "ERROR: No .github_project.json found. Project not initialized."
    exit 1
fi
```
{{else}}
**No project specified** - Using current directory context.

```bash
# Check for .github_project.json in current directory
if [ -f ".github_project.json" ]; then
    REPO=$(cat .github_project.json | jq -r '.repo')
    PROJECT_DIR="."
    echo "Repository: $REPO"
else
    echo "ERROR: No project context. Either:"
    echo "  1. Run from a project directory with .github_project.json"
    echo "  2. Specify project name: /regenerate-issues <project_name>"
    exit 1
fi
```
{{/if}}

---

## When to Use This Command

1. **Backlog Empty** - All issues completed, need new work
2. **Spec Updated** - app_spec.txt has new features not in issues
3. **Phase Transition** - Moving from MVP to Enhancement phase
4. **Quality Improvement** - Existing issues need better descriptions

---

## Step 1: Assess Current State

```bash
# Count open vs closed issues (use --limit 10000 for large projects)
gh issue list --repo $REPO --state all --json state --limit 10000 --jq 'group_by(.state) | .[] | {state: .[0].state, count: length}'

# List recently closed issues
gh issue list --repo $REPO --state closed --limit 20

# Find META issue for progress context
gh issue list --repo $REPO --state open --search "[META]" --json number,title

# Check for open issues (use --limit 10000 for accurate count)
OPEN_COUNT=$(gh issue list --repo $REPO --state open --json number --limit 10000 | jq 'length')
echo "Open issues: $OPEN_COUNT"
```

---

## Step 2: Review Current app_spec.txt

```bash
# Read the specification
cat $PROJECT_DIR/app_spec.txt
```

**Questions to Consider:**
- Are there features in the spec not yet covered by issues?
- Has the spec been updated since initial issue creation?
- Are there new phases (Phase 2, Phase 3) to implement?

---

## Step 3: Choose Regeneration Mode

**Option A: Expand from Spec (New Features)**
- Compare spec features vs existing issues
- Create new issues for uncovered features
- Assign appropriate priority labels

**Option B: Phase Transition**
- Close out Phase 1 issues
- Create Phase 2/3 issues from spec
- Update milestones

**Option C: Issue Improvement**
- Audit existing issues for quality
- Split large issues into smaller ones
- Improve acceptance criteria and test steps

**Option D: Full Regeneration**
- Archive or close existing issues
- Re-read app_spec.txt
- Create fresh issue set (use sparingly)

---

## Step 4: Create New Issues

For each new feature, create an issue:

```bash
gh issue create --repo $REPO \
  --title "[Category] Feature Name" \
  --body "## Description
[What this feature does]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Test Steps
1. Step 1
2. Step 2
3. Verify result

## Technical Notes
[Implementation hints]" \
  --label "priority:medium,functional"
```

---

## Step 5: Update META Issue

After creating new issues:

```bash
META_NUM=$(gh issue list --repo $REPO --search "[META]" --json number -q '.[0].number')

gh issue comment $META_NUM --repo $REPO --body "## Issue Regeneration - $(date +%Y-%m-%d)

**Mode:** [Expansion/Phase Transition/Improvement]
**New Issues Created:** X
**Phase:** [Current phase]

### Summary
[Brief description of what was added]

### New Issue Numbers
- #X: Feature name
- #Y: Feature name
"
```

---

## Issue Templates

### Feature Issue Template
```markdown
## Description
[Clear description of what this feature does]

## User Story
As a [user type], I want to [action] so that [benefit].

## Acceptance Criteria
- [ ] [Specific, testable criterion]
- [ ] [Specific, testable criterion]

## Test Steps
1. [Setup step]
2. [Action step]
3. [Verification step]

## Dependencies
- Depends on: #X (if any)
```

---

## Priority Distribution Guidelines

| Priority | Percentage | Use For |
|----------|-----------|---------|
| urgent | 10-15% | Critical infrastructure, auth, security |
| high | 25-30% | Core features, main user flows |
| medium | 35-40% | Secondary features, enhancements |
| low | 15-20% | Polish, nice-to-haves, optimization |

---

## Quick Commands

```bash
# Check if backlog is empty
gh issue list --repo $REPO --state open --limit 1

# Get issue count by priority (use --limit 10000 for large projects)
gh issue list --repo $REPO --state open --json labels --limit 10000 --jq '[.[] | .labels[].name] | map(select(startswith("priority:"))) | group_by(.) | .[] | {priority: .[0], count: length}'

# Find issues without acceptance criteria (use --limit 10000 for large projects)
gh issue list --repo $REPO --state open --json number,body --limit 10000 --jq '.[] | select(.body | contains("Acceptance Criteria") | not) | .number'
```

---

## Checklist

Before finishing regeneration:

- [ ] All new features from spec have corresponding issues
- [ ] Priority labels are balanced
- [ ] Each issue has clear acceptance criteria
- [ ] Each issue has test steps
- [ ] META issue is updated with regeneration summary
- [ ] No duplicate issues created
