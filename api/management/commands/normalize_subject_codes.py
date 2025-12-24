import re
from typing import Optional

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Subject, Topic, Question, Exam


def normalize_code(value: str) -> str:
    """Trim, collapse whitespace to hyphen, and uppercase."""
    return re.sub(r"\s+", "-", value.strip()).upper()


def unique_code(base: str, *, exclude_pk: Optional[str]) -> str:
    """Ensure code is unique by appending -1, -2, ... if needed."""
    code = base
    counter = 1
    while Subject.objects.filter(code=code).exclude(pk=exclude_pk).exists():
        code = f"{base}-{counter}"
        counter += 1
    return code


class Command(BaseCommand):
    help = "Normalize all Subject codes to UPPERCASE-HYPHEN format and update related FKs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Show what would change without applying updates",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]

        with transaction.atomic():
            subjects = Subject.objects.all().order_by("code")
            total = subjects.count()
            changed = 0
            self.stdout.write(self.style.NOTICE(f"Scanning {total} subjects..."))

            for s in subjects:
                current = s.code or s.id
                base_normalized = normalize_code(current)

                # Skip if already normalized and unique
                if (
                    current == base_normalized
                    and not Subject.objects.filter(code=current).exclude(pk=s.pk).exists()
                ):
                    continue

                new_code = unique_code(base_normalized, exclude_pk=s.pk)

                if new_code == s.pk:
                    # Only code needs updating; PK already matches
                    if s.code != new_code:
                        changed += 1
                        if dry_run:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"[DRY] Subject '{s.name}': code {s.code!r} -> {new_code!r}"
                                )
                            )
                        else:
                            s.code = new_code
                            s.save(update_fields=["code"])
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"[OK] Subject '{s.name}': code normalized to {new_code}"
                                )
                            )
                    continue

                # Full rename: update related FKs first, then change subject PK/code
                changed += 1
                old_id = s.pk

                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[DRY] {old_id} -> {new_code} (Subject '{s.name}')"
                        )
                    )
                    continue

                topics_updated = Topic.objects.filter(subject_id=old_id).update(subject_id=new_code)
                questions_updated = (
                    Question.objects.filter(subject_id=old_id).update(subject_id=new_code)
                )
                exams_updated = Exam.objects.filter(subject_id=old_id).update(subject_id=new_code)

                # Update subject PK and code
                s.id = new_code
                s.code = new_code
                # Save without update_fields so the PK change is persisted
                s.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"[RENAMED] {old_id} -> {new_code} | "
                        f"Topics:{topics_updated} Questions:{questions_updated} Exams:{exams_updated}"
                    )
                )

            # Cleanup: delete subjects whose codes contain whitespace
            spaced_subjects = list(Subject.objects.filter(code__regex=r"\s"))
            deleted = 0
            if spaced_subjects:
                self.stdout.write(
                    self.style.NOTICE(
                        f"Cleaning up {len(spaced_subjects)} subjects with whitespace in code..."
                    )
                )
            for spaced in spaced_subjects:
                target_id = normalize_code(spaced.code or spaced.id)
                target = None
                try:
                    target = Subject.objects.get(pk=target_id)
                except Subject.DoesNotExist:
                    try:
                        target = Subject.objects.get(code=target_id)
                    except Subject.DoesNotExist:
                        target = None

                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[DRY][DELETE] Subject '{spaced.name}' ({spaced.pk} | code={spaced.code!r}) "
                            + (f"-> reassign to {target.pk}" if target else "(no target)")
                        )
                    )
                    continue

                if target and target.pk != spaced.pk:
                    Topic.objects.filter(subject_id=spaced.pk).update(subject_id=target.pk)
                    Question.objects.filter(subject_id=spaced.pk).update(subject_id=target.pk)
                    Exam.objects.filter(subject_id=spaced.pk).update(subject_id=target.pk)

                spaced.delete()
                deleted += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[DELETED] Subject '{spaced.name}' ({spaced.pk} | code={spaced.code!r})"
                    )
                )

            if changed == 0 and deleted == 0:
                self.stdout.write(self.style.SUCCESS("No changes needed. All subjects are normalized."))
            else:
                summary_style = self.style.WARNING if dry_run else self.style.SUCCESS
                self.stdout.write(
                    summary_style(
                        f"Done. Changes: {changed}, Deleted: {deleted} (dry_run={dry_run})"
                    )
                )


