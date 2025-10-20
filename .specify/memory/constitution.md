<!--
Sync Impact Report
Version: N/A → 1.0.0
Modified Principles:
- Placeholder → I. SQLAlchemy Declarative Source of Truth
- Placeholder → II. Store Layer Transaction Discipline
- Placeholder → III. Migration-First Schema Evolution
- Placeholder → IV. Baseline Sync via Init Scripts
- Placeholder → V. Operational Tooling Guardrails
Added Sections:
- Database Technology Standards
- Development Workflow & Review
Removed Sections:
- None
Templates:
- .specify/templates/plan-template.md ✅
- .specify/templates/spec-template.md ✅
- .specify/templates/tasks-template.md ✅
Follow-ups:
- None
-->

# Replay LLM Call Constitution

## Core Principles

### I. SQLAlchemy Declarative Source of Truth
- All persistent entities MUST live under `src/models/` and subclass `BaseDBModel` to keep primary keys, timestamps, and mixins uniform.
- Column definitions MUST use SQLAlchemy 2.0 typed `Mapped[...]` declarations with explicit nullability that matches `migrations/*.sql` and `initdb/create_tables.sql`.
- Relationships MUST declare `back_populates`, cascades, and soft-delete semantics explicitly so stores can enforce consistency and eager loading.
Rationale: Keeping declarative models as the single schema contract prevents drift between code, migrations, and the running database.

### II. Store Layer Transaction Discipline
- Application code MUST access the database through store classes in `src/stores/`; direct engine or session usage outside this layer is prohibited.
- Stores MUST use `database_session()` for scoped work and wrap multi-step writes in `transaction_manager()` so failures raise `DatabaseException` and roll back atomically.
- Store methods MUST log via `src/core/logger` and commit using the established pattern (`db.add/merge → db.commit → db.refresh`) to guarantee observability and freshness.
Rationale: Centralised transaction management avoids hidden side effects and keeps auditing consistent across services and scripts.

### III. Migration-First Schema Evolution
- Every schema change MUST ship with a sequential, idempotent `.sql` file in `migrations/` following `{version}_{description}.sql` and recorded in `schema_migrations`.
- Teams MUST apply migrations via `scripts/run_migrations.py` and confirm status with `scripts/check_migrations.py` before merging or deploying.
- Each migration MUST be documented in `docs/DATABASE_MIGRATIONS.md`, including intent and safety notes, so operational history stays auditable.
Rationale: Treating migrations as first-class artifacts guarantees reproducible schema evolution across environments.

### IV. Baseline Sync via Init Scripts
- `initdb/create_tables.sql` MUST mirror the schema produced by all migrations and pre-seed `schema_migrations` with the full version list.
- Whenever a migration is added or amended, the init script MUST be updated in the same change set and validated against a fresh database snapshot.
- Bootstrapping flows (`make setup`, Docker entrypoints, manual onboarding) MUST rely on the init script instead of ad-hoc SQL resets.
Rationale: Keeping the baseline synchronized protects new environments from drift and simplifies recovery workflows.

### V. Operational Tooling Guardrails
- CI/CD pipelines and manual checklists MUST run `scripts/check_migrations.py` whenever models, migrations, scripts, or init assets change.
- Operational runbooks MUST call `test_connection()` (directly or via `scripts/check_migrations.py`) before and after applying migrations.
- Migration and store operations MUST emit structured logs through `src/core/logger` so outcomes are traceable in `logs/`.
Rationale: Enforcing operational tooling keeps the database healthy and offers rapid diagnostics when failures occur.

## Database Technology Standards

- PostgreSQL, configured via `settings.database__url`, is the primary datastore; alternate engines are limited to isolated tests and MUST still respect migration tooling.
- SQLAlchemy 2.0 with the pooled engine defined in `src/stores/database.py` is the only approved ORM adapter; new engines require explicit governance approval.
- Connection details, pooling limits, and secrets MUST flow through `src/core/config.Settings`; embedding credentials or engine config in feature code is forbidden.
- Identifier generation MUST reuse existing utilities (for example, `src/utils/snowflake_generator.py`) unless a design document justifies a new strategy.

## Development Workflow & Review

- Pull requests touching `src/models/`, `migrations/`, `scripts/`, or `initdb/` MUST attach evidence of `scripts/check_migrations.py` output and list the migration file names.
- Implementation plans and specifications MUST enumerate migration tasks, baseline updates, and store-layer touchpoints using the `.specify` templates.
- Release checklists MUST include running `scripts/run_migrations.py` against a disposable database followed by `make test` to validate integration.
- Reviewers MUST verify that `docs/DATABASE_MIGRATIONS.md` and any dependent playbooks stay synchronized with the committed migrations.

## Governance

- This constitution supersedes conflicting persistence guidance; maintainers MUST update other docs in the same change when contradictions arise.
- Amendments require a pull request containing the proposal, migration tooling validation evidence, and approval from at least two maintainers responsible for data infrastructure.
- Versioning follows semantic rules: MAJOR for principle rewrites/removals, MINOR for new principles or sections, PATCH for clarifications or typo fixes.
- Compliance reviews occur at least once per quarter; reviewers sample recent migrations to confirm parity between `src/models/`, `migrations`, and `initdb`, and remediation MUST precede any release freeze.

**Version**: 1.0.0 | **Ratified**: 2025-10-20 | **Last Amended**: 2025-10-20
