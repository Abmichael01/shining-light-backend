"""
Records staff-initiated changes as StaffChangeRequest rows so admins can
review what was changed, when, and by whom. Changes apply immediately;
the audit log gives admins approve/rollback control after the fact.
"""
from typing import Iterable, Mapping

from api.models import Staff, StaffChangeRequest, StaffDocument, StaffEducation


PROFILE_FIELDS_TRACKED = (
    'title',
    'surname',
    'first_name',
    'other_names',
    'phone_number',
    'nationality',
    'state_of_origin',
    'date_of_birth',
    'permanent_address',
    'marital_status',
    'religion',
    'number_of_children_in_school',
    'account_name',
    'account_number',
    'bank_name',
)


def _stringify(value) -> str:
    if value is None:
        return ''
    return str(value)


def record_profile_changes(staff: Staff, before: Mapping[str, object], after: Mapping[str, object]) -> int:
    """Emit one StaffChangeRequest per changed profile field.

    `before` and `after` should be dicts keyed by Staff field name. Only the
    fields in PROFILE_FIELDS_TRACKED are recorded — admin sees one row per
    field so they can approve/reject changes independently.
    """
    rows = []
    for field in PROFILE_FIELDS_TRACKED:
        if field not in after:
            continue
        old = _stringify(before.get(field))
        new = _stringify(after.get(field))
        if old == new:
            continue
        rows.append(
            StaffChangeRequest(
                staff=staff,
                change_type='profile_field',
                field_name=field,
                old_value=old,
                new_value=new,
            )
        )
    if rows:
        StaffChangeRequest.objects.bulk_create(rows)
    return len(rows)


def record_document_change(
    staff: Staff,
    document: StaffDocument,
    change_type: str,
    old_filename: str = '',
    new_filename: str = '',
) -> StaffChangeRequest:
    """Record a document upload / replace / delete."""
    return StaffChangeRequest.objects.create(
        staff=staff,
        document=document if change_type != 'document_delete' else None,
        change_type=change_type,
        field_name=document.document_type if document else '',
        old_value=old_filename,
        new_value=new_filename,
    )


def record_education_change(
    staff: Staff,
    education: StaffEducation | None,
    change_type: str,
    old_value: str = '',
    new_value: str = '',
    field_name: str = '',
) -> StaffChangeRequest:
    """Record an education record create / update / delete.

    For 'education_delete', the FK is left null because the row no longer
    exists. For create/update we keep the FK so admin can deep-link to it.
    """
    return StaffChangeRequest.objects.create(
        staff=staff,
        education=education if change_type != 'education_delete' else None,
        change_type=change_type,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
    )


def snapshot_staff(staff: Staff) -> dict:
    """Capture the current values of all tracked profile fields."""
    return {field: getattr(staff, field, None) for field in PROFILE_FIELDS_TRACKED}
