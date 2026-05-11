"""
AI-assisted admin message drafting and approved delivery.

The AI is only allowed to draft content. Delivery happens through an explicit
admin approval action.
"""

import json
import re
from typing import Any, Dict, List, Tuple

from django.core.mail import get_connection
from django.db import transaction
from django.utils import timezone
from django.utils.html import strip_tags

from api.models import AIMessageDraft, GuardianMessage, Staff, Student
from api.utils.email import get_student_recipient_emails, send_bulk_email
from api.utils.sms import send_bulk_sms

from .openai_client import get_default_model, get_openai_client


ALLOWED_CHANNELS = {"sms", "email"}
ALLOWED_TARGET_GROUPS = {
    "all_students",
    "specific_class",
    "all_staff",
    "teaching_staff",
    "non_teaching_staff",
    "custom",
}


def normalize_list(value: Any) -> List[str]:
    if not value:
        return []
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def build_target_description(payload: Dict[str, Any]) -> str:
    target_group = payload.get("target_group")
    class_model = payload.get("class_model")
    student_ids = normalize_list(payload.get("student_ids"))
    custom_recipients = normalize_list(payload.get("custom_recipients"))

    labels = {
        "all_students": "all enrolled students and their parents/guardians",
        "all_staff": "all active staff",
        "teaching_staff": "all active teaching staff",
        "non_teaching_staff": "all active non-teaching staff",
    }
    if target_group == "specific_class":
        class_name = getattr(class_model, "name", None) or "the selected class"
        return f"students and parents/guardians in {class_name}"
    if target_group == "custom":
        count = len(student_ids) + len(custom_recipients)
        return f"a custom recipient list with {count} recipient reference(s)"
    return labels.get(target_group, "the selected recipients")


def clean_ai_json(raw_text: str) -> Dict[str, str]:
    text = (raw_text or "").strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("AI response must be a JSON object")
    return {
        "subject": str(data.get("subject") or "").strip(),
        "content": str(data.get("content") or "").strip(),
    }


def generate_message_copy(
    *,
    prompt: str,
    channel: str,
    target_description: str,
) -> Tuple[str, str, str]:
    if not prompt.strip():
        raise ValueError("prompt is required")

    model = get_default_model()
    client = get_openai_client()
    channel_instruction = (
        "For SMS, write one plain-text message under 160 characters. Do not add HTML."
        if channel == "sms"
        else "For email, write polished HTML body content using simple paragraphs/lists. Keep it concise."
    )
    feedback_notes = list(
        AIMessageDraft.objects.filter(status="rejected")
        .exclude(rejection_reason="")
        .order_by("-rejected_at")
        .values_list("rejection_reason", flat=True)[:5]
    )
    feedback_instruction = ""
    if feedback_notes:
        feedback_instruction = (
            "\nRecent admin rejection feedback to avoid repeating:\n"
            + "\n".join(f"- {note[:240]}" for note in feedback_notes)
        )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You draft school admin communications for Shining Light International School. "
                    "Return only valid JSON with keys subject and content. The admin will review "
                    "and approve before anything is sent."
                    f"{feedback_instruction}"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Audience: {target_description}\n"
                    f"Channel: {channel}\n"
                    f"Instruction: {channel_instruction}\n"
                    f"Admin request: {prompt.strip()}"
                ),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.45,
    )
    draft = clean_ai_json(response.choices[0].message.content or "{}")
    content = draft["content"]
    subject = draft["subject"]

    if channel == "sms":
        content = strip_tags(content).replace("\n", " ").strip()
        if len(content) > 160:
            content = content[:157].rstrip() + "..."
        if not subject:
            subject = "SMS Draft"
    elif not subject:
        subject = "Shining Light School Notification"

    if not content:
        raise ValueError("AI did not return message content")

    return subject, content, model


def create_ai_message_draft(validated_data: Dict[str, Any], user) -> AIMessageDraft:
    channel = validated_data.get("channel")
    target_group = validated_data.get("target_group")
    if channel not in ALLOWED_CHANNELS:
        raise ValueError("channel must be sms or email")
    if target_group not in ALLOWED_TARGET_GROUPS:
        raise ValueError("target_group is invalid")
    if target_group == "specific_class" and not validated_data.get("class_model"):
        raise ValueError("class_id is required for a specific class draft")

    target_description = build_target_description(validated_data)
    subject, content, model = generate_message_copy(
        prompt=validated_data["prompt"],
        channel=channel,
        target_description=target_description,
    )

    return AIMessageDraft.objects.create(
        channel=channel,
        target_group=target_group,
        class_model=validated_data.get("class_model"),
        student_ids=normalize_list(validated_data.get("student_ids")),
        custom_recipients=normalize_list(validated_data.get("custom_recipients")),
        prompt=validated_data["prompt"],
        subject=subject,
        content=content,
        ai_model=model,
        created_by=user,
    )


def resolve_students_for_draft(draft: AIMessageDraft):
    students = Student.objects.none()
    if draft.target_group == "all_students":
        students = Student.objects.filter(status="enrolled")
    elif draft.target_group == "specific_class" and draft.class_model_id:
        students = Student.objects.filter(status="enrolled", class_model=draft.class_model)
    elif draft.target_group == "custom" and draft.student_ids:
        students = Student.objects.filter(id__in=draft.student_ids)
    return students.select_related("class_model").prefetch_related("guardians")


