# Tenant-Aware Clinic Onboarding: Technical Walkthrough

This guide describes a production-oriented implementation for onboarding many clinics into Valcura without a deployment, database, or `.env` file per clinic. It is an implementation blueprint; it does not claim these changes have already been made.

The recommended first scale target is a **modular Django monolith, shared PostgreSQL database, and shared schema**, with every clinic-owned row scoped by a stable clinic identity. This keeps onboarding and operations manageable while leaving room to partition hot data or move selected enterprise tenants later.

> **Do not use the current alpha as a multi-tenant production system.** The current backend has clinic-linked patient and opportunity records, but `MessageLog` and `WorkflowState` are not clinic-owned; the WhatsApp webhook does not resolve a clinic from the provider account; `/api/messages/` reads all message logs; and staff creation accepts a clinic selection. Complete the isolation and webhook work below before processing real multi-clinic patient data. See [CLINIC_ONBOARDING.md](./Valcura/CLINIC_ONBOARDING.md) for the current alpha procedure and known limitations.

## 1. Define the tenant boundary and architecture

Treat a clinic as the tenant boundary for patient records, messages, workflow state, staff membership, integrations, imports, and reporting. A user can be a member of one or more clinics; a platform operator is a distinct role and must not be represented as an ordinary clinic user.

Use the following initial deployment shape:

```text
Browser/API ── authenticated identity ──> tenant-scoped application services
Meta webhook ── verified provider account ──> clinic integration ──> same services
                                                     │
                                                     ├── PostgreSQL (tenant_id on owned rows)
                                                     ├── Redis (cache/queue; tenant-aware keys)
                                                     └── Secret manager (provider credential references)
```

Keep separate concerns behind clear modules even if they remain in the existing `user_request` Django app at first:

| Responsibility | Suggested module boundary |
|---|---|
| Clinic profile, status, settings | `clinics` |
| Authentication, invitation, membership, roles | `accounts` |
| Patients, opportunities, imports | `patients` |
| Message processing, webhook events, workflow state | `messaging` |
| WhatsApp, Sheets, CRM configuration and adapters | `integrations` |

Do not begin with a database/schema per clinic. That multiplies migrations, connection management, provisioning, reporting, and support work. Revisit dedicated databases only for a clear isolation, residency, contractual, or capacity requirement.

## 2. Establish the current baseline

Before changing the schema:

1. Confirm which database is used in each environment. The backend settings select PostgreSQL using `DATABASE_URL`; local settings also contain a commented SQLite alternative. Never run a production backfill or migration against an unverified database.
2. Take and restore-test a database backup. Record migration state and row counts for clinics, users, patients, messages, and workflow state.
3. Inventory all writes and reads of clinic-owned data, not just dashboard views. In this repository, start with:
   - [models.py](./Valcura_backend/user_request/models.py)
   - [forms.py](./Valcura_backend/user_request/forms.py)
   - [views.py](./Valcura_backend/user_request/views.py)
   - [services.py](./Valcura_backend/user_request/services.py)
   - [google_sheets_service.py](./Valcura_backend/user_request/google_sheets_service.py)
   - [urls.py](./Valcura_backend/Valcura_backend/urls.py)
   - [test_hospital_auth.py](./Valcura_backend/tests/test_hospital_auth.py)
4. Search the codebase for every `MessageLog.objects`, `WorkflowState.objects`, `PatientContact.objects`, and integration service construction. Include management commands, importers, scheduled jobs, and test utilities.
5. Capture a behavior baseline for registration, login, clinic dashboard, staff creation, message listing, inbound WhatsApp, MacroDroid, and Sheets synchronization. Keep the existing single-clinic experience working until a planned cutover.

Use synthetic patient data in development and acceptance testing. Do not copy production patient messages, credentials, or tokens into issue trackers or test fixtures.

## 3. Introduce stable clinic identity and lifecycle state

### 3.1 Make identity independent of the display name

