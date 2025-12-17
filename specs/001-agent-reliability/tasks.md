# Tasks: Agent Reliability Improvements

**Input**: Design documents from `/specs/001-agent-reliability/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are included in Phase 2 (Foundational) as the Constitution Check indicates test coverage is required for claim lifecycle logic.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: Repository root (no src/ directory - Python CLI tool)
- Tests in `tests/` directory

---

## Phase 1: Setup ✅ COMPLETE

**Purpose**: Project initialization and test infrastructure

- [x] T001 Create tests/ directory structure at repository root
- [x] T002 Add pytest configuration in pyproject.toml or pytest.ini
- [x] T003 [P] Add configuration constants CLAIM_TTL_MINUTES=30, MAX_NO_ISSUES_ROUNDS=3, PRODUCTIVITY_THRESHOLD=0.1 in github_config.py

---

## Phase 2: Foundational (Blocking Prerequisites) ✅ COMPLETE

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: User stories depend on these shared components

### Tests for Foundational Components

- [x] T004 [P] Create test_claim_lifecycle.py with test stubs for TTL expiration in tests/test_claim_lifecycle.py
- [x] T005 [P] Create test_api_error_handler.py with test stubs for error classification in tests/test_api_error_handler.py
- [x] T006 [P] Create test_outcome_validation.py with test stubs for session outcome validation in tests/test_outcome_validation.py

### Core Data Models

- [x] T007 [P] Create IssueClaim dataclass with ClaimStatus enum per data-model.md in issue_claim_manager.py
- [x] T008 [P] Create APIError dataclass with APISource and RecoveryAction enums per contracts in api_error_handler.py
- [x] T009 [P] Create SessionOutcome and ProductivityMetrics dataclasses per data-model.md in session_state.py
- [x] T010 [P] Create BacklogState dataclass per data-model.md in parallel_agent.py

**Checkpoint**: Foundation ready - user story implementation can now begin ✅

---

## Phase 3: User Story 1 - Issue Claim Lifecycle Management (Priority: P1) MVP ✅ COMPLETE

**Goal**: Properly manage issue claims so multiple agents don't work on the same issue and stale claims don't block the backlog indefinitely.

**Independent Test**: Run 3 parallel sessions and verify no issue is claimed by more than one session, stale claims (older than 30 min) are automatically cleaned up.

### Implementation for User Story 1

- [x] T011 [US1] Add CLAIM_TTL_MINUTES constant to IssueLockManager class in parallel_agent.py
- [x] T012 [US1] Implement _cleanup_stale_claims() method per quickstart Pattern 1 in parallel_agent.py
- [x] T013 [US1] Modify claim_issue() to call _cleanup_stale_claims() before querying GitHub in parallel_agent.py
- [x] T014 [US1] Add failed_at and failure_count fields to claim data structure in parallel_agent.py
- [x] T015 [US1] Modify release_issue() to accept was_closed parameter per quickstart Pattern 2 in parallel_agent.py
- [x] T016 [US1] Implement failure tracking logic - keep failed claims with incremented failure_count in parallel_agent.py
- [x] T017 [US1] Add deprioritization of issues with 3+ failures in claim_issue() issue selection in parallel_agent.py
- [x] T018 [US1] Update _run_single_session() to track issue_num and call release_issue(was_closed=True/False) in parallel_agent.py
- [x] T019 [US1] Add logging for stale claim cleanup and failure tracking in parallel_agent.py
- [ ] T020 [US1] Write unit tests for _cleanup_stale_claims() in tests/test_claim_lifecycle.py
- [ ] T021 [US1] Write unit tests for failure tracking and deprioritization in tests/test_claim_lifecycle.py

**Checkpoint**: User Story 1 complete - stale claims cleaned up, failures tracked, no duplicate claims ✅

---

## Phase 4: User Story 2 - Graceful Termination on Empty Backlog (Priority: P1) ✅ COMPLETE

**Goal**: Agent automatically stops when all issues are completed to avoid wasting compute resources.

**Independent Test**: Deplete the issue backlog and verify agent stops within 3 consecutive rounds of no issues.

### Implementation for User Story 2

- [x] T022 [US2] Add MAX_NO_ISSUES_ROUNDS constant to ParallelAgentManager in parallel_agent.py
- [x] T023 [US2] Add consecutive_no_issues counter to run_parallel() method in parallel_agent.py
- [x] T024 [US2] Modify _run_single_session() to return "NO_ISSUES" string when no issues available in parallel_agent.py
- [x] T025 [US2] Implement termination check per quickstart Pattern 3 in run_parallel() in parallel_agent.py
- [x] T026 [US2] Add "ALL ISSUES COMPLETE - Stopping agent" message on termination in parallel_agent.py
- [x] T027 [US2] Reset counter when any session finds work in parallel_agent.py
- [x] T028 [US2] Add similar termination logic to autonomous_agent_fixed.py main loop in autonomous_agent_fixed.py

**Checkpoint**: User Story 2 complete - agent terminates gracefully on empty backlog ✅

---

## Phase 5: User Story 3 - Accurate Session Outcome Validation (Priority: P1) ✅ COMPLETE

**Goal**: Accurate success/failure reporting so metrics are trustworthy.

**Independent Test**: Run a session that closes an issue and verify outcome is marked as SUCCESS with correct issue numbers.

### Implementation for User Story 3

- [x] T029 [US3] Add issues_worked tracking list to session state in parallel_agent.py
- [x] T030 [US3] Record claimed issue number in issues_worked when claim succeeds in parallel_agent.py
- [x] T031 [US3] Modify check_session_outcomes() signature to accept issues_worked parameter per quickstart Pattern 4 in parallel_agent.py
- [x] T032 [US3] Replace time-based query with issue-specific GitHub state checks in check_session_outcomes() in parallel_agent.py
- [x] T033 [US3] Update SessionOutcome dataclass usage to include issues_worked and issues_closed lists in parallel_agent.py
- [x] T034 [US3] Apply same fix to check_session_mandatory_outcomes() in autonomous_agent_fixed.py
- [x] T035 [US3] Add logging for outcome validation showing specific issues in parallel_agent.py
- [ ] T036 [US3] Write unit tests for issue-specific outcome validation in tests/test_outcome_validation.py

**Checkpoint**: User Story 3 complete - outcomes validated against specific issues worked on ✅

---

## Phase 6: User Story 4 - Claude API Error Recovery (Priority: P2)

**Goal**: Gracefully handle Claude API errors so transient issues don't cascade into total session failures.

**Independent Test**: Simulate API errors and verify appropriate recovery behavior.

### Implementation for User Story 4

- [ ] T037 [P] [US4] Create api_error_handler.py with error classification from contracts in api_error_handler.py
- [ ] T038 [US4] Implement classify_error() function with Claude error codes (400, 401, 429, 500, 529) in api_error_handler.py
- [ ] T039 [US4] Add error handling wrapper in _run_single_session() to catch and classify Claude errors in parallel_agent.py
- [ ] T040 [US4] Implement recovery logic for 401 errors - trigger token rotation in parallel_agent.py
- [ ] T041 [US4] Implement recovery logic for 429/529 errors - wait and retry in parallel_agent.py
- [ ] T042 [US4] Implement recovery logic for 400 errors - mark issue for manual review in parallel_agent.py
- [ ] T043 [US4] Add _mark_issue_blocked() helper for non-recoverable errors in parallel_agent.py
- [ ] T044 [US4] Write unit tests for Claude error classification in tests/test_api_error_handler.py

**Checkpoint**: User Story 4 complete - Claude API errors classified and recovered when possible

---

## Phase 7: User Story 5 - GitHub API Error Classification (Priority: P2)

**Goal**: Clear error messages when GitHub API calls fail with recovery hints.

**Independent Test**: Trigger different GitHub error codes and verify appropriate error messages.

### Implementation for User Story 5

- [ ] T045 [P] [US5] Create GitHubAPIError exception class per quickstart Pattern 5 in github_cache.py
- [ ] T046 [US5] Implement execute_gh_command() wrapper with error classification in github_cache.py
- [ ] T047 [US5] Add classification for 401, 403, 404, 409, 422, 429 errors per research.md in github_cache.py
- [ ] T048 [US5] Update IssueLockManager._get_open_issues() to use execute_gh_command() in parallel_agent.py
- [ ] T049 [US5] Update other gh command calls in parallel_agent.py to use execute_gh_command() in parallel_agent.py
- [ ] T050 [US5] Add error logging with classification details in github_cache.py
- [ ] T051 [US5] Write unit tests for GitHub error classification in tests/test_api_error_handler.py

**Checkpoint**: User Story 5 complete - GitHub errors classified with recovery hints

---

## Phase 8: User Story 6 - Enhanced Session Health Monitoring (Priority: P2)

**Goal**: Detect sessions that are running but unproductive.

**Independent Test**: Observe a session with 50 tool calls but 0 files changed and verify low productivity warning.

### Implementation for User Story 6

- [ ] T052 [US6] Add files_changed and issues_closed parameters to analyze_session_health() in autonomous_agent_fixed.py
- [ ] T053 [US6] Implement calculate_productivity_score() per research.md formula in autonomous_agent_fixed.py
- [ ] T054 [US6] Add productivity warning check (tool_count >= 30 AND score < 0.1) in autonomous_agent_fixed.py
- [ ] T055 [US6] Add productivity_score to session health status dict in autonomous_agent_fixed.py
- [ ] T056 [US6] Add same productivity monitoring to parallel_agent.py analyze_session_health() in parallel_agent.py
- [ ] T057 [US6] Add logging for productivity warnings in both agents in autonomous_agent_fixed.py
- [ ] T058 [US6] Update logging_system.py to track productivity metrics in logging_system.py

**Checkpoint**: User Story 6 complete - productivity warnings generated for unproductive sessions

---

## Phase 9: User Story 7 - GitHub Projects Kanban Integration (Priority: P3)

**Goal**: Visual Kanban board showing issue progress for stakeholders.

**Independent Test**: Create a project board and verify issues move through Todo -> In Progress -> Done columns.

### Implementation for User Story 7

- [ ] T059 [P] [US7] Create github_projects.py with GitHubProjectsManager class per contracts in github_projects.py
- [ ] T060 [US7] Implement get_or_create_project() with gh CLI commands in github_projects.py
- [ ] T061 [US7] Implement add_issue_to_project() with GraphQL mutation in github_projects.py
- [ ] T062 [US7] Implement update_issue_status() with GraphQL mutation in github_projects.py
- [ ] T063 [US7] Implement move_to_in_progress() and move_to_done() helper methods in github_projects.py
- [ ] T064 [US7] Add project metadata storage to .github_project.json per data-model.md in github_projects.py
- [ ] T065 [US7] Integrate project creation into initializer in autonomous_agent_fixed.py
- [ ] T066 [US7] Call move_to_in_progress() when issue is claimed in parallel_agent.py
- [ ] T067 [US7] Call move_to_done() when issue is closed in parallel_agent.py
- [ ] T068 [US7] Implement sync_all_issues() to add existing issues to board in github_projects.py
- [ ] T069 [US7] Add error handling for missing project columns in github_projects.py

**Checkpoint**: User Story 7 complete - project board reflects issue states

---

## Phase 10: User Story 8 - Prompt System Cleanup (Priority: P3)

**Goal**: Reduced prompt redundancy for easier maintenance and fewer tokens.

**Independent Test**: Measure prompt token count before and after consolidation.

### Implementation for User Story 8

- [ ] T070 [P] [US8] Create "Quick Reference" section at top of coding_prompt.md per research.md in prompts/coding_prompt.md
- [ ] T071 [US8] Consolidate --repo mentions into Quick Reference section in prompts/coding_prompt.md
- [ ] T072 [US8] Consolidate turn budgeting explanation into Quick Reference section in prompts/coding_prompt.md
- [ ] T073 [US8] Add concrete issue selection algorithm per research.md in prompts/coding_prompt.md
- [ ] T074 [US8] Implement constitution replacement (not append) logic in prompts.py in prompts.py
- [ ] T075 [US8] Apply same consolidation to initializer_prompt.md in prompts/initializer_prompt.md
- [ ] T076 [US8] Verify prompt token reduction by comparing before/after in prompts.py

**Checkpoint**: User Story 8 complete - prompts consolidated with 20%+ token reduction

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T077 [P] Update CLAUDE.md with new features (TTL, termination, productivity) in CLAUDE.md
- [ ] T078 [P] Run all tests and verify passing in tests/
- [ ] T079 Code review for consistency across parallel_agent.py and autonomous_agent_fixed.py
- [ ] T080 Manual integration test: run parallel agent with 3 sessions
- [ ] T081 Manual edge case test: create stale claim and verify cleanup
- [ ] T082 Manual edge case test: deplete backlog and verify termination
- [ ] T083 Run quickstart.md success verification checklist

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-10)**: All depend on Foundational phase completion
- **Polish (Phase 11)**: Depends on all desired user stories being complete

### User Story Dependencies

| Story | Depends On | Can Run In Parallel With |
|-------|-----------|--------------------------|
| US1 (Claim Lifecycle) | Foundational | None (start first) |
| US2 (Termination) | Foundational | US1 if different files |
| US3 (Outcome Validation) | Foundational | US1, US2 |
| US4 (Claude Errors) | Foundational | US1, US2, US3, US5 |
| US5 (GitHub Errors) | Foundational | US1, US2, US3, US4 |
| US6 (Health Monitoring) | Foundational | US1, US2, US3, US4, US5 |
| US7 (Projects) | Foundational | All others |
| US8 (Prompts) | Foundational | All others |

### Within Each User Story

- Models/dataclasses before services
- Core implementation before integration
- Unit tests after implementation

### Parallel Opportunities

- Phase 1 tasks T001-T003 can run in parallel
- Phase 2 test stubs T004-T006 can run in parallel
- Phase 2 data models T007-T010 can run in parallel
- US4 T037 and US5 T045 can run in parallel (new files)
- US7 T059 and US8 T070 can run in parallel (new files)

---

## Parallel Example: Phase 2 Foundational

```bash
# Launch all test stubs in parallel:
Task: "Create test_claim_lifecycle.py with test stubs in tests/test_claim_lifecycle.py"
Task: "Create test_api_error_handler.py with test stubs in tests/test_api_error_handler.py"
Task: "Create test_outcome_validation.py with test stubs in tests/test_outcome_validation.py"

