"""
AI Skills: Data Retrieval (Secure RBAC)

Allows the AI to fetch real-time data with strict permission checks.
- Admins/Staff: Full access to summaries and listings.
- Students: Restricted to specific models and OWN data only.
"""

from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List, Optional
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models, transaction
from django.db.models import Count, Sum, Avg, Q
from api.models import (
    AIActionLog, Student, BioData, Staff, FeeType, FeePayment,
    Exam, Question, School, Session,
    Class, Subject, Department, SessionTerm
)
from api.services.ai.message_drafts import create_ai_message_draft
from api.models.scheduling.timetable import TimetableEntry
from api.models.scheduling.attendance import StudentAttendance

# Full whitelist for Admins
ADMIN_MODELS = {
    "students": Student,
    "staff": Staff,
    "fee_types": FeeType,
    "fee_payments": FeePayment,
    "exams": Exam,
    "questions": Question,
    "schools": School,
    "sessions": Session,
    "classes": Class,
    "subjects": Subject,
    "departments": Department,
    "timetables": TimetableEntry,
}

# Restricted whitelist for Students
STUDENT_MODELS = {
    "subjects": Subject,
    "timetables": TimetableEntry,
    "exams": Exam,
    "attendance": StudentAttendance,
    "sessions": Session,
    "my_profile": Student, # Their own student record
}

EDITABLE_ADMIN_MODELS = {
    **ADMIN_MODELS,
    "student_biodata": BioData,
}

MODEL_ALIASES = {
    "student": "students",
    "students": "students",
    "student_record": "students",
    "staff_member": "staff",
    "staff": "staff",
    "fee": "fee_types",
    "fees": "fee_types",
    "fee_type": "fee_types",
    "fee_types": "fee_types",
    "payment": "fee_payments",
    "payments": "fee_payments",
    "fee_payment": "fee_payments",
    "fee_payments": "fee_payments",
    "exam": "exams",
    "exams": "exams",
    "question": "questions",
    "questions": "questions",
    "school": "schools",
    "schools": "schools",
    "session": "sessions",
    "sessions": "sessions",
    "class": "classes",
    "classes": "classes",
    "subject": "subjects",
    "subjects": "subjects",
    "department": "departments",
    "departments": "departments",
    "timetable": "timetables",
    "timetables": "timetables",
    "biodata": "student_biodata",
    "bio_data": "student_biodata",
    "student_biodata": "student_biodata",
}

PROTECTED_EDIT_FIELDS = {
    "id",
    "pk",
    "created_at",
    "updated_at",
    "created_by",
    "reviewed_by",
    "approved_by",
    "sent_by",
}

def get_allowed_model(model_name: str, user: Any) -> Optional[Any]:
    """Check if the user has permission to access this model."""
    user_type = getattr(user, 'user_type', 'unknown')
    
    if user_type in ['admin', 'staff']:
        return ADMIN_MODELS.get(model_name)
    
    if user_type == 'student':
        return STUDENT_MODELS.get(model_name)
    
    return None

def apply_student_privacy(model_name: str, queryset: Any, user: Any) -> Any:
    """Ensure students only see their own data for relevant models."""
    if not user or user.user_type != 'student':
        return queryset
    
    student = getattr(user, 'student_profile', None)
    if not student:
        return queryset.none() # No profile, no data

    # Row-level security for students
    if model_name == "my_profile":
        return queryset.filter(id=student.id)
    if model_name == "attendance":
        return queryset.filter(student=student)
    if model_name == "exams":
        # Students can only see exams for their class
        return queryset.filter(class_model=student.class_model)
    if model_name == "timetables":
        return queryset.filter(class_model=student.class_model)
    
    return queryset

def normalize_model_name(model_name: str) -> str:
    """Normalize AI/user model names to registry keys."""
    key = (model_name or "").strip().lower().replace("-", "_").replace(" ", "_")
    return MODEL_ALIASES.get(key, key)

def get_editable_admin_model(model_name: str) -> Optional[Any]:
    return EDITABLE_ADMIN_MODELS.get(normalize_model_name(model_name))