Clinic names can change and are not unique identifiers. Add a generated UUID tenant identifier to `ClinicProfile`; keep the current `clinic_id` temporarily as a compatibility key because other rows currently reference it. Stop generating IDs from the first characters of the clinic name, which can collide.

Example model direction:

```python
import uuid

class ClinicProfile(models.Model):
    clinic_id = models.CharField(max_length=50, unique=True, primary_key=True)  # legacy key
    tenant_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    onboarding_status = models.CharField(max_length=32, default="pending", db_index=True)
    # Existing profile fields remain during the first migration.
```

For new clinics, make the legacy key opaque and collision-resistant (or plan a later primary-key migration); never derive it from `clinic_name`. Use `tenant_id` in new APIs, audit events, queue payloads, and operational tooling. Do not accept a client-supplied tenant ID as proof of authorization.

Use explicit lifecycle transitions, for example:

```text
pending → profile_complete → integration_pending → data_import_pending
        → test_pending → active
active → suspended → active
active/suspended → offboarding → closed
```

Validate transitions in a service layer. A clinic must not become `active` simply because a registration form was submitted.

### 3.2 Use clinic memberships instead of trusting a user-selected clinic

The current `HospitalUser.clinic` field describes one clinic per user. For a scalable authorization model, add a membership table and migrate authorization to it:

```python
class ClinicMembership(models.Model):
    clinic = models.ForeignKey(ClinicProfile, on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    role = models.CharField(max_length=32)
    status = models.CharField(max_length=16, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["clinic", "user"], name="uniq_clinic_user_membership"),
        ]
```

Roles should be explicit and enforced server-side (for example, clinic owner, clinic admin, manager, receptionist, clinician, and platform operator). Define an action-to-role matrix before exposing endpoints. Avoid authorizing with only `is_hospital_admin`; an admin must also have an active membership in the clinic being changed.

Migration sequence:

1. Add the membership table without removing `HospitalUser.clinic`.
2. Backfill one membership for every existing user with a non-null clinic; preserve the current role.
3. Compare row counts and verify users with null clinics or conflicting role data for manual resolution.
4. Switch login/session request context, staff management, and dashboard queries to memberships.
5. Keep `HospitalUser.clinic` as a compatibility field for one release if needed; stop reading it for authorization.
6. Remove the old field only after all application code, jobs, imports, and integrations use memberships.

## 4. Establish tenant ownership on every data model

Every tenant-owned model must have an explicit clinic foreign key. At minimum, add clinic ownership to:

- `MessageLog`
- `WorkflowState`
- provider webhook/idempotency events
- clinic imports and their row-level errors
- clinic-specific integration configuration
- any clinic-specific template mapping, job, export, or audit event

The current `PatientContact`, `Opportunity`, `InteractionLog`, and several other operational models already reference `ClinicProfile`; retain and consistently use those relationships. For models with both a clinic and a parent such as patient or opportunity, validate that the parent belongs to the same clinic.

For phone-based state, change the global uniqueness rule to tenant-scoped uniqueness:

```python
class WorkflowState(models.Model):
    clinic = models.ForeignKey(ClinicProfile, on_delete=models.PROTECT)
    phone_number = models.CharField(max_length=50)
    # workflow fields ...

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["clinic", "phone_number"],
                name="uniq_workflow_state_clinic_phone",
            ),
        ]
        indexes = [
            models.Index(fields=["clinic", "updated_at"]),
        ]
```

Normalize phone numbers to a single canonical format before lookup and uniqueness checks. Prefer a patient foreign key for workflow state when a patient record exists, with phone retained only as a normalized contact key. Do not use a phone number alone to infer which clinic owns historical data.

Add composite indexes based on measured access patterns, typically `(clinic, created_at)` for message timelines and `(clinic, status, next_followup_date_time)` for follow-up queues. Review query plans with realistic tenant sizes before adding many overlapping indexes; each index increases write and storage costs.

## 5. Migrate existing data without guessing tenant ownership

Use an expand/backfill/validate/contract rollout. Do not make a new ownership column non-null until the backfill is reviewed.

### 5.1 Expand

