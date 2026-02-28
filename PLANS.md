# ExecPlans

This file defines how to write and maintain execution plans ("ExecPlans") for non-trivial implementation work in this repository.

An ExecPlan should be complete enough that an engineer or coding agent with only the current working tree and the plan can execute the task end-to-end.

## When to Use an ExecPlan

Write an ExecPlan for work that is non-trivial, including:
- multi-file or multi-service changes;
- architectural, schema, or orchestration updates;
- migrations and refactors with risk of regressions;
- tasks likely to span multiple sessions;
- work with meaningful unknowns that require investigation.

Skip ExecPlans for tiny, localized edits that can be completed safely in one short pass.

## Core Requirements

Every ExecPlan must:
- be self-contained and understandable by a newcomer to the codebase;
- describe why the change is needed and what "done" looks like;
- provide exact file paths, commands, and checkpoints to verify progress;
- include validation steps with observable outcomes;
- include rollback/recovery guidance for risky or stateful steps;
- be maintained as a living document as work proceeds.

## Living Document Rules

Keep the plan current during execution.

Required live sections:
- `Progress`: checklist with status updates.
- `Surprises & Discoveries`: unexpected findings and evidence.
- `Decision Log`: tradeoffs and reasoning behind important choices.
- `Outcomes & Retrospective`: what shipped, what did not, and lessons learned.

If direction changes, update the plan before continuing implementation.

## Repo-Specific Additions

Because this repository is instructional, each ExecPlan must also include:
- student-facing learning impact;
- onboarding impact (first-run experience in VS Code/devcontainer);
- docs impact (`README.md`, lesson notes, runbooks);
- commands that are copy-paste friendly for learners.

For infrastructure changes, explicitly call out impacts on:
- `.devcontainer/` setup;
- `docker-compose*.yml`;
- Superset, Airflow, and dbt integration boundaries.

## Recommended Plan Structure

Use the following template and keep section names stable.

```md
# <Short task title>

This ExecPlan is a living document. Update `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` as work advances.

Reference: `PLANS.md` (repository root) for standards.

## Purpose / Big Picture

Explain in plain language:
- what is changing;
- why it matters;
- how users/students will experience the improvement.

## Student Learning Impact

State:
- which lesson(s) this affects;
- what becomes easier or clearer for students;
- any new concept introduced by the implementation.

## Scope

List in-scope and out-of-scope items to avoid drift.

## Progress

- [ ] Investigate current state and constraints
- [ ] Implement core changes
- [ ] Update docs and examples
- [ ] Run validation checks
- [ ] Final review and cleanup

## Surprises & Discoveries

Capture concrete findings with evidence (command output summary, logs, behavior).

- Discovery:
  Evidence:

## Decision Log

Record meaningful decisions and rationale.

- Decision:
  Rationale:
  Date:

## Outcomes & Retrospective

Summarize:
- delivered changes;
- deferred items;
- follow-up recommendations.

## Context and Orientation

Provide enough local orientation that a new contributor can start quickly:
- key files and directories (absolute or repo-relative paths);
- relevant services and environment variables;
- prerequisites and assumptions.

## Plan of Work

Describe phases with intent and expected artifacts.

### Phase 1: Baseline and Design

Detail what to inspect and how to confirm understanding.

### Phase 2: Implementation

List exact edits, files, and integration points.

### Phase 3: Validation and Documentation

List concrete validation commands and expected outcomes.

## Concrete Steps

Include executable commands with working directory and expected results.

Example format:
- Run: `docker compose config`
  Expected: Compose file resolves with no errors.
- Run: `docker compose up -d`
  Expected: required services become healthy.

## Validation and Acceptance

Define acceptance criteria as observable behavior, for example:
- service starts are deterministic;
- first-time setup works from clean checkout;
- docs match real commands;
- learners can complete the intended flow without manual host installs.

## Idempotence and Recovery

Explain:
- how to safely re-run setup steps;
- how to recover from partial failure;
- how to reset state (volumes, caches, generated files) when needed.

## Artifacts and Notes

Record links/paths to:
- logs;
- screenshots;
- test outputs;
- temporary scripts or migrations.

## Interfaces and Dependencies

Document dependencies and contracts this work relies on:
- image tags, ports, env vars, service names;
- data contracts (schemas, parquet conventions, dbt model boundaries);
- expected interaction between Superset, Airflow, and ETL code.
```

## Quality Bar for ExecPlans

A good ExecPlan is executable by someone new to the project, resilient to ambiguity, and explicit about verification.

If a step cannot be validated, the plan is incomplete.