# Launch all data models in parallel:
Task: "Create IssueClaim dataclass in issue_claim_manager.py"
Task: "Create APIError dataclass in api_error_handler.py"
Task: "Create SessionOutcome dataclass in session_state.py"
Task: "Create BacklogState dataclass in parallel_agent.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1-3 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Claim Lifecycle)
4. Complete Phase 4: User Story 2 (Termination)
5. Complete Phase 5: User Story 3 (Outcome Validation)
6. **STOP and VALIDATE**: Test all P1 stories independently
7. Deploy/demo if ready - this is the MVP!

### Incremental Delivery

1. Setup + Foundational -> Foundation ready
2. Add US1 (Claims) -> Test independently -> Core reliability improved
3. Add US2 (Termination) -> Test independently -> Resource waste eliminated
4. Add US3 (Outcomes) -> Test independently -> MVP complete with accurate metrics
5. Add US4+US5 (Errors) -> Test independently -> Error handling improved
6. Add US6 (Health) -> Test independently -> Monitoring improved
7. Add US7+US8 (Enhancements) -> Test independently -> Full feature complete

---

## Summary

| Phase | Task Count | Description |
|-------|------------|-------------|
| Setup | 3 | Project initialization |
| Foundational | 7 | Core data models and test stubs |
| US1 (Claims) | 11 | Claim lifecycle with TTL |
| US2 (Termination) | 7 | Empty backlog detection |
| US3 (Outcomes) | 8 | Accurate validation |
| US4 (Claude Errors) | 8 | Claude API error recovery |
| US5 (GitHub Errors) | 7 | GitHub API error classification |
| US6 (Health) | 7 | Productivity monitoring |
| US7 (Projects) | 11 | GitHub Projects integration |
| US8 (Prompts) | 7 | Prompt consolidation |
| Polish | 7 | Final validation |
| **Total** | **83** | |

### MVP Scope (P1 Stories Only)

- Tasks T001-T036 (36 tasks)
- Covers: Setup, Foundational, US1, US2, US3
- Delivers: Core reliability improvements

### Full Feature Scope

- Tasks T001-T083 (83 tasks)
- Covers: All 8 user stories plus polish
- Delivers: Complete reliability overhaul with GitHub Projects and prompt optimization
