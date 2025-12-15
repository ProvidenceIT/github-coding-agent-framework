---
name: tdd-workflow
description: Test-Driven Development workflow with browser verification via MCP
tags: [testing, tdd, quality, verification, mcp]
---

# Test-Driven Development Workflow

**Usage:** `/tdd-workflow [project_name] [issue_number]`

**Arguments:**
- `project_name` (optional) - Name of the project in `generations/` directory
- `issue_number` (optional) - GitHub issue number to implement with TDD

**Examples:**
```
/tdd-workflow serverwatch 42
/tdd-workflow serverwatch           # TDD workflow for current issue
/tdd-workflow                       # Uses current project context
```

---

## Step 0: Resolve Project Context

{{#if $ARGUMENTS}}
**Arguments:** `$ARGUMENTS`

```bash
# Parse arguments
ARGS="$ARGUMENTS"
PROJECT_NAME=$(echo "$ARGS" | awk '{print $1}')
ISSUE_NUM=$(echo "$ARGS" | awk '{print $2}')

# Set project directory
PROJECT_DIR="./generations/$PROJECT_NAME"

# Check if project exists
if [ -d "$PROJECT_DIR" ]; then
    echo "Found project: $PROJECT_DIR"
    cd "$PROJECT_DIR"
else
    echo "ERROR: Project not found at $PROJECT_DIR"
    echo "Available projects:"
    ls -d ./generations/*/ 2>/dev/null | xargs -n1 basename
    exit 1
fi

# Load repo info
if [ -f ".github_project.json" ]; then
    REPO=$(cat .github_project.json | jq -r '.repo')
    echo "Repository: $REPO"
else
    echo "ERROR: No .github_project.json found."
    exit 1
fi

# Load constitution TDD settings
if [ -f "project_constitution.json" ]; then
    TDD_ENABLED=$(cat project_constitution.json | jq -r '.tdd.enabled // false')
    COVERAGE_MIN=$(cat project_constitution.json | jq -r '.tdd.coverage_minimum // 70')
    BROWSER_TEST=$(cat project_constitution.json | jq -r '.tdd.browser_verification // false')
    echo "TDD Enabled: $TDD_ENABLED"
    echo "Coverage Minimum: $COVERAGE_MIN%"
    echo "Browser Testing: $BROWSER_TEST"
fi

# If issue number provided, fetch it
if [ -n "$ISSUE_NUM" ]; then
    echo ""
    echo "=== Issue #$ISSUE_NUM ==="
    gh issue view $ISSUE_NUM --repo $REPO
fi
```
{{else}}
**No project specified** - Using current directory.

```bash
PROJECT_DIR="."
REPO=$(cat .github_project.json 2>/dev/null | jq -r '.repo' || echo "")

if [ -z "$REPO" ]; then
    echo "ERROR: No project context. Specify project name:"
    echo "  /tdd-workflow <project_name> [issue_number]"
    exit 1
fi

echo "Repository: $REPO"
```
{{/if}}

---

## TDD Philosophy

**Red-Green-Refactor Cycle:**
1. **RED** - Write a failing test first
2. **GREEN** - Write minimal code to make test pass
3. **REFACTOR** - Improve code while keeping tests green

---

## Step 1: Understand the Requirement

Before writing any code, clarify:
- What is the expected behavior?
- What are the edge cases?
- What are the acceptance criteria?

```bash
# If working on an issue, read it first
gh issue view $ISSUE_NUM --repo $REPO 2>/dev/null || echo "No issue specified - define requirements manually"
```

---

## Step 2: Set Up Test Infrastructure

**For Node.js/TypeScript projects:**
```bash
# Check if test framework exists
cat package.json | grep -E "jest|vitest|mocha" || echo "No test framework found"

# If not installed, add vitest
npm install -D vitest @testing-library/react @testing-library/jest-dom

# Create vitest config if missing
if [ ! -f "vitest.config.ts" ]; then
    cat > vitest.config.ts << 'EOF'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    coverage: {
      reporter: ['text', 'json', 'html'],
    },
  },
})
EOF
fi
```

**For Python projects:**
```bash
# Check for pytest
pip show pytest || pip install pytest pytest-cov
```

---

## Step 3: Write Failing Test (RED Phase)

Create test file **BEFORE** implementation:

### API Endpoint Test Example
```typescript
// tests/api/feature.test.ts
import { describe, it, expect } from 'vitest'

describe('GET /api/feature', () => {
  it('should return expected data', async () => {
    const response = await fetch('http://localhost:3000/api/feature')
    expect(response.status).toBe(200)

    const data = await response.json()
    expect(data).toHaveProperty('id')
    expect(data).toHaveProperty('name')
  })

  it('should handle errors gracefully', async () => {
    const response = await fetch('http://localhost:3000/api/feature/invalid')
    expect(response.status).toBe(404)
  })
})
```

### Component Test Example
```typescript
// tests/components/Feature.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { Feature } from '@/components/Feature'

describe('Feature Component', () => {
  it('renders correctly', () => {
    render(<Feature />)
    expect(screen.getByTestId('feature')).toBeInTheDocument()
  })

  it('handles user interaction', () => {
    const handleClick = vi.fn()
    render(<Feature onClick={handleClick} />)
    fireEvent.click(screen.getByRole('button'))
    expect(handleClick).toHaveBeenCalledOnce()
  })
})
```

**Run test to confirm it fails:**
```bash
npm test -- --run
# Should see FAILING tests (RED)
```

---

## Step 4: Implement Minimal Solution (GREEN Phase)

Write just enough code to make the test pass:

```bash
# Implement the feature
# Keep it simple - minimum viable implementation

# Run tests again
npm test -- --run
# Should see PASSING tests (GREEN)
```

---

## Step 5: Refactor (Optional)

Improve the code while keeping tests green:
- Extract functions
- Improve naming
- Add error handling
- Optimize performance

```bash
# After each refactor, run tests
npm test -- --run
# Must still be GREEN
```

---

## Step 6: Browser Verification

{{#if BROWSER_TEST}}
**Browser testing is REQUIRED by constitution.**
{{/if}}

### Option 1: Simple curl check
```bash
# Test API endpoint
curl -s http://localhost:3000/api/health | jq .

# Test page loads
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
```

### Option 2: MCP Puppeteer (if available)
```bash
# Navigate to page
mcp puppeteer navigate http://localhost:3000

# Take screenshot
mcp puppeteer screenshot ./screenshots/verification.png

# Check element exists
mcp puppeteer evaluate "document.querySelector('.feature').textContent"
```

### Option 3: Playwright E2E
```bash
# Install if needed
npm install -D @playwright/test

# Run E2E tests
npx playwright test --grep "feature"
```

---

## Step 7: Check Coverage

```bash
# Run with coverage
npm test -- --coverage

# Check coverage meets minimum
COVERAGE=$(npm test -- --coverage 2>&1 | grep "All files" | awk '{print $4}' | tr -d '%')
echo "Coverage: $COVERAGE%"

if [ "$COVERAGE" -lt "${COVERAGE_MIN:-70}" ]; then
    echo "WARNING: Coverage below minimum (${COVERAGE_MIN:-70}%)"
fi
```

---

## Step 8: Complete the Issue

If working on a GitHub issue:

```bash
# Add completion comment
gh issue comment $ISSUE_NUM --repo $REPO --body "## TDD Implementation Complete

### Test Coverage
- Coverage: $COVERAGE%
- All tests passing

### Tests Added
- \`tests/api/feature.test.ts\`
- \`tests/components/Feature.test.tsx\`

### Verification
- Unit tests: PASS
- Browser verification: ${BROWSER_TEST:-SKIP}
"

# Close the issue
gh issue close $ISSUE_NUM --repo $REPO
```

---

## TDD Checklist

For each feature:

- [ ] Requirement understood from issue/spec
- [ ] Test file created BEFORE implementation
- [ ] Test fails initially (RED)
- [ ] Minimal implementation written
- [ ] Test passes (GREEN)
- [ ] Code refactored (if needed)
- [ ] All tests still pass
- [ ] Coverage meets minimum ({{COVERAGE_MIN:-70}}%)
- [ ] Browser verification done (if required)
- [ ] Issue closed with TDD summary

---

## Common Test Patterns

### Testing Async Code
```typescript
it('handles async operation', async () => {
  const result = await asyncFunction()
  expect(result).toBe(expected)
})
```

### Testing Errors
```typescript
it('throws on invalid input', () => {
  expect(() => validate(null)).toThrow('Invalid')
})
```

### Testing API Responses
```typescript
it('returns 404 for missing', async () => {
  const res = await fetch('/api/item/999')
  expect(res.status).toBe(404)
})
```

### Mocking Dependencies
```typescript
vi.mock('./database', () => ({
  getItem: vi.fn().mockResolvedValue({ id: 1 })
}))
```

---

## Quick Reference

```bash
# Run all tests
npm test

# Run specific test file
npm test -- tests/api/feature.test.ts

# Run tests in watch mode
npm test -- --watch

# Run with coverage
npm test -- --coverage

# Run E2E tests
npx playwright test
```

---

## Verification Before Closing Issue

```bash
echo "=== TDD VERIFICATION ==="

# 1. All tests pass
npm test -- --run && echo "PASS: Tests" || echo "FAIL: Tests"

# 2. Coverage meets threshold
npm test -- --coverage

# 3. Lint passes
npm run lint 2>/dev/null && echo "PASS: Lint" || echo "SKIP: No lint"

# 4. Build succeeds
npm run build 2>/dev/null && echo "PASS: Build" || echo "SKIP: No build"

echo "=== END VERIFICATION ==="
```