def resolve_admin_record(model_name: str, record_id: Any) -> Any:
    """Resolve a record by primary key, with student-friendly ID fallbacks."""
    normalized = normalize_model_name(model_name)
    model = get_editable_admin_model(normalized)
    if not model:
        raise ValueError(f"'{model_name}' is not editable from chat.")

    lookup_value = str(record_id).strip()
    if not lookup_value:
        raise ValueError("record_id is required.")

    if normalized == "students":
        record = model.objects.filter(
            Q(pk=lookup_value) |
            Q(application_number__iexact=lookup_value) |
            Q(admission_number__iexact=lookup_value)
        ).first()
        if record:
            return record

        loose_matches = list(
            model.objects.filter(
                Q(pk__icontains=lookup_value) |
                Q(application_number__icontains=lookup_value) |
                Q(admission_number__icontains=lookup_value) |
                Q(biodata__surname__icontains=lookup_value) |
                Q(biodata__first_name__icontains=lookup_value) |
                Q(biodata__other_names__icontains=lookup_value)
            ).distinct()[:3]
        )
        if len(loose_matches) == 1:
            return loose_matches[0]
        if len(loose_matches) > 1:
            raise ValueError(
                f"More than one student matched '{record_id}'. Ask for the exact student ID."
            )
        raise model.DoesNotExist()

    if normalized == "student_biodata":
        # Allow resolving biodata by student ID (STU-xxxx, APP-xxxx, adm-xxxx)
        student = Student.objects.filter(
            Q(pk=lookup_value) |
            Q(application_number__iexact=lookup_value) |
            Q(admission_number__iexact=lookup_value)
        ).first()
        if student:
            try:
                return student.biodata
            except ObjectDoesNotExist:
                # If biodata doesn't exist, we return a new unsaved instance 
                # so update_record_fields can prepare it.
                return BioData(student=student)

    return model.objects.get(pk=lookup_value)

def record_label(record: Any) -> str:
    if isinstance(record, Student):
        return f"Student {record.pk} ({record.get_full_name()})"
    if isinstance(record, BioData):
        return f"Student {record.student_id} biodata ({record})"
    return f"{record._meta.verbose_name.title()} {record.pk} ({record})"

def is_field_editable(field: Any) -> bool:
    if getattr(field, "name", "") in PROTECTED_EDIT_FIELDS or getattr(field, "primary_key", False):
        return False
    if getattr(field, "auto_created", False):
        return False
    if isinstance(field, (models.FileField, models.ManyToManyField)):
        return False
    return getattr(field, "editable", True)

def get_editable_field(model: Any, field_name: str) -> Any:
    safe_name = (field_name or "").strip()
    if not safe_name:
        raise ValueError("Field name is required.")
    if safe_name in PROTECTED_EDIT_FIELDS:
        raise ValueError(f"'{safe_name}' cannot be edited from chat.")
    try:
        field = model._meta.get_field(safe_name)
    except Exception:
        # Allow admins/AI to pass a ForeignKey attname such as class_model_id.
        for candidate in model._meta.fields:
            if getattr(candidate, "attname", None) == safe_name:
                field = candidate
                break
        else:
            raise ValueError(f"'{safe_name}' is not a field on {model._meta.verbose_name}.")
    if not is_field_editable(field):
        raise ValueError(f"'{safe_name}' cannot be edited from chat.")
    return field

def serialize_field_value(instance: Any, field: Any) -> Any:
    raw_value = getattr(instance, field.attname if isinstance(field, models.ForeignKey) else field.name)
    if hasattr(raw_value, "isoformat"):
        return raw_value.isoformat()
    if isinstance(raw_value, Decimal):
        return str(raw_value)
    return raw_value

def display_field_value(instance: Any, field: Any, value: Any = None) -> str:
    if value is None:
        value = serialize_field_value(instance, field)
    if isinstance(field, models.ForeignKey):
        related = field.remote_field.model.objects.filter(pk=value).first()
        return str(related) if related else str(value)
    if value in (None, ""):
        return "blank"
    return str(value)

def coerce_field_value(field: Any, value: Any) -> Any:
    if isinstance(field, models.ForeignKey):
        related_pk = field.target_field.to_python(value)
        if not field.remote_field.model.objects.filter(pk=related_pk).exists():
            raise ValueError(f"No {field.remote_field.model._meta.verbose_name} found with ID '{value}'.")
        return related_pk
    return field.to_python(value)

