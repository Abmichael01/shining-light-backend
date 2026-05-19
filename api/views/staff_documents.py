"""
Staff self-service education records (qualifications + certificate files)
and the admin review queue for all staff change requests.

Staff side:
    GET    /staff-portal/education/             list my education records
    POST   /staff-portal/education/             add a new qualification
    PATCH  /staff-portal/education/{id}/        update one (or replace cert file)
    DELETE /staff-portal/education/{id}/        remove one

Admin side:
    GET  /staff-changes/                    list pending change requests
    GET  /staff-changes/summary/            counts for the badge
    POST /staff-changes/{id}/approve/       approve and verify
    POST /staff-changes/{id}/reject/        reject (admin manually fixes if needed)
"""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from api.models import Staff, StaffChangeRequest, StaffEducation
from api.pagination import StandardResultsSetPagination
from api.permissions import IsSchoolAdmin
from api.serializers import StaffChangeRequestSerializer, StaffEducationSerializer
from api.services.staff_audit import record_education_change


# Tracked fields on StaffEducation — anything outside this list (id, staff,
# timestamps, verified, certificate) is handled separately.
TRACKED_EDUCATION_FIELDS = (
    'level',
    'institution_name',
    'year_of_graduation',
    'degree',
)


def _resolve_staff(user):
    return Staff.objects.filter(user=user).first()


def _education_summary(edu: StaffEducation) -> str:
    """Short human-friendly string of an education record for audit values."""
    parts = [
        edu.get_level_display() if edu.level else '',
        edu.institution_name or '',
        str(edu.year_of_graduation or ''),
        edu.get_degree_display() if edu.degree else '',
    ]
    return ' · '.join(p for p in parts if p)


def _flip_unverified(edu: StaffEducation) -> None:
    edu.verified = False
    edu.verified_by = None
    edu.verified_at = None


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def my_staff_education(request):
    """List or add education records for the authenticated staff member."""
    staff = _resolve_staff(request.user)
    if not staff:
        return Response({'error': 'Staff profile not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        records = staff.education_records.all()
        serializer = StaffEducationSerializer(records, many=True, context={'request': request})
        return Response(serializer.data)

    serializer = StaffEducationSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    # Staff-created records always start unverified — admin must approve.
    education = serializer.save(staff=staff, verified=False, verified_by=None, verified_at=None)

    record_education_change(
        staff=staff,
        education=education,
        change_type='education_create',
        new_value=_education_summary(education),
    )
    return Response(
        StaffEducationSerializer(education, context={'request': request}).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def my_staff_education_detail(request, pk):
    """Update fields / replace certificate file, or delete an education record."""
    staff = _resolve_staff(request.user)
    if not staff:
        return Response({'error': 'Staff profile not found'}, status=status.HTTP_404_NOT_FOUND)

    education = get_object_or_404(StaffEducation, pk=pk, staff=staff)

    if request.method == 'DELETE':
        snapshot = _education_summary(education)
        record_education_change(
            staff=staff,
            education=None,
            change_type='education_delete',
            old_value=snapshot,
            field_name=education.level,
        )
        education.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PATCH — capture the before snapshot so we can diff
    before = {f: getattr(education, f) for f in TRACKED_EDUCATION_FIELDS}
    had_old_cert = bool(education.certificate)
    old_cert_name = education.certificate.name if had_old_cert else ''

    serializer = StaffEducationSerializer(
        education,
        data=request.data,
        partial=True,
        context={'request': request},
    )
    serializer.is_valid(raise_exception=True)
    education = serializer.save()

    # Flip verification — any change needs admin re-approval
    _flip_unverified(education)
    education.save(update_fields=['verified', 'verified_by', 'verified_at', 'updated_at'])

    # Audit each changed tracked field individually
    after = {f: getattr(education, f) for f in TRACKED_EDUCATION_FIELDS}
    for field in TRACKED_EDUCATION_FIELDS:
        if str(before[field] or '') != str(after[field] or ''):
            record_education_change(
                staff=staff,
                education=education,
                change_type='education_update',
                field_name=field,
                old_value=str(before[field] or ''),
                new_value=str(after[field] or ''),
            )

    # Cert file change is recorded as a single audit row
    new_cert_name = education.certificate.name if education.certificate else ''
    if old_cert_name != new_cert_name:
        record_education_change(
            staff=staff,
            education=education,
            change_type='education_update',
            field_name='certificate',
            old_value=old_cert_name,
            new_value=new_cert_name,
        )

    return Response(
        StaffEducationSerializer(education, context={'request': request}).data,
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# Admin review queue
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def staff_changes_list(request):
    """List staff change requests. Defaults to pending_review."""
    queryset = (
        StaffChangeRequest.objects
        .select_related('staff', 'document', 'education', 'reviewed_by')
        .all()
    )
    status_filter = request.query_params.get('status', 'pending_review')
    if status_filter and status_filter != 'all':
        queryset = queryset.filter(status=status_filter)

    staff_id = request.query_params.get('staff_id')
    if staff_id:
        queryset = queryset.filter(staff__staff_id=staff_id)

    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = StaffChangeRequestSerializer(page, many=True, context={'request': request})
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def staff_changes_summary(request):
    """Lightweight counts admin can poll for a notification badge."""
    return Response({
        'pending_review': StaffChangeRequest.objects.filter(status='pending_review').count(),
        'approved': StaffChangeRequest.objects.filter(status='approved').count(),
        'rejected': StaffChangeRequest.objects.filter(status='rejected').count(),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def staff_change_approve(request, pk):
    """Approve a pending change.

    For document changes: marks the associated StaffDocument verified.
    For education changes: marks the associated StaffEducation verified.
    """
    change = get_object_or_404(StaffChangeRequest, pk=pk)
    if change.status != 'pending_review':
        return Response(
            {'error': f'Change is already {change.status}.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    change.status = 'approved'
    change.reviewed_by = request.user
    change.reviewed_at = timezone.now()
    change.review_notes = request.data.get('notes', '') or ''
    change.save()

    if change.document and change.change_type in ('document_upload', 'document_replace'):
        change.document.verified = True
        change.document.verified_by = request.user
        change.document.verified_at = timezone.now()
        change.document.save(update_fields=['verified', 'verified_by', 'verified_at', 'updated_at'])

    if change.education and change.change_type in ('education_create', 'education_update'):
        change.education.verified = True
        change.education.verified_by = request.user
        change.education.verified_at = timezone.now()
        change.education.save(update_fields=['verified', 'verified_by', 'verified_at', 'updated_at'])

    return Response(
        StaffChangeRequestSerializer(change, context={'request': request}).data,
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def staff_change_reject(request, pk):
    """Reject a pending change. The underlying record was already updated
    by the staff member — admin must manually correct it if a rollback is
    needed. We store the rejection so the audit trail stays accurate."""
    change = get_object_or_404(StaffChangeRequest, pk=pk)
    if change.status != 'pending_review':
        return Response(
            {'error': f'Change is already {change.status}.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    change.status = 'rejected'
    change.reviewed_by = request.user
    change.reviewed_at = timezone.now()
    change.review_notes = request.data.get('notes', '') or ''
    change.save()

    return Response(
        StaffChangeRequestSerializer(change, context={'request': request}).data,
        status=status.HTTP_200_OK,
    )
