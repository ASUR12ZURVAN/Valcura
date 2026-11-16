# Valcura Multi-Tenant Architecture: 10-Day Execution Plan

**Source:** [`walkthrough.md`](./walkthrough.md)  
**Duration:** 10 working days, organized into six phases  
**Target:** A safe, pilot-ready shared-schema multi-tenant Django application  
**Architecture:** Modular Django monolith, shared PostgreSQL database, explicit clinic ownership, and tenant-scoped application services

## Objective and delivery boundary

Deliver tenant isolation as the first milestone, then add the minimum controlled onboarding and integration workflows needed for a guarded pilot. Existing single-clinic behavior should remain compatible during the expand-and-contract rollout.

This is a 10-working-day target execution sequence, not a promise that unknown operational dependencies can be resolved within that period. The compressed schedule assumes parallel work where tasks are independent; it does not bypass dependencies, safety checks, or release gates. Production launch remains blocked until all release gates below pass. Use synthetic data for development and acceptance testing; do not enable real multi-clinic patient processing before tenant-isolation and webhook gates pass.

### Working assumptions

- The team can access the Django/PostgreSQL environments, run migrations, and obtain an approved backup/restore test.
- A product/operations owner can resolve ambiguous legacy data and approve role, retention, and activation policies.
- Provider accounts, webhook settings, email delivery, queue infrastructure, and a managed secret store are available or have named owners. Where they are not, implement and test the integration boundary without storing secrets in the application database; do not substitute a global credential fallback.
- Days are working days. Parallel review/testing can happen within a day, but dependent schema, backfill, and cutover work remains sequential; extend the schedule if those dependencies cannot safely fit.
- Keep new onboarding behind a feature flag; a feature flag must never bypass authorization or tenant scoping.

## Phase 1 — Baseline and isolation test foundation (Day 1)

### Day 1 — Inventory, safety, and behavior baseline

- Confirm configured database targets for local, test, staging, and production; document how `DATABASE_URL` is selected and prevent accidental production migration execution.
- Record migration state and row counts for clinics, users, patients, messages, and workflow state; arrange a backup and restore test before any data migration.
- Inventory all reads, writes, service constructors, jobs, imports, and tests for clinic-owned data, especially `MessageLog`, `WorkflowState`, `PatientContact`, `HospitalUser`, WhatsApp, and Sheets.
- Capture existing behavior for registration/login, dashboard, staff creation, message listing, webhook ingestion, MacroDroid, and Sheets synchronization.
- Identify environment-specific and global credentials without copying their values into code, logs, tests, or this plan.

**Deliverables:** database/environment checklist; model/query/write inventory; baseline test results; owners and unresolved dependencies.

#### Isolation tests and authorization policy

- Add failing regression tests with two clinics and users for cross-clinic message/dashboard access and forged clinic selection during staff creation.
- Add webhook baseline cases for unknown account routing and duplicate deliveries; record current behavior before fixing it.
- Agree an action-to-role matrix for clinic owner/admin, manager, receptionist, clinician, and platform operator. Define multi-clinic user selection and suspension behavior.
- Establish test-data factories/fixtures using synthetic data and a PostgreSQL-backed test target for database-specific behavior.

**Exit gate:** The current leakage risks are reproducible in tests; database backup/restore is confirmed or migration work is held until it is.

## Phase 2 — Tenant identity and additive schema (Days 2–3)

### Day 2 — Stable clinic identity and lifecycle

- Add a generated immutable UUID `tenant_id` to `ClinicProfile`, retaining the existing `clinic_id` as a compatibility key.
- Add indexed onboarding/lifecycle status with explicit allowed transitions; keep new registrations from activating a clinic implicitly.
- Replace name-derived identifiers for new clinics with opaque, collision-resistant legacy keys.
- Add model and migration tests for UUID uniqueness, stability, and independence from clinic-name changes.

#### Membership, invitation, integration, and audit models

- Add `ClinicMembership` with role/status, timestamps, and a unique clinic-user constraint; keep `HospitalUser.clinic` temporarily.
- Add invitation, `ClinicIntegration`, and audit/event models with clinic ownership and appropriate expiry, uniqueness, and status fields.
- Store only references to managed secrets in integration records; do not create a database field for raw tokens or keys.
- Add indexes and constraints for measured access patterns and unique provider-account mapping.

### Day 3 — Tenant ownership schema expansion