def resolve_staff_for_draft(draft: AIMessageDraft):
    staff = Staff.objects.none()
    if draft.target_group == "all_staff":
        staff = Staff.objects.filter(status="active", user__is_active=True)
    elif draft.target_group == "teaching_staff":
        staff = Staff.objects.filter(status="active", user__is_active=True, staff_type="teaching")
    elif draft.target_group == "non_teaching_staff":
        staff = Staff.objects.filter(status="active", user__is_active=True, staff_type="non_teaching")
    return staff.select_related("user")


def get_student_phone(student):
    primary = student.guardians.filter(is_primary_contact=True).first()
    if primary and primary.phone_number:
        return primary.phone_number, primary
    guardian = student.guardians.first()
    if guardian and guardian.phone_number:
        return guardian.phone_number, guardian
    return None, primary or guardian


def resolve_delivery_targets(draft: AIMessageDraft):
    students = list(resolve_students_for_draft(draft))
    staff = list(resolve_staff_for_draft(draft))
    custom_recipients = normalize_list(draft.custom_recipients)

    recipients = []
    guardian_records = []
    missing_count = 0

    if draft.channel == "email":
        for student in students:
            emails = get_student_recipient_emails(student)
            primary = student.guardians.filter(is_primary_contact=True).first() or student.guardians.first()
            if emails:
                recipients.extend(emails)
                guardian_records.append((student, primary, "pending", ""))
            else:
                missing_count += 1
                guardian_records.append((student, primary, "failed", "No email contact found"))

        recipients.extend([s.user.email for s in staff if s.user and s.user.email])
        recipients.extend(custom_recipients)
    else:
        for student in students:
            phone, primary = get_student_phone(student)
            if phone:
                recipients.append(phone)
                guardian_records.append((student, primary, "pending", ""))
            else:
                missing_count += 1
                guardian_records.append((student, primary, "failed", "No phone contact found"))

        recipients.extend([s.phone_number for s in staff if s.phone_number])
        recipients.extend(custom_recipients)

    cleaned = []
    seen = set()
    for recipient in recipients:
        value = str(recipient).strip()
        if value and value not in seen:
            seen.add(value)
            cleaned.append(value)

    return cleaned, guardian_records, missing_count


def deliver_draft(draft: AIMessageDraft, user) -> Dict[str, Any]:
    recipients, guardian_records, missing_count = resolve_delivery_targets(draft)
    if not recipients:
        return {
            "success": False,
            "summary": "No valid recipients found.",
            "error": "No valid recipients found.",
            "recipient_count": 0,
        }

    connection = None
    try:
        if draft.channel == "email":
            connection = get_connection()
            connection.open()
            success, provider_message = send_bulk_email(
                recipients,
                draft.subject or "Shining Light School Notification",
                draft.content,
                connection=connection,
            )
        else:
            sms_text = strip_tags(draft.content).replace("\n", " ").strip()
            if len(sms_text) > 160:
                sms_text = sms_text[:157].rstrip() + "..."
            success, provider_message = send_bulk_sms(recipients, sms_text)
    finally:
        if connection:
            connection.close()

    now = timezone.now()
    guardian_messages = []
    for student, guardian, initial_status, error_message in guardian_records:
        status = initial_status
        final_error = error_message
        sent_at = None
        if initial_status == "pending":
            status = "sent" if success else "failed"
            final_error = "" if success else str(provider_message)
            sent_at = now if success else None
        guardian_messages.append(
            GuardianMessage(
                sender=user,
                student=student,
                recipient_guardian=guardian,
                channel=draft.channel,
                subject=draft.subject,
                content=draft.content,
                status=status,
                error_message=final_error or None,
                sent_at=sent_at,
            )
        )
    if guardian_messages:
        GuardianMessage.objects.bulk_create(guardian_messages)

    summary = (
        f"Processed {len(recipients)} resolved recipient(s). "
        f"Missing contacts: {missing_count}."
    )
    return {
        "success": bool(success),
        "summary": summary,
        "error": "" if success else str(provider_message),
        "recipient_count": len(recipients),
    }


def approve_and_send_draft(draft: AIMessageDraft, user) -> Dict[str, Any]:
    if draft.status == "sent":
        raise ValueError("This draft has already been sent")
    if draft.status == "rejected":
        raise ValueError("Rejected drafts cannot be sent")
    if not draft.content.strip():
        raise ValueError("Draft content is required before sending")
    if draft.channel == "email" and not draft.subject.strip():
        raise ValueError("Email subject is required before sending")

    now = timezone.now()
    with transaction.atomic():
        draft.status = "approved"
        draft.approved_by = user
        draft.approved_at = now
        draft.error_message = ""
        draft.save(update_fields=["status", "approved_by", "approved_at", "error_message", "updated_at"])

    result = deliver_draft(draft, user)
    draft.sent_by = user
    draft.send_summary = result["summary"]
    draft.error_message = result["error"]
    if result["success"]:
        draft.status = "sent"
        draft.sent_at = timezone.now()
    else:
        draft.status = "failed"
    draft.save(
        update_fields=[
            "status",
            "sent_by",
            "sent_at",
            "send_summary",
            "error_message",
            "updated_at",
        ]
    )
    return result


def reject_draft(draft: AIMessageDraft, user, reason: str = "") -> None:
    if draft.status == "sent":
        raise ValueError("Sent drafts cannot be rejected")
    draft.status = "rejected"
    draft.approved_by = user
    draft.rejected_at = timezone.now()
    draft.rejection_reason = reason.strip()
    draft.error_message = ""
    draft.save(update_fields=["status", "approved_by", "rejected_at", "rejection_reason", "error_message", "updated_at"])
