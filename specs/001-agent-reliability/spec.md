# Feature Specification: Agent Reliability Improvements

**Feature Branch**: `001-agent-reliability`
**Created**: 2025-12-17
**Status**: Draft
**Input**: User description: "Comprehensive improvement plan addressing critical issues discovered through log analysis - issue claiming deadlocks, stale claims, broken outcome validation, missing GitHub Projects integration, and cascading API errors"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Issue Claim Lifecycle Management (Priority: P1)

As an operator running parallel agent sessions, I need the system to properly manage issue claims so that multiple agents don't work on the same issue and stale claims don't block the backlog indefinitely.

**Why this priority**: This is the most critical issue - without proper claim lifecycle management, agents enter infinite reclaim loops (same issue claimed 30+ times) and stale claims block progress entirely. This directly impacts session success rate.

**Independent Test**: Can be fully tested by running 3 parallel sessions and verifying that no issue is claimed by more than one session, and stale claims (older than 30 minutes) are automatically cleaned up.

**Acceptance Scenarios**:

1. **Given** a claimed issue older than 30 minutes, **When** a new session attempts to claim an issue, **Then** the stale claim is automatically released and available for claiming
2. **Given** an issue claimed by session A, **When** session B queries for available issues, **Then** that issue is not included in the available list
3. **Given** a session that fails without closing its issue, **When** the claim is processed, **Then** the claim is marked as failed (not released) with a failure count and timestamp
4. **Given** an issue with 3+ failures, **When** a new session looks for work, **Then** that issue is deprioritized or flagged for manual review

---

### User Story 2 - Graceful Termination on Empty Backlog (Priority: P1)

As an operator, I need the agent to automatically stop when all issues are completed so that it doesn't waste compute resources spinning indefinitely on an empty backlog.

**Why this priority**: Without this, the agent runs for hours producing "No unclaimed issues available" messages, wasting significant API costs and compute time.

**Independent Test**: Can be fully tested by depleting the issue backlog and verifying the agent stops within 3 consecutive rounds of finding no issues.

**Acceptance Scenarios**:

1. **Given** all issues are claimed or closed, **When** all parallel sessions report "NO_ISSUES" for 3 consecutive rounds, **Then** the agent displays "ALL ISSUES COMPLETE - Stopping agent" and terminates gracefully
2. **Given** an empty backlog, **When** a single new issue is created, **Then** the next iteration detects and claims it (counter resets)

---

### User Story 3 - Accurate Session Outcome Validation (Priority: P1)

As an operator reviewing session logs, I need accurate success/failure reporting so that I can trust the metrics and identify actual problems.

**Why this priority**: Current time-based validation marks sessions as "FAILED" even when they successfully closed issues, making metrics unreliable for decision-making.

**Independent Test**: Can be fully tested by running a session that closes an issue and verifying the outcome is marked as SUCCESS.

**Acceptance Scenarios**:

1. **Given** a session that worked on issues #5 and #7, **When** outcome validation runs, **Then** it checks the state of specifically issues #5 and #7 (not a time-based query)
2. **Given** a session that closed 2 of 3 issues worked on, **When** outcome is reported, **Then** it shows "2/3 issues closed" with accurate success count
3. **Given** a session that worked on issues but closed none, **When** outcome validation runs, **Then** it reports failure with specific message about which issues were not closed

---

### User Story 4 - Claude API Error Recovery (Priority: P2)

As an operator, I need the system to gracefully handle Claude API errors so that transient issues don't cascade into total session failures.

**Why this priority**: Content filtering (HTTP 400) and server errors currently crash sessions without recovery, causing lost work. This affects reliability but is less critical than the claim lifecycle issues.

**Independent Test**: Can be fully tested by simulating API errors and verifying appropriate recovery behavior.

**Acceptance Scenarios**:

1. **Given** a content filtering error from the Claude API, **When** the error is caught, **Then** the issue is marked as requiring manual review and the session continues with other work
2. **Given** an authentication error (401), **When** the error is caught, **Then** the system attempts token rotation and retries once
3. **Given** a server error (500), **When** the error is caught, **Then** the system waits 30 seconds and retries once

---

### User Story 5 - GitHub API Error Classification (Priority: P2)

As an operator, I need clear error messages when GitHub API calls fail so that I can understand what went wrong and whether it's recoverable.

**Why this priority**: Currently GitHub 401/403/409 errors are not distinguished, making troubleshooting difficult.

**Independent Test**: Can be fully tested by triggering different GitHub error codes and verifying appropriate error messages and recovery hints.

**Acceptance Scenarios**:

1. **Given** a GitHub 401 error, **When** displayed to user, **Then** message indicates "Authentication failed - check gh auth status" and is marked as non-recoverable
2. **Given** a GitHub 429 rate limit error, **When** encountered, **Then** message indicates "Rate limited - waiting" and is marked as recoverable
3. **Given** a GitHub 409 conflict error, **When** encountered, **Then** message indicates "Conflict - may need to pull latest" and is marked as recoverable

---

### User Story 6 - Enhanced Session Health Monitoring (Priority: P2)

As an operator monitoring agent sessions, I need to detect sessions that are running but unproductive so that I can intervene before wasting resources.

**Why this priority**: Current health checks detect stopped sessions but miss "busy but unproductive" sessions (high tool count, no files changed).

**Independent Test**: Can be fully tested by observing a session with 50 tool calls but 0 files changed and verifying a low productivity warning is generated.

**Acceptance Scenarios**:

1. **Given** a session with 30+ tool calls and 0 files changed, **When** health is analyzed, **Then** a "Low productivity" warning is generated
2. **Given** a session with 20 tool calls and 5 files changed, **When** health is analyzed, **Then** productivity is rated as healthy
3. **Given** productivity metrics, **When** displayed, **Then** show a productivity score (ratio of outcomes to effort)

---

### User Story 7 - GitHub Projects Kanban Integration (Priority: P3)

As a stakeholder, I need a visual Kanban board showing issue progress so that I can track project status without reading logs.

**Why this priority**: This is a visibility enhancement that improves stakeholder experience but doesn't affect core agent functionality.

**Independent Test**: Can be fully tested by creating a project board and verifying issues move through Todo → In Progress → Done columns.

**Acceptance Scenarios**:

1. **Given** a repository, **When** initialization runs, **Then** a GitHub Project board is created and linked to the repository
2. **Given** a session claims an issue, **When** work begins, **Then** the issue moves to "In Progress" column on the board
3. **Given** a session closes an issue, **When** the issue is closed, **Then** it moves to "Done" column on the board
4. **Given** all existing issues, **When** the project is initialized, **Then** all open issues are added to the board in "Todo" column

---

### User Story 8 - Prompt System Cleanup (Priority: P3)

As a maintainer, I need reduced prompt redundancy so that prompts are easier to maintain and don't waste tokens on repeated information.

**Why this priority**: This is a maintenance improvement - prompts work but are verbose with `--repo` mentioned 15+ times and turn budgeting explained 4+ times.

**Independent Test**: Can be fully tested by measuring prompt token count before and after consolidation.

**Acceptance Scenarios**:

1. **Given** the consolidated prompt, **When** compared to original, **Then** core information appears once in a "Quick Reference" section
2. **Given** a constitution with TDD settings, **When** prompt is generated, **Then** constitution TDD section replaces (not appends to) the base prompt TDD section
3. **Given** vague issue selection guidance, **When** replaced, **Then** a concrete algorithm with size estimation and priority ordering is provided

---

### Edge Cases

- What happens when multiple sessions try to clean up the same stale claim simultaneously? (Use atomic file locking to serialize cleanup operations)
- How does the system handle a GitHub API outage during claim release? (Log the failure and leave claim in place; TTL cleanup will handle it next round)
- What happens when the Claude API returns an unexpected error code not in the handler list? (Fall through to generic error handling with full error message logged)
- How does graceful termination behave if one session finds an issue but others don't? (Reset the no-issues counter - only terminate when ALL sessions report no issues)
- What happens when a GitHub Project has been manually modified (columns renamed/removed)? (Detect missing columns and recreate them, or warn operator)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST expire issue claims older than a configurable TTL (default 30 minutes)
- **FR-002**: System MUST track failed claim attempts with timestamp and failure count
- **FR-003**: System MUST prevent the same issue from being claimed by multiple concurrent sessions
- **FR-004**: System MUST stop automatically after N consecutive rounds (default 3) where all sessions report no available issues
- **FR-005**: System MUST validate session outcomes by checking specific issues worked on, not time-based queries
- **FR-006**: System MUST classify Claude API errors into recoverable and non-recoverable categories
- **FR-007**: System MUST classify GitHub API errors with specific error codes and recovery hints
- **FR-008**: System MUST calculate a productivity score based on outcomes (issues closed, files changed) divided by effort (tool calls)
- **FR-009**: System MUST warn when productivity score falls below threshold for sessions with significant activity
- **FR-010**: System MUST create and link a GitHub Project board during repository initialization
- **FR-011**: System MUST update issue status on the project board when issues are claimed, worked on, or closed
- **FR-012**: System MUST consolidate repeated prompt content into a single reference section
- **FR-013**: System MUST merge constitution settings by replacement (not append) for conflicting sections
- **FR-014**: System MUST provide a concrete issue selection algorithm with size estimation

### Key Entities

- **Issue Claim**: Represents a session's lock on an issue - includes session ID, issue number, claimed timestamp, optional failure timestamp, failure count
- **Session Outcome**: Represents the result of a session - includes issues worked on, issues closed, files changed, tool count, productivity score, success/failure status
- **GitHub Project Item**: Represents an issue's presence on a Kanban board - includes item ID, issue number, current status column
- **API Error**: Represents a classified error from external APIs - includes error code, message, recoverable flag, suggested action

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Session success rate increases from ~70% to 95% or higher (measured by issues closed when work was attempted)
- **SC-002**: Zero issue reclaim loops occur (same issue claimed by same session more than once per round)
- **SC-003**: Agent terminates within 5 minutes of backlog depletion (instead of running for hours)
- **SC-004**: Stale claims are automatically cleaned up within the TTL window
- **SC-005**: All API errors are classified with appropriate recovery guidance
- **SC-006**: Productivity warnings are generated for sessions with 30+ tool calls and no visible output
- **SC-007**: Project board accurately reflects current issue states within 1 minute of state changes
- **SC-008**: Prompt token count reduces by at least 20% through redundancy elimination

## Assumptions

- The GitHub CLI (`gh`) is properly authenticated and has necessary permissions for Projects v2 GraphQL API
- Sessions operate within a single repository context (multi-repo support out of scope)
- The 30-minute claim TTL is appropriate for typical issue complexity (configurable for different use cases)
- Token rotation mechanism exists and is functional (only needs to be invoked on auth errors)
- File-based locking mechanism is sufficient for claim coordination (distributed locking out of scope)
- Productivity scoring thresholds (30 tools, 0.1 ratio) are reasonable starting points that can be tuned