- Add nullable clinic foreign keys to unscoped message, workflow, provider-event, import, and other discovered tenant-owned records.
- Add tenant-scoped workflow uniqueness (clinic plus normalized phone/contact key) while retaining compatibility needed for a safe rollout.
- Generate and review additive migrations; test forward and rollback behavior against PostgreSQL.
- Keep new multi-tenant onboarding disabled while old and new representations coexist.

**Exit gate:** Schema is additive and deployable without guessing ownership; PostgreSQL migration tests pass; no raw integration secrets are persisted.

## Phase 3 — Backfill, authorization, and tenant-scoped data access (Days 4–5)

### Day 4 — Resumable identity and membership backfill

- Implement a dry-run, bounded-batch, resumable management command for stable clinic identities and existing user memberships.
- Preserve existing roles where unambiguous; report users with null clinics or conflicting role data for operator review.
- Emit structured counts and audit references without exposing patient content or credentials.
- Test repeated execution, interruption/resume, and dry-run mode.

#### Legacy message/workflow ownership review

- Implement dry-run ownership resolution only from reliable clinic relationships or verified historical integration/account mappings.
- Assign ownership in bounded, retry-safe batches and record the reason/source; quarantine ambiguous records for manual review.
- Explicitly prohibit assigning ownership from phone number alone.
- Compare source/target counts and produce an unassigned-record report with a retention decision required from the owner.

### Day 5 — Central tenant context and service/query boundaries

- Add a shared authorization helper/service that resolves the active membership and trusted clinic context.
- Require clinic context for domain-service reads/writes; ensure create operations derive clinic from this context, never a submitted clinic ID.
- Validate clinic equality for related patients, opportunities, staff, and integrations.
- Create separate audited authorization for platform-wide operator functions.

#### Migrate tenant-facing application surfaces

- Scope message APIs, dashboard counts/lists, staff administration, imports, exports, and automation/service callers through authorized clinic querysets.
- Remove unrestricted tenant-facing query paths and prevent staff admins from creating users in another clinic.
- Add tests for list/retrieve/update/delete/count/export denial across clinics, inactive memberships, unauthenticated access, and multi-membership selection.
- Check pagination and bounded filtering on list endpoints.

**Exit gate:** Tenant-facing reads and writes have no unscoped fallback; core cross-tenant negative tests pass on PostgreSQL; every uncertain legacy row remains quarantined/unassigned, not guessed.

## Phase 4 — Clinic integrations and webhook isolation (Days 6–7)

### Day 6 — Per-clinic integration configuration and webhook routing

- Implement clinic-scoped integration lookup by provider and external account identifier, with unique active account mapping.
- Refactor WhatsApp and Sheets service construction to require a clinic integration/configuration rather than silently reading global clinic credentials.
- Integrate with the approved secret-manager interface; keep only secret references in the database and mask identifiers in user-visible status.
- Add connection-health and credential-rotation/revocation status handling.

#### Authenticated webhook routing

- Retain GET verification using the configured verification token; validate POST signatures against the raw request body using the app secret.
- Parse all entries, changes, and messages in each payload.
- Resolve each event to exactly one active clinic using the verified provider account ID; reject or quarantine unknown/ambiguous accounts with no default-tenant fallback.
- Add tests for invalid signatures, valid routing, unknown accounts, and ambiguous account mappings.

### Day 7 — Webhook idempotency and asynchronous processing

- Add clinic-owned webhook/event records with a provider event/message ID uniqueness constraint and delivery/processing state.
- Acknowledge valid events quickly; enqueue processing rather than synchronously calling Sheets/CRM.
- Ensure duplicate delivery creates one logical event and triggers at most one side effect; make retries safe.
- Apply equivalent authentication and explicit clinic mapping to MacroDroid, Twilio, and any other active webhook path.

#### Tenant-safe outbound messaging and integration verification

- Require the target clinic integration and approved provider-account/template mapping for outbound sends.
- Enforce consent, clinic quotas, rate limits, retries/backoff, and a dead-letter or review path.
- Make queue payloads and relevant cache, lock, and idempotency keys tenant-aware; workers reload and validate clinic ownership before action.
- Run end-to-end synthetic tests for test send, inbound routing, duplicate delivery, and clinic-specific credentials.

**Exit gate:** No webhook or integration action infers a tenant from a phone number or global default; signature, routing, and idempotency tests pass.

## Phase 5 — Controlled onboarding and data operations (Days 8–9)

### Day 8 — Private invitation and resumable onboarding

