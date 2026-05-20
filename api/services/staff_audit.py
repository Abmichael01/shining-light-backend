"""
Records staff-initiated changes as StaffChangeRequest rows.

Hybrid approval model:
  * Low-risk profile fields, document changes, and education changes apply
    immediately. We record an audit row (is_gated=False, applied_at=now).
  * High-risk profile fields are diverted by the serializer into pending
    gated requests (is_gated=True, applied_at=null). The serializer creates
    those rows; this module is responsible for notifying admins about them.
"""
from typing import List, Mapping

from django.utils import timezone

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

    A single email notification is sent to admins per call (batching all
    field changes in one save).
    """
    rows = []
    field_summaries = []
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
                is_gated=False,
                applied_at=timezone.now(),
            )
        )
        pretty = field.replace('_', ' ').title()
        field_summaries.append(f"• {pretty}: {old or '(empty)'} → {new or '(empty)'}")

    if rows:
        StaffChangeRequest.objects.bulk_create(rows)
        _notify_admins(staff, '\n'.join(field_summaries), len(rows))
    return len(rows)


def _notify_admins(staff: Staff, summary: str, count: int) -> None:
    """Fire-and-forget admin notification. Imported lazily to keep this
    module import-light and avoid circular imports."""
    try:
        from api.utils.email import send_staff_change_notification
        send_staff_change_notification(staff, summary, change_count=count)
    except Exception as e:
        # Notification is best-effort — never fail the API call because of it.
        print(f"_notify_admins suppressed: {e}")


def record_document_change(
    staff: Staff,
    document: StaffDocument,
    change_type: str,
    old_filename: str = '',
    new_filename: str = '',
) -> StaffChangeRequest:
    """Record a document upload / replace / delete + notify admins."""
    change = StaffChangeRequest.objects.create(
        staff=staff,
        document=document if change_type != 'document_delete' else None,
        change_type=change_type,
        field_name=document.document_type if document else '',
        old_value=old_filename,
        new_value=new_filename,
        is_gated=False,
        applied_at=timezone.now(),
    )
    label = document.get_document_type_display() if document else change_type
    action = {
        'document_upload': 'uploaded',
        'document_replace': 'replaced',
        'document_delete': 'removed',
    }.get(change_type, 'changed')
    _notify_admins(staff, f"• Document {action}: {label}", count=1)
    return change


def record_education_change(
    staff: Staff,
    education: StaffEducation | None,
    change_type: str,
    old_value: str = '',
    new_value: str = '',
    field_name: str = '',
) -> StaffChangeRequest:
    """Record an education record create / update / delete + notify admins.

    For 'education_delete', the FK is left null because the row no longer
    exists. For create/update we keep the FK so admin can deep-link to it.
    """
    change = StaffChangeRequest.objects.create(
        staff=staff,
        education=education if change_type != 'education_delete' else None,
        change_type=change_type,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        is_gated=False,
        applied_at=timezone.now(),
    )
    action = {
        'education_create': 'added a new qualification',
        'education_update': f"updated qualification field '{field_name or 'data'}'",
        'education_delete': 'removed a qualification',
    }.get(change_type, 'changed a qualification')
    detail = new_value or old_value or ''
    summary = f"• Education: {action}{(' — ' + detail) if detail else ''}"
    _notify_admins(staff, summary, count=1)
    return change


def snapshot_staff(staff: Staff) -> dict:
    """Capture the current values of all tracked profile fields."""
    return {field: getattr(staff, field, None) for field in PROFILE_FIELDS_TRACKED}


def notify_admins_of_gated_changes(staff: Staff, gated: List[StaffChangeRequest]) -> None:
    """Send one notification covering all high-risk fields that are now
    pending admin approval. The Staff record was NOT updated for these —
    that only happens when the admin approves.
    """
    if not gated:
        return
    lines = []
    for change in gated:
        pretty = change.field_name.replace('_', ' ').title()
        old = change.old_value or '(empty)'
        new = change.new_value or '(empty)'
        lines.append(f"• {pretty}: {old} → {new}  [awaiting approval]")
    _notify_admins(staff, '\n'.join(lines), len(gated))