def set_field_value(instance: Any, field: Any, value: Any) -> None:
    coerced_value = coerce_field_value(field, value)
    if isinstance(field, models.ForeignKey):
        setattr(instance, field.attname, coerced_value)
    else:
        setattr(instance, field.name, coerced_value)

def split_full_name(full_name: str) -> Dict[str, str]:
    parts = [part for part in str(full_name).strip().split() if part]
    if len(parts) < 2:
        raise ValueError("Student full name should include at least surname and first name.")
    return {
        "surname": parts[0],
        "first_name": parts[1],
        "other_names": " ".join(parts[2:]),
    }

def build_record_change(model_name: str, record: Any, field_name: str, new_value: Any) -> Dict[str, Any]:
    normalized = normalize_model_name(model_name)
    model = get_editable_admin_model(normalized)
    field = get_editable_field(model, field_name)
    old_value = serialize_field_value(record, field)
    coerced_value = coerce_field_value(field, new_value)
    new_payload_value = coerced_value.isoformat() if hasattr(coerced_value, "isoformat") else (
        str(coerced_value) if isinstance(coerced_value, Decimal) else coerced_value
    )
    return {
        "target_model": normalized,
        "record_id": str(record.pk),
        "field": field.name,
        "field_label": str(field.verbose_name).title(),
        "expected_old_value": old_value,
        "old_display": display_field_value(record, field, old_value),
        "new_value": new_payload_value,
        "new_display": display_field_value(record, field, new_payload_value),
    }

def validate_record_changes(changes: List[Dict[str, Any]]) -> None:
    staged_records = {}
    for change in changes:
        key = (change["target_model"], str(change["record_id"]))
        if key not in staged_records:
            staged_records[key] = resolve_admin_record(change["target_model"], change["record_id"])
        record = staged_records[key]
        field = get_editable_field(record.__class__, change["field"])
        set_field_value(record, field, change["new_value"])

    for record in staged_records.values():
        record.full_clean()

def get_data_summary(model_name: str = "", filters: Dict[str, Any] = None, user: Any = None) -> Dict[str, Any]:
    """Fetch counts and basic stats for a model with RBAC."""
    if not model_name:
        return {"error": "model_name is required."}
    model = get_allowed_model(model_name, user)
    if not model:
        return {"error": f"Access to model '{model_name}' is restricted or not found."}
    
    queryset = model.objects.all()
    queryset = apply_student_privacy(model_name, queryset, user)
    
    # Apply simple filters if provided (sanitize to avoid deep traversal)
    if filters:
        try:
            queryset = queryset.filter(**filters)
        except Exception as e:
            return {"error": f"Invalid filter: {str(e)}"}
    
    count = queryset.count()
    
    extra = {}
    if model_name == "fee_payments" and user.user_type in ['admin', 'staff']:
        extra["total_amount"] = float(queryset.aggregate(Sum('amount'))['amount__sum'] or 0)
    elif model_name == "students" and user.user_type in ['admin', 'staff']:
        extra["by_status"] = list(queryset.values('status').annotate(count=Count('id')))

    return {
        "model": model_name,
        "total_count": count,
        "extra_stats": extra,
        "filter_applied": filters or "none"
    }

def list_records(model_name: str = "", limit: int = 5, filters: Dict[str, Any] = None, user: Any = None) -> List[Dict[str, Any]]:
    """List recent records for a model with RBAC."""
    if not model_name:
        return [{"error": "model_name is required."}]
    model = get_allowed_model(model_name, user)
    if not model:
        return [{"error": "Restricted"}]
    
    queryset = model.objects.all()
    queryset = apply_student_privacy(model_name, queryset, user)
    
    if filters:
        queryset = queryset.filter(**filters)
        
    limit = min(limit, 10 if user.user_type == 'student' else 20)
    
    # Ordering logic
    for field in ['created_at', 'enrollment_date', 'date', 'start_time']:
        if hasattr(model, field):
            queryset = queryset.order_by(f'-{field}')
            break
            
    records = list(queryset.values()[:limit])
    
    # Cleanup for JSON
    for r in records:
        for k, v in r.items():
            if hasattr(v, 'isoformat'):
                r[k] = v.isoformat()
            elif hasattr(v, 'to_eng_string'): 
                r[k] = float(v)
                
    return records