- Replace unrestricted public self-registration with operator provisioning or a controlled onboarding request followed by an invitation.
- Implement single-use, short-lived, clinic/email/role-bound invitations; store a cryptographic token hash and invalidate on acceptance, expiry, cancellation, or role change.
- Rate-limit and audit invitation actions; avoid account-existence disclosure.
- Persist onboarding progress so interrupted setup can resume idempotently.

#### Clinic profile, roles, and lifecycle workflow

- Implement profile capture for required operational, time-zone, language, specialty, working-hours, and consent/policy settings.
- Enforce lifecycle transitions from pending through profile, integration, import, and test verification to active; support suspension and offboarding states.
- Ensure only active authorized membership roles can manage clinic setup; platform operators use a distinct audited path.

### Day 9 — Safe import workflow

- Add clinic-scoped import records, private upload constraints, dry-run preview, field mapping, duplicate preview, consent validation, and bounded batch processing.
- Normalize phone numbers; scope duplicate detection to the clinic.
- Make writes transactional per bounded batch and retries idempotent by import/source-row identity.
- Store row-level failures without copying sensitive patient payloads into general logs; provide an authorized error summary/export.

#### Activation checks and operational controls

- Add integration health checks, authorized test send, inbound routing verification, and workflow/template configuration checks.
- Block activation until required profile, integration, import, and test checks pass; record approver and timestamp.
- Add per-tenant rate/storage limits and basic tenant-aware metrics for row counts, latency, queue depth, volume, and errors.
- Document support actions for pause/resume, credential rotation, export, retention/deletion, and audit review.

**Exit gate:** Onboarding is resumable and auditable; failed integration/import/verification prevents activation; import retries do not duplicate records or side effects.

## Phase 6 — Validation, staged rollout, and release decision (Day 10)

### Day 10 — Full isolation and migration verification

- Run Django checks, focused tests, migration tests, and integration tests against PostgreSQL.
- Execute two-clinic negative tests for patients, messages, opportunities, interactions, workflow state, imports, integrations, dashboards, and exports.
- Validate related-object clinic consistency, membership status, invitation expiry/replay, and operator audit behavior.
- Review unresolved legacy rows and approve quarantine, retention, archive, or deletion decisions before enforcing non-null ownership.

#### Staging rehearsal and operational readiness

- Rehearse expand, backfill, validate, and contract steps in staging with a restored/synthetic dataset; measure locks, batch duration, and rollback behavior.
- Validate restore/PITR procedures, alerting, structured logs, secret redaction, rate limits, and queue retry/dead-letter behavior.
- Add required non-null/unique/FK constraints only after ownership validation; keep compatibility fields until telemetry confirms no consumers remain.
- Confirm feature-flag behavior disables new onboarding safely without re-opening unscoped access.

#### Synthetic pilot and go/no-go

- Run end-to-end onboarding for at least two synthetic clinics, including invitation, integration mapping, import, test send, inbound webhook, dashboard visibility, and cross-clinic denial.
- Review success/error metrics, tenant routing, duplicates, support runbooks, and rollback controls with engineering and operations.
- Decide: **go** for a small, explicitly monitored clinic pilot only if every release gate passes; otherwise keep real multi-tenant processing disabled and schedule remediation.
- Record pilot scope, owners, rollback trigger, and follow-up work; defer legacy field/code removal until post-pilot telemetry confirms it is safe.

## Cross-cutting definition of done

- Tenant context is derived from authenticated active membership or a verified provider-account mapping, never trusted from a client-supplied clinic ID.
- Every tenant-owned record, service operation, background job, dashboard, export, and webhook event is scoped to exactly one clinic.
- No ambiguous legacy ownership is guessed; unresolved data remains quarantined and access-restricted.
- Clinic secrets are stored in a managed secret store, and are not returned, logged, or included in test fixtures.
- PostgreSQL-backed cross-tenant negative tests, webhook signature/idempotency tests, and migration/backfill tests pass.
- Activation and pilot are gated by auditable checks; rollback disables new tenant onboarding/processing without restoring global data access.

## Explicitly deferred unless required for the pilot

- Per-clinic database/schema provisioning; the initial target is shared PostgreSQL schema.
- PostgreSQL Row-Level Security, read replicas, table partitioning, or connection-pooler changes absent measured need and a separate review.
- Destructive removal of `HospitalUser.clinic` or other compatibility fields before all application, job, import, and integration consumers have moved.
- Broad onboarding-volume expansion or production use before data ownership, security, restore, and support gates are approved.