Create additive migrations first:

1. Add `ClinicProfile.tenant_id` and onboarding status.
2. Add nullable clinic references to currently unscoped records (`MessageLog`, `WorkflowState`, and any discovered tables).
3. Add membership, integration, invitation, and webhook-event tables.
4. Add nullable external provider identifiers and idempotency keys as appropriate.
5. Deploy application code that can read old and new representations, but do not yet enable multi-tenant onboarding.

### 5.2 Backfill

Build a one-off management command with dry-run mode, bounded batches, structured counts, and a resumable cursor. For each existing message or workflow row:

1. Resolve ownership only from a reliable source, such as a known clinic-specific integration/account mapping or a stable clinic-owned record with an unambiguous relationship.
2. Write the clinic association and record the reason/source in an audit report.
3. Leave ambiguous rows unassigned and send them to a manual-review report.
4. Never assign a clinic by guessing from a phone number that may exist at multiple clinics.

Do not perform a full-table, long-running update inside a schema migration when tables are large. Run batches outside the migration, monitor locks and replication lag, and make the job safe to retry.

### 5.3 Validate and contract

Before enforcing non-null ownership:

- Compare source and destination counts.
- Confirm every active tenant-owned row has exactly one clinic.
- Check that patient, opportunity, interaction, message, and workflow associations do not cross clinic boundaries.
- Review all unassigned legacy records and decide whether to retain them in a restricted quarantine state or archive/delete them under an approved retention policy.
- Add `NOT NULL`, uniqueness, and foreign-key constraints only after validation.
- Remove compatibility reads in a later release, not in the same deployment that first adds the new columns.

Use separate migration and application deploy steps, with a tested rollback plan. A rollback must not silently erase tenant assignments or newly captured patient data.

## 6. Centralize tenant authorization and query scoping

Create one request/service boundary that resolves an authenticated user's active clinic membership. For a single-clinic portal, select the clinic from the user's active membership. For users with multiple memberships, require an explicit clinic selection from the memberships they are authorized to use and validate it on every request.

Pass a resolved clinic object or typed tenant context into domain services:

```python
def list_messages(*, clinic, filters):
    return MessageLog.objects.filter(clinic=clinic).filter(**filters)
```

Apply these rules consistently:

1. Every tenant-facing read starts from an authorized clinic-scoped queryset.
2. Every create assigns `clinic` from the trusted request/service context, not a posted form field.
3. Every update/delete fetches the object through the authorized clinic queryset, e.g. `MessageLog.objects.filter(clinic=clinic, pk=message_id)`.
4. Every related-object write validates clinic equality for all referenced patient, opportunity, staff, and integration records.
5. Never expose an unrestricted manager/queryset to tenant-facing serializers, exports, dashboard counters, or background tasks.
6. Platform-wide operations use a separate, audited permission path.

Replace the current global `/api/messages/` query with a clinic-scoped endpoint and deny requests without valid clinic membership. Likewise, constrain `create_hospital_user` to the acting admin's clinic; do not bind an arbitrary clinic from POST data. Scope dashboards and APIs by `MessageLog.clinic`, not by collecting patient phone numbers and querying a global message table.

Tenant middleware can attach a validated tenant context for convenience, but middleware is not the security boundary. The service/query layer must still require the clinic scope so management commands, async jobs, and internal callers cannot accidentally skip it.

## 7. Make onboarding private, resumable, and auditable

Replace unrestricted public self-registration with an operator-created clinic or a controlled onboarding request followed by an invitation. The owner invite should:

- Be single-use, short-lived, and bound to a specific clinic, email, and role.
- Store only a cryptographic hash of the token.
- Be invalidated after acceptance, expiry, cancellation, or role change.
- Avoid revealing whether an email address has an account.
- Be rate-limited and audited.

Implement onboarding as an idempotent state machine rather than a single large form submission. Persist each step and its result so an interrupted signup can resume without duplicating clinics or external accounts.

### Recommended user journey

