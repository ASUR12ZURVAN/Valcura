import uuid

from django.core.management.base import BaseCommand
from django.db import transaction

from user_request.models import (
    ClinicAuditEvent,
    ClinicMembership,
    ClinicProfile,
    HospitalUser,
    MessageLog,
)


class Command(BaseCommand):
    help = (
        "Backfill tenant identities, clinic memberships, and audit legacy unscoped data"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate backfill without committing changes to the database",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Batch size for processing records (default: 100)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        mode_str = "DRY-RUN (No changes will be saved)" if dry_run else "LIVE EXECUTION"
        self.stdout.write(
            self.style.NOTICE(f"=== Tenant Backfill Command [{mode_str}] ===")
        )
        self.stdout.write(f"Batch size: {batch_size}\n")

        stats = {
            "clinics_inspected": 0,
            "clinics_tenant_id_backfilled": 0,
            "memberships_created": 0,
            "memberships_existing": 0,
            "users_unassigned_clinic": 0,
            "messages_inspected": 0,
            "messages_unassigned_quarantined": 0,
        }

        # -------------------------------------------------------------
        # Step 1: ClinicProfile Identity Verification
        # -------------------------------------------------------------
        self.stdout.write("1. Verifying ClinicProfile identities...")
        clinics = ClinicProfile.objects.all().order_by("clinic_id")
        stats["clinics_inspected"] = clinics.count()

        for clinic in clinics:
            needs_save = False
            if not clinic.tenant_id:
                if not dry_run:
                    clinic.tenant_id = uuid.uuid4()
                    needs_save = True
                stats["clinics_tenant_id_backfilled"] += 1

            if not clinic.onboarding_status and not dry_run:
                clinic.onboarding_status = "pending"
                needs_save = True

            if needs_save and not dry_run:
                clinic.save(update_fields=["tenant_id", "onboarding_status"])
                ClinicAuditEvent.objects.create(
                    clinic=clinic,
                    action="backfill_tenant_id",
                    target_type="ClinicProfile",
                    target_id=str(clinic.clinic_id),
                    payload={
                        "tenant_id": str(clinic.tenant_id),
                        "onboarding_status": clinic.onboarding_status,
                    },
                )

        self.stdout.write(
            f"   Clinics checked: {stats['clinics_inspected']}, "
            f"Tenant IDs updated: {stats['clinics_tenant_id_backfilled']}\n"
        )

        # -------------------------------------------------------------
        # Step 2: ClinicMembership Backfill from HospitalUser.clinic
        # -------------------------------------------------------------
        self.stdout.write(
            "2. Backfilling ClinicMembership from HospitalUser records..."
        )
        users = HospitalUser.objects.all().order_by("id")

        # Map existing legacy roles to membership roles
        role_map = {
            "admin": "admin",
            "manager": "manager",
            "receptionist": "receptionist",
            "doctor": "clinician",
        }

        for i in range(0, users.count(), batch_size):
            batch = users[i : i + batch_size]
            with transaction.atomic():
                for user in batch:
                    if not user.clinic:
                        stats["users_unassigned_clinic"] += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"   [WARN] User ID {user.id} ({user.username}) has no associated clinic. Quarantined for review."
                            )
                        )
                        continue

                    # Check if membership already exists
                    existing = ClinicMembership.objects.filter(
                        clinic=user.clinic, user=user
                    ).first()
                    if existing:
                        stats["memberships_existing"] += 1
                        continue

                    target_role = role_map.get(user.role, "receptionist")
                    if user.is_hospital_admin:
                        target_role = "admin"

                    if not dry_run:
                        membership = ClinicMembership.objects.create(
                            clinic=user.clinic,
                            user=user,
                            role=target_role,
                            status="active",
                        )
                        ClinicAuditEvent.objects.create(
                            clinic=user.clinic,
                            actor=user,
                            action="backfill_membership",
                            target_type="ClinicMembership",
                            target_id=str(membership.id),
                            payload={
                                "user_id": user.id,
                                "role": target_role,
                                "status": "active",
                            },
                        )
                    stats["memberships_created"] += 1

                if dry_run:
                    # Roll back any temporary changes in dry run
                    transaction.set_rollback(True)

        self.stdout.write(
            f"   Memberships created: {stats['memberships_created']}, "
            f"Existing: {stats['memberships_existing']}, "
            f"Users with null clinic (quarantined): {stats['users_unassigned_clinic']}\n"
        )

        # -------------------------------------------------------------
        # Step 3: Legacy MessageLog Review & Quarantine
        # -------------------------------------------------------------
        self.stdout.write("3. Inspecting legacy unscoped MessageLog records...")
        messages = MessageLog.objects.filter(clinic__isnull=True).order_by("id")
        stats["messages_inspected"] = messages.count()

        # In Phase 3: Prohibit guessing ownership from phone number alone.
        # Unassigned records without verifiable provider account mapping remain quarantined.
        stats["messages_unassigned_quarantined"] = stats["messages_inspected"]

        self.stdout.write(
            f"   Unscoped MessageLogs found: {stats['messages_inspected']}. "
            f"All {stats['messages_unassigned_quarantined']} quarantined (ownership not inferred from phone alone).\n"
        )

        # -------------------------------------------------------------
        # Summary
        # -------------------------------------------------------------
        self.stdout.write(self.style.SUCCESS("=== Backfill Summary ==="))
        self.stdout.write(f"Mode: {'DRY RUN' if dry_run else 'COMMITTED'}")
        self.stdout.write(f"Total Clinics Inspected: {stats['clinics_inspected']}")
        self.stdout.write(f"Memberships Created: {stats['memberships_created']}")
        self.stdout.write(
            f"Memberships Already Present: {stats['memberships_existing']}"
        )
        self.stdout.write(
            f"Users Needing Review (Null Clinic): {stats['users_unassigned_clinic']}"
        )
        self.stdout.write(
            f"Unscoped MessageLogs Quarantined: {stats['messages_unassigned_quarantined']}"
        )

        if dry_run:
            self.stdout.write(
                self.style.NOTICE(
                    "\nDry run completed successfully. No rows were modified."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "\nBackfill execution completed and committed successfully."
                )
            )