def create_message_draft(
    prompt: str,
    channel: str = "email",
    target_group: str = "all_students",
    class_id: Optional[str] = None,
    student_ids: Optional[List[str]] = None,
    custom_recipients: Optional[List[str]] = None,
    user: Any = None,
) -> Dict[str, Any]:
    """Create an AI-generated message draft for admin approval."""
    if not user or getattr(user, 'user_type', None) != 'admin':
        return {"error": "Only admins can create AI message drafts."}

    class_model = None
    if target_group == "specific_class":
        if not class_id:
            return {"error": "class_id is required for specific_class drafts."}
        class_model = Class.objects.filter(id=class_id).first()
        if not class_model:
            return {"error": "Class not found."}

    try:
        draft = create_ai_message_draft(
            {
                "prompt": prompt,
                "channel": channel,
                "target_group": target_group,
                "class_model": class_model,
                "student_ids": student_ids or [],
                "custom_recipients": custom_recipients or [],
            },
            user,
        )
    except Exception as e:
        return {"error": str(e)}

    return {
        "draft_id": draft.id,
        "channel": draft.channel,
        "subject": draft.subject,
        "status": draft.status,
        "target_group": draft.target_group,
        "target_summary": (
            draft.class_model.name
            if draft.target_group == "specific_class" and draft.class_model
            else draft.get_target_group_display()
        ),
        "review_url": f"/school-admin/communications?ai=drafts&draft={draft.id}",
        "note": "Draft created only. It has not been sent. Admin must review and approve it.",
    }

def update_fee_type_amount(
    amount: Any = None,
    fee_name: Optional[str] = None,
    fee_id: Optional[int] = None,
    class_name: Optional[str] = None,
    school_name: Optional[str] = None,
    user: Any = None,
) -> Dict[str, Any]:
    """Prepare a fee amount update for explicit admin approval from chat."""
    if amount is None:
        return {"error": "amount is required."}
    if not user or getattr(user, 'user_type', None) != 'admin':
        return {"error": "Only admins can update fee amounts."}

    try:
        amount_decimal = Decimal(str(amount).replace(",", "").strip())
    except (InvalidOperation, AttributeError):
        return {"error": "Enter a valid fee amount."}

    if amount_decimal <= 0:
        return {"error": "Fee amount must be greater than zero."}

    queryset = FeeType.objects.select_related("school").prefetch_related("applicable_classes")

    if fee_id:
        queryset = queryset.filter(id=fee_id)
    elif fee_name:
        queryset = queryset.filter(name__icontains=fee_name.strip())
    else:
        return {"error": "fee_name or fee_id is required."}

    if school_name:
        queryset = queryset.filter(school__name__icontains=school_name.strip())

    if class_name:
        raw_class = class_name.strip()
        compact_class = raw_class.replace(" ", "")
        matching_classes = Class.objects.filter(
            Q(name__icontains=raw_class) |
            Q(grade_level__icontains=raw_class) |
            Q(class_code__iexact=raw_class) |
            Q(class_code__iexact=compact_class)
        )
        if not matching_classes.exists() and compact_class != raw_class:
            matching_classes = Class.objects.filter(
                Q(name__icontains=compact_class) |
                Q(grade_level__icontains=compact_class)
            )
        if matching_classes.exists():
            class_school_ids = matching_classes.values_list("school_id", flat=True)
            queryset = queryset.filter(
                Q(applicable_classes__in=matching_classes) |
                Q(applicable_classes__isnull=True, school_id__in=class_school_ids)
            )
        else:
            return {"error": f"No class matched '{class_name}'."}

    matches = list(queryset.distinct()[:6])
    if not matches:
        return {"error": "No matching fee type found."}
    if len(matches) > 1:
        return {
            "error": "More than one fee type matched. Ask the admin to specify the fee ID.",
            "matches": [
                {
                    "id": fee.id,
                    "name": fee.name,
                    "amount": float(fee.amount),
                    "school": fee.school.name,
                    "classes": [klass.name for klass in fee.applicable_classes.all()],
                }
                for fee in matches
            ],
        }

    fee = matches[0]
    old_amount = fee.amount

    return {
        "requires_approval": True,
        "fee_id": fee.id,
        "fee_name": fee.name,
        "old_amount": float(old_amount),
        "new_amount": float(amount_decimal),
        "school": fee.school.name,
        "classes": [klass.name for klass in fee.applicable_classes.all()],
        "action": {
            "type": "update_fee_type_amount",
            "label": "Approve fee change",
            "summary": f"Change {fee.name} from ₦{old_amount:,.2f} to ₦{amount_decimal:,.2f}",
            "payload": {
                "fee_id": fee.id,
                "fee_name": fee.name,
                "amount": str(amount_decimal),
                "expected_old_amount": str(old_amount),
            },
        },
        "note": "Approval required. The fee has not been updated yet.",
    }