1. **Provision clinic:** A Valcura operator creates a clinic with a generated tenant ID, status `pending`, and an audit event.
2. **Invite owner:** Create an expiring invitation and send a one-time acceptance link. The user verifies the email, sets credentials, and gains an active owner membership.
3. **Collect profile:** Gather clinic display name, address/time zone, languages, specialties, working hours, operational contacts, consent/communication policies, and required regional settings. Keep revenue and staffing analytics optional unless the product requires them.
4. **Connect integrations:** Guide an authorized owner/admin through WhatsApp and optional CRM or Sheets setup. Validate the connection and record a health status.
5. **Import data:** Offer a dry run, field mapping, duplicate preview, consent validation, error report, and retryable import. Make import jobs clinic-scoped and idempotent.
6. **Configure workflows:** Apply versioned platform defaults, then save clinic-specific approved template mappings and workflow preferences as data.
7. **Verify:** Run a test send to an authorized test number; validate inbound routing, event deduplication, and that data appears only in the intended clinic's dashboard.
8. **Activate:** Require all blocking checks to pass before status changes to `active`. Record who approved it and when.
9. **Operate or offboard:** Support pause/resume, credential rotation, data export, retention/deletion workflow, and an audit trail.

The owner may only manage their clinic after activation; platform operators can see setup state across tenants under a separate permission. Show progress and actionable validation errors without exposing secrets or another clinic's identifiers.

## 8. Store per-clinic integrations and secrets safely

Create a `ClinicIntegration` record containing clinic, provider, external account identifier, non-secret configuration, status, health-check timestamps, and a secret-manager reference. Add uniqueness so one external WhatsApp phone-number ID cannot ambiguously resolve to multiple active clinics.

Keep deployment-wide values in environment/hosting configuration (Django secret key, database URL, secret-manager credentials, webhook app secret). Keep per-clinic access tokens, private keys, and refresh tokens in a managed secret store. The database should contain a secret reference, not the raw secret. Never return credentials in forms, API responses, logs, traces, or exception messages.

Refactor `WhatsAppService` and `GoogleSheetsService` so callers pass a clinic integration/configuration object. Remove implicit reads of one global clinic account for tenant-specific actions. Keep a temporary platform default only behind an explicit migration/test mode, with telemetry to show when it is still used.

For Meta WhatsApp onboarding:

1. Use the supported Meta onboarding/authorization flow for the intended business account.
2. Persist the returned business and phone-number account identifiers and map each provider account to exactly one clinic integration.
3. Store tokens in the secret manager; show connection status and masked account identifiers in the clinic UI.
4. Validate permissions and account status before allowing activation.
5. Support token rotation, revocation, provider disconnect, and alerting for expired/revoked credentials.
6. Treat approved templates as platform or clinic configuration with an explicit provider account/template mapping. Do not generate or submit templates based only on clinic name, and do not assume Meta template approval can be bypassed or guaranteed automatically.

## 9. Route webhooks to the correct clinic

The current WhatsApp webhook reads incoming messages but does not scope them to a clinic. Replace that behavior before using one webhook endpoint for multiple tenants.

For Meta Cloud API:

1. Handle the GET verification challenge using the configured verification token; do not log the supplied token.
2. For POST events, validate `X-Hub-Signature-256` against the raw request body using the Meta app secret. A GET verify token alone does not authenticate POST payloads.
3. Parse every entry/change/message in the payload, not just the first message.
4. Extract `value.metadata.phone_number_id` and resolve exactly one active `ClinicIntegration` by provider and external account ID.
5. Reject or quarantine unknown/ambiguous accounts; never fall back to a default clinic.
6. Deduplicate using the provider's stable message/event ID with a database uniqueness constraint. A duplicate delivery should return an appropriate success response without repeating side effects.
7. Create a tenant-owned message/event record and enqueue processing. Acknowledge the provider quickly; do not make a slow Sheets or CRM request before responding.
8. Process retries idempotently and record delivery/processing state.

Apply equivalent authentication and explicit clinic mapping to MacroDroid, Twilio, and any other webhook. A caller-supplied clinic ID or patient phone number is not sufficient proof of tenant ownership.

