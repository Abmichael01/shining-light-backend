"""Central policy for which staff profile fields require admin approval.

Two tiers:
  * LOW_RISK_FIELDS  — apply immediately, just audit the change.
  * HIGH_RISK_FIELDS — write to StaffChangeRequest.new_value only; the
                       Staff record stays unchanged until admin approves.

Keep these sets disjoint. A field that is not in either set will be treated
as high-risk by `is_high_risk_field()` — failing closed is safer than
silently applying an unclassified change.
"""

from typing import FrozenSet

HIGH_RISK_FIELDS: FrozenSet[str] = frozenset({
    # Payroll / banking — wrong value = money goes to wrong account.
    'account_name',
    'account_number',
    'bank_name',
    # Identity — name on record must match official documents.
    'surname',
    'first_name',
    'other_names',
    'date_of_birth',
    # Contact channel used for OTP / official comms.
    'phone_number',
})

LOW_RISK_FIELDS: FrozenSet[str] = frozenset({
    'title',
    'nationality',
    'state_of_origin',
    'permanent_address',
    'marital_status',
    'religion',
    'number_of_children_in_school',
    'passport_photo',
})


def is_high_risk_field(field_name: str) -> bool:
    """Return True if changes to this field must be admin-approved before
    they take effect. Unknown fields fall back to high-risk (fail-closed)."""
    if field_name in LOW_RISK_FIELDS:
        return False
    return True