def approve_fee_type_amount_update(payload: Dict[str, Any], user: Any = None) -> Dict[str, Any]:
    """Approve and apply a fee amount update prepared by chat."""
    if not user or getattr(user, 'user_type', None) != 'admin':
        return {"error": "Only admins can approve fee amount updates."}

    if not isinstance(payload, dict):
        return {"error": "Invalid approval payload."}

    fee_id = payload.get("fee_id")
    if not fee_id:
        return {"error": "fee_id is required."}

    try:
        amount_decimal = Decimal(str(payload.get("amount")).replace(",", "").strip())
    except (InvalidOperation, AttributeError):
        return {"error": "Enter a valid fee amount."}

    if amount_decimal <= 0:
        return {"error": "Fee amount must be greater than zero."}

    try:
        expected_old_amount = payload.get("expected_old_amount")
        expected_decimal = (
            Decimal(str(expected_old_amount).replace(",", "").strip())
            if expected_old_amount is not None
            else None
        )
    except (InvalidOperation, AttributeError):
        return {"error": "Invalid previous fee amount in approval payload."}

    try:
        with transaction.atomic():
            fee = (
                FeeType.objects.select_for_update()
                .select_related("school")
                .prefetch_related("applicable_classes")
                .get(id=fee_id)
            )

            if expected_decimal is not None and fee.amount != expected_decimal:
                return {
                    "error": (
                        "This fee changed after Lumina prepared the approval. "
                        "Ask Lumina to prepare the fee change again."
                    ),
                    "fee_id": fee.id,
                    "current_amount": float(fee.amount),
                }

            old_amount = fee.amount
            fee.amount = amount_decimal
            fee.clean()
            fee.save(update_fields=["amount", "updated_at"])
    except Exception as e:
        if isinstance(e, ObjectDoesNotExist):
            return {"error": "Fee type not found."}
        return {"error": str(e)}

    return {
        "updated": True,
        "fee_id": fee.id,
        "fee_name": fee.name,
        "old_amount": float(old_amount),
        "new_amount": float(fee.amount),
        "school": fee.school.name,
        "classes": [klass.name for klass in fee.applicable_classes.all()],
        "changes": [
            {
                "target_model": "fee_types",
                "record_id": str(fee.id),
                "field": "amount",
                "field_label": "Amount",
                "old_value": str(old_amount),
                "new_value": str(fee.amount),
                "old_display": f"₦{old_amount:,.2f}",
                "new_display": f"₦{fee.amount:,.2f}",
                "record_label": record_label(fee),
            }
        ],
        "note": f"{fee.name} has been updated from ₦{old_amount:,.2f} to ₦{fee.amount:,.2f}.",
    }