## 10. Make imports and external side effects scalable

Run bulk imports, message delivery, CRM synchronization, Sheets sync, and webhook follow-up in background jobs rather than holding an HTTP request open. Every job payload should include a stable tenant ID and object/event identifier; the worker must reload and validate the clinic before acting.

For each import:

1. Upload to private, access-controlled storage with size/type limits.
2. Create an import record scoped to the clinic with status and requested-by user.
3. Parse and validate in bounded batches; provide a dry-run preview before writes.
4. Normalize phone numbers, validate consent and required fields, and detect duplicates within the clinic.
5. Use database transactions per bounded batch, not one transaction for an unbounded file.
6. Store row-level failures without copying sensitive patient payloads into general logs.
7. Make retries idempotent using an import ID and source-row identity.
8. Publish a completion summary and permit authorized export of the error report.

For outbound messaging, enforce clinic-level quotas, approved-template/account compatibility, consent checks, rate limits, retries with backoff, and a dead-letter/review path. Queue keys, cache keys, locks, and idempotency keys must include the tenant identity where relevant.

## 11. Scale the shared service safely

Scale the shared PostgreSQL model before introducing per-tenant infrastructure:

- Use pagination and bounded filters for all list endpoints; avoid materializing every patient phone number in Python.
- Add `select_related`/`prefetch_related` only where needed and inspect query counts for dashboard/API paths.
- Track per-tenant row counts, query latency, queue depth, message volume, storage, and error rates.
- Set per-tenant rate and storage limits to prevent noisy-neighbor impact.
- Use a managed connection pooler when application concurrency requires it; size web and worker pools against the database connection limit.
- Use Redis for shared cache/queue only with tenant-aware keys and authorization-safe cached values.
- Keep tenant context in structured logs and traces as a non-secret UUID; do not log patient message bodies or credentials by default.
- Partition very large append-heavy tables (such as message or webhook event records) only after query/retention measurements justify it. Ensure every partition and unique key preserves tenant isolation and idempotency.
- Introduce read replicas for read-heavy analytics only after considering replication lag and keeping writes/authorization-sensitive reads on the primary.
- Define backups, point-in-time recovery, restore drills, encryption, key rotation, retention, deletion, and incident-response ownership.

If PostgreSQL Row-Level Security (RLS) is later added as defense in depth, set tenant context transaction-locally, ensure connection-pool reuse cannot leak context, and test every worker and admin path. RLS does not replace correct application authorization or tested migrations.

## 12. Verify isolation with tests and release gates

Add tests before enabling multi-tenant production traffic. Use at least two clinics and users for each isolation test.

### Authorization and data isolation

- Clinic A cannot list, retrieve, change, delete, export, or count Clinic B's patients, messages, opportunities, interactions, workflow state, imports, or integrations.
- A clinic admin cannot create or invite a user into another clinic by submitting a forged clinic identifier.
- A user with multiple memberships can access only the clinic selected from their authorized memberships.
- Inactive, suspended, expired, or revoked memberships are denied.
- Unauthenticated users cannot call tenant data APIs.
- Platform-wide access requires the explicit operator permission and is audited.

### Webhooks and messaging

- Invalid POST signatures are rejected.
- A valid event maps to the clinic identified by its provider account ID.
- Unknown and ambiguous account IDs are quarantined or rejected, never assigned to a default tenant.
- Duplicate provider event IDs create one logical event and trigger at most one side effect.
- One payload containing multiple messages processes all messages correctly.
- A test send uses only the target clinic's credentials/template mapping.

### Data integrity and onboarding

- UUID generation is stable, unique, and unrelated to display-name edits.
- Workflow state and any per-clinic natural key can repeat across clinics but not within the same clinic.
- A patient or opportunity from Clinic B cannot be attached to a Clinic A operation.
- Invitation expiry, reuse, cancellation, and replay are rejected.
- Failed integration checks or import validation prevent activation.
- Migration tests verify the backfill, ambiguous-row handling, and rollback behavior.