def update_record_fields(
    model_name: str = "",
    record_id: Any = "",
    fields: Dict[str, Any] = None,
    user: Any = None,
) -> Dict[str, Any]:
    """Prepare generic admin record edits for approval from chat."""
    if not user or getattr(user, 'user_type', None) != 'admin':
        return {"error": "Only admins can prepare record edits."}

    if not isinstance(fields, dict) or not fields:
        return {"error": "Provide at least one field to update."}

    normalized = normalize_model_name(model_name)
    if normalized not in EDITABLE_ADMIN_MODELS:
        return {"error": f"'{model_name}' cannot be edited from chat."}

    try:
        record = resolve_admin_record(normalized, record_id)
        changes = []

        # Auto-delegate fields to BioData if they belong there
        to_student = {}
        to_biodata = {}
        
        if normalized == "students":
            biodata_fields = {f.name for f in BioData._meta.fields}
            student_fields = {f.name for f in Student._meta.fields}
            
            # Handle special 'full_name' or 'name' alias
            if "full_name" in fields or "name" in fields:
                name_val = fields.get("full_name", fields.get("name"))
                to_biodata.update(split_full_name(name_val))
                fields = {k: v for k, v in fields.items() if k not in {"full_name", "name"}}

            for field_name, value in fields.items():
                if field_name in student_fields:
                    to_student[field_name] = value
                elif field_name in biodata_fields:
                    to_biodata[field_name] = value
                else:
                    to_student[field_name] = value

            try:
                biodata = record.biodata
            except ObjectDoesNotExist:
                biodata = BioData(student=record)

            changes = []
            for fn, val in to_student.items():
                changes.append(build_record_change("students", record, fn, val))
            for fn, val in to_biodata.items():
                changes.append(build_record_change("student_biodata", biodata, fn, val))
        else:
            # For non-student models, just apply changes directly
            changes = []
            for field_name, value in fields.items():
                changes.append(build_record_change(normalized, record, field_name, value))

        if not changes:
            return {"error": "No editable fields were provided."}

        validate_record_changes(changes)
    except ObjectDoesNotExist:
        return {"error": f"No {model_name} record found with ID '{record_id}'."}
    except Exception as e:
        return {"error": str(e)}

    summary_parts = [
        f"{change['field_label']}: {change['old_display']} -> {change['new_display']}"
        for change in changes
    ]
    summary = f"Update {record_label(record)}: " + "; ".join(summary_parts)

    return {
        "requires_approval": True,
        "model_name": normalized,
        "record_id": str(record.pk),
        "changes": changes,
        "action": {
            "type": "update_record_fields",
            "label": "Approve record update",
            "summary": summary,
            "payload": {
                "model_name": normalized,
                "record_id": str(record.pk),
                "changes": changes,
            },
        },
        "note": "Approval required. The record has not been updated yet.",
    }


def approve_record_fields_update(payload: Dict[str, Any], user: Any = None) -> Dict[str, Any]:
    """Approve and apply generic record edits prepared by chat."""
    if not user or getattr(user, 'user_type', None) != 'admin':
        return {"error": "Only admins can approve record edits."}

    if not isinstance(payload, dict):
        return {"error": "Invalid approval payload."}

    changes = payload.get("changes")
    if not isinstance(changes, list) or not changes:
        return {"error": "No changes were supplied for approval."}

    try:
        with transaction.atomic():
            locked_records = {}
            applied = []

            for change in changes:
                normalized = normalize_model_name(change.get("target_model"))
                model = get_editable_admin_model(normalized)
                if not model:
                    return {"error": f"'{change.get('target_model')}' cannot be edited from chat."}

                record_key = (normalized, str(change.get("record_id")))
                if record_key not in locked_records:
                    if normalized == "student_biodata":
                        try:
                            locked_records[record_key] = model.objects.select_for_update().get(pk=change.get("record_id"))
                        except (ObjectDoesNotExist, ValueError, ValidationError):
                            try:
                                student = Student.objects.get(id=change.get("record_id"))
                                try:
                                    locked_records[record_key] = BioData.objects.select_for_update().get(student=student)
                                except ObjectDoesNotExist:
                                    locked_records[record_key] = BioData(student=student)
                            except ObjectDoesNotExist:
                                return {"error": f"Student {change.get('record_id')} not found for biodata update."}
                    else:
                        locked_records[record_key] = model.objects.select_for_update().get(pk=change.get("record_id"))
                record = locked_records[record_key]

                field = get_editable_field(model, change.get("field"))
                current_value = serialize_field_value(record, field)
                if current_value != change.get("expected_old_value"):
                    return {
                        "error": (
                            "This record changed after Lumina prepared the approval. "
                            "Ask Lumina to prepare the edit again."
                        ),
                        "model_name": normalized,
                        "record_id": str(record.pk),
                        "field": field.name,
                        "current_value": current_value,
                    }

                set_field_value(record, field, change.get("new_value"))
                applied.append({
                    "model_name": normalized,
                    "target_model": normalized,
                    "record_id": str(record.pk),
                    "field": field.name,
                    "old_value": current_value,
                    "new_value": serialize_field_value(record, field),
                    "old_display": change.get("old_display", str(current_value)),
                    "new_display": display_field_value(record, field),
                    "field_label": str(field.verbose_name).title(),
                    "record_label": record_label(record),
                })

            for (normalized, _record_id), record in locked_records.items():
                record.full_clean()
                changed_fields = [
                    item["field"]
                    for item in applied
                    if item["model_name"] == normalized and str(item["record_id"]) == str(record.pk)
                ]
                if hasattr(record, "updated_at") and "updated_at" not in changed_fields:
                    changed_fields.append("updated_at")
                record.save(update_fields=changed_fields)
    except ObjectDoesNotExist:
        return {"error": "One of the records could not be found."}
    except Exception as e:
        return {"error": str(e)}

    if len(applied) == 1:
        item = applied[0]
        note = f"{item['record_label']} {item['field_label']} has been updated."
    else:
        note = f"{len(applied)} record fields have been updated."

    return {
        "updated": True,
        "changes": applied,
        "note": note,
    }


def create_ai_action_log(
    action_type: str,
    payload: Dict[str, Any],
    result: Dict[str, Any],
    user: Any,
    label: str = "",
    summary: str = "",
) -> AIActionLog:
    """Store an approved AI action for audit and future revert."""
    return AIActionLog.objects.create(
        action_type=action_type,
        label=label or action_type.replace("_", " ").title(),
        summary=summary or result.get("note", ""),
        payload=payload or {},
        result=result or {},
        changes=result.get("changes") or [],
        status="approved",
        approved_by=user,
    )


def revert_ai_action(action_log: AIActionLog, user: Any = None) -> Dict[str, Any]:
    """Revert an approved AI action using its logged old/new values."""
    if not user or getattr(user, 'user_type', None) != 'admin':
        return {"error": "Only admins can revert AI actions."}

    if action_log.status != "approved":
        return {"error": "Only approved actions can be reverted."}

    changes = action_log.changes or []
    if not changes:
        return {"error": "This action does not have revertable changes."}

    try:
        with transaction.atomic():
            locked_records = {}
            reverted = []

            for change in changes:
                normalized = normalize_model_name(change.get("target_model") or change.get("model_name"))
                model = get_editable_admin_model(normalized)
                if not model:
                    return {"error": f"'{normalized}' cannot be reverted from chat."}

                record_key = (normalized, str(change.get("record_id")))
                if record_key not in locked_records:
                    locked_records[record_key] = model.objects.select_for_update().get(pk=change.get("record_id"))
                record = locked_records[record_key]

                field = get_editable_field(model, change.get("field"))
                current_value = serialize_field_value(record, field)
                expected_value = change.get("new_value")
                if current_value != expected_value:
                    return {
                        "error": (
                            "This record changed after the AI action was approved, so it cannot be reverted safely."
                        ),
                        "model_name": normalized,
                        "record_id": str(record.pk),
                        "field": field.name,
                        "current_value": current_value,
                        "expected_value": expected_value,
                    }

                set_field_value(record, field, change.get("old_value"))
                reverted.append({
                    "model_name": normalized,
                    "target_model": normalized,
                    "record_id": str(record.pk),
                    "field": field.name,
                    "field_label": str(field.verbose_name).title(),
                    "old_value": expected_value,
                    "new_value": serialize_field_value(record, field),
                    "old_display": change.get("new_display", str(expected_value)),
                    "new_display": change.get("old_display", display_field_value(record, field)),
                    "record_label": record_label(record),
                })

            for (normalized, _record_id), record in locked_records.items():
                record.full_clean()
                changed_fields = [
                    item["field"]
                    for item in reverted
                    if item["model_name"] == normalized and str(item["record_id"]) == str(record.pk)
                ]
                if hasattr(record, "updated_at") and "updated_at" not in changed_fields:
                    changed_fields.append("updated_at")
                record.save(update_fields=changed_fields)

            from django.utils import timezone
            action_log.status = "reverted"
            action_log.reverted_by = user
            action_log.reverted_at = timezone.now()
            action_log.result = {
                **(action_log.result or {}),
                "reverted": True,
                "revert_changes": reverted,
            }
            action_log.save(update_fields=["status", "reverted_by", "reverted_at", "result", "updated_at"])
    except ObjectDoesNotExist:
        return {"error": "One of the records could not be found."}
    except Exception as e:
        return {"error": str(e)}

    return {
        "reverted": True,
        "changes": reverted,
        "note": f"AI action #{action_log.id} has been reverted.",
    }