Run the Django checks, focused tests, migration checks, and integration tests against PostgreSQL. SQLite-only tests are not sufficient for PostgreSQL constraints, locking, query plans, or RLS behavior.

## 13. Deploy with an expand-and-contract rollout

Roll out in controlled stages:

1. **Prepare:** Backup and restore-test; baseline metrics; add alerts; confirm support and rollback owners.
2. **Expand schema:** Deploy nullable columns and new tables. Keep old code paths functional.
3. **Deploy compatible code:** Add UUID/membership/integration support, tenant-scoped service APIs, and metrics. Keep new self-service onboarding disabled.
4. **Backfill:** Run resumable tenant assignment and membership jobs in small batches. Review ambiguous records manually.
5. **Enforce:** Add constraints and switch all reads/writes to tenant-scoped services. Remove or deny unscoped message endpoints.
6. **Secure integrations:** Enable signature verification, provider-account routing, idempotency, and clinic-specific secrets. Stop global credential fallback.
7. **Pilot:** Enable invitations and onboarding for internal/synthetic tenants first, then a small clinic cohort with explicit monitoring.
8. **Verify:** Execute cross-tenant acceptance tests and operational checks before processing real data.
9. **Expand:** Increase onboarding volume gradually using activation success, webhook routing, isolation, and error-rate metrics as gates.
10. **Contract:** Remove legacy fields and code only after traffic and job telemetry confirm no remaining consumers.

Feature flags should control onboarding availability and any old-to-new integration fallback. Do not use a feature flag to bypass tenant checks. A rollback must disable new onboarding or processing safely without reopening global data access.

## 14. Production readiness checklist

- [ ] Stable generated tenant ID exists and is not based on clinic name.
- [ ] All clinic-owned records and background jobs carry validated tenant ownership.
- [ ] Membership roles, invitation flow, and platform-operator boundary are enforced server-side.
- [ ] No tenant-facing query or endpoint has an unscoped fallback.
- [ ] Webhook signatures are verified; provider account maps uniquely to an active clinic.
- [ ] Webhook events and jobs are idempotent, retryable, and observable.
- [ ] Clinic secrets are stored outside the database and never logged or returned.
- [ ] Import, activation, suspension, credential rotation, and offboarding are auditable.
- [ ] Cross-tenant negative tests pass on PostgreSQL.
- [ ] Backups, restore, retention/deletion, alerts, rate limits, and incident response are documented and exercised.
- [ ] Alpha limitations in [CLINIC_ONBOARDING.md](./Valcura/CLINIC_ONBOARDING.md) are closed or explicitly gated before real multi-clinic data is enabled.

## 15. Repository implementation order

For this codebase, implement in this order to reduce risk:

1. Add tests that demonstrate cross-clinic leakage in message listing, dashboard queries, user creation, and webhook ingestion.
2. Add tenant UUID, onboarding status, membership, integration, invitation, and webhook-event models with additive migrations.
3. Backfill identities and memberships; report unresolved legacy message/workflow ownership for review.
4. Add clinic-scoped query/service helpers and migrate dashboard, API, staff administration, imports, and automation call sites.
5. Add explicit clinic ownership and tenant-scoped uniqueness to messages and workflow state; make webhook routing resolve from provider account identity.
6. Refactor WhatsApp and Sheets services to use clinic integration configuration and secret references.
7. Implement controlled invitation onboarding, integration checks, dry-run import, workflow setup, test messaging, and activation.
8. Add background processing, idempotency, metrics, and operational limits before increasing onboarding volume.
9. Run PostgreSQL isolation and migration tests; pilot with synthetic/test tenants; then onboard real clinics gradually.
10. Remove alpha compatibility behavior only after verifying no live requests, jobs, or imports depend on it.

See [WORKFLOW.md](./WORKFLOW.md) for repository setup and deployment context. The first implementation milestone should be tenant isolation—not a broader onboarding UI—because every later workflow depends on reliable ownership and authorization.