# Updated tool definitions for OpenAI (enum includes new models)
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_data_summary",
            "description": "Get counts and basic statistics for school models.",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_name": {
                        "type": "string",
                        "enum": ["students", "staff", "fee_types", "fee_payments", "exams", "questions", "schools", "sessions", "subjects", "timetables", "attendance", "my_profile"],
                        "description": "The name of the model to query."
                    },
                    "filters": {
                        "type": "object",
                        "description": "Optional filters."
                    }
                },
                "required": ["model_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_message_draft",
            "description": "Create an AI email or SMS draft for admin review. This never sends the message; it only creates a draft that must be approved from Communications > AI Assist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The admin's instruction for the message to draft."
                    },
                    "channel": {
                        "type": "string",
                        "enum": ["email", "sms"],
                        "description": "Delivery channel for the draft.",
                        "default": "email"
                    },
                    "target_group": {
                        "type": "string",
                        "enum": ["all_students", "specific_class", "all_staff", "teaching_staff", "non_teaching_staff", "custom"],
                        "description": "Recipient group for the draft.",
                        "default": "all_students"
                    },
                    "class_id": {
                        "type": "string",
                        "description": "Class ID when target_group is specific_class."
                    },
                    "student_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Student IDs for a custom student recipient list."
                    },
                    "custom_recipients": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Email addresses or phone numbers for a custom recipient list."
                    }
                },
                "required": ["prompt", "channel", "target_group"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_fee_type_amount",
            "description": "Admin-only action to prepare a fee type amount update for approval. This returns an approval action and does not save until the admin clicks Approve.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fee_name": {
                        "type": "string",
                        "description": "Fee type name, for example Application Fee."
                    },
                    "fee_id": {
                        "type": "integer",
                        "description": "Exact fee type ID, preferred when available."
                    },
                    "amount": {
                        "type": "number",
                        "description": "New amount in Naira."
                    },
                    "class_name": {
                        "type": "string",
                        "description": "Optional class name/code, for example JSS1 or JSS 1."
                    },
                    "school_name": {
                        "type": "string",
                        "description": "Optional school name to disambiguate."
                    }
                },
                "required": ["amount"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_record_fields",
            "description": (
                "Admin-only action to prepare edits to school records for approval. "
                "This never saves immediately; it returns an approval action. "
                "Use this for admin requests like changing a student name, staff details, class names, subjects, schools, sessions, or other editable record fields. "
                "For student names, use model_name='students', record_id as the student/application/admission ID, and fields={'full_name': 'Surname Firstname Othernames'}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "model_name": {
                        "type": "string",
                        "enum": ["students", "staff", "fee_types", "fee_payments", "exams", "questions", "schools", "sessions", "classes", "subjects", "departments", "timetables", "student_biodata"],
                        "description": "The model/table to edit."
                    },
                    "record_id": {
                        "type": "string",
                        "description": "Record primary key. For students, application number or admission number also works."
                    },
                    "fields": {
                        "type": "object",
                        "description": "Field names and new values. For student name, pass full_name."
                    }
                },
                "required": ["model_name", "record_id", "fields"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_records",
            "description": "List detailed records for a model.",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_name": {
                        "type": "string",
                        "enum": ["students", "staff", "fee_types", "fee_payments", "exams", "questions", "schools", "sessions", "subjects", "timetables", "attendance", "my_profile"],
                        "description": "The name of the model to query."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of records to return.",
                        "default": 5
                    }
                },
                "required": ["model_name"]
            }
        }
    }
]
