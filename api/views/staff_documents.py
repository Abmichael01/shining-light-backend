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

from api.models import Staff, StaffChangeRequest, StaffDocument, StaffEducation
from api.pagination import StandardResultsSetPagination
from api.permissions import IsSchoolAdmin
from api.serializers import StaffChangeRequestSerializer, StaffDocumentSerializer, StaffEducationSerializer
from api.services.staff_audit import record_document_change, record_education_change


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
# Staff "Other Documents" (NIN, passport, TRCN, etc.) — non-cert files.
# Lives on StaffDocument model, embedded in the staff edit form.
# ---------------------------------------------------------------------------

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def my_staff_documents(request):
    """List or upload an 'other document' for the authenticated staff."""
    staff = _resolve_staff(request.user)
    if not staff:
        return Response({'error': 'Staff profile not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        docs = staff.staff_documents.all()
        serializer = StaffDocumentSerializer(docs, many=True, context={'request': request})
        return Response(serializer.data)

    serializer = StaffDocumentSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    # Staff-uploaded docs always start unverified — admin must approve.
    document = serializer.save(staff=staff, verified=False, verified_by=None, verified_at=None)

    record_document_change(
        staff=staff,
        document=document,
        change_type='document_upload',
        new_filename=document.document_file.name if document.document_file else '',
    )
    return Response(
        StaffDocumentSerializer(document, context={'request': request}).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def my_staff_document_detail(request, pk):
    """Replace the file on or delete an 'other document'."""
    staff = _resolve_staff(request.user)
    if not staff:
        return Response({'error': 'Staff profile not found'}, status=status.HTTP_404_NOT_FOUND)

    document = get_object_or_404(StaffDocument, pk=pk, staff=staff)

    if request.method == 'PUT':
        new_file = request.FILES.get('document_file')
        if not new_file:
            return Response({'error': 'document_file is required.'}, status=status.HTTP_400_BAD_REQUEST)

        old_file = document.document_file
        old_name = old_file.name if old_file else ''
        document.document_file = new_file
        document.verified = False
        document.verified_by = None
        document.verified_at = None
        if 'label' in request.data:
            document.label = request.data.get('label') or ''
        document.save()

        if old_file and old_file.name and old_file.name != document.document_file.name:
            old_file.delete(save=False)

        record_document_change(
            staff=staff,
            document=document,
            change_type='document_replace',
            old_filename=old_name,
            new_filename=document.document_file.name,
        )
        return Response(
            StaffDocumentSerializer(document, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )

    # DELETE
    old_name = document.document_file.name if document.document_file else ''
    record_document_change(
        staff=staff,
        document=document,
        change_type='document_delete',
        old_filename=old_name,
    )
    document.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Admin-side staff documents
# Admin is the authority, so these bypass the change-request/audit flow and
# the uploaded docs land verified=True immediately. Used by the admin
# staff-create wizard and the admin staff-edit form.
# ---------------------------------------------------------------------------

def _verify_doc_immediately(document: StaffDocument, admin_user) -> None:
    document.verified = True
    document.verified_by = admin_user
    document.verified_at = timezone.now()


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def admin_staff_documents(request, staff_pk):
    """List or upload an 'other document' for any staff (admin-side)."""
    staff = get_object_or_404(Staff, pk=staff_pk)

    if request.method == 'GET':
        docs = staff.staff_documents.all()
        return Response(
            StaffDocumentSerializer(docs, many=True, context={'request': request}).data
        )

    serializer = StaffDocumentSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    document = serializer.save(staff=staff)
    _verify_doc_immediately(document, request.user)
    document.save(update_fields=['verified', 'verified_by', 'verified_at', 'updated_at'])
    return Response(
        StaffDocumentSerializer(document, context={'request': request}).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def admin_staff_document_detail(request, staff_pk, pk):
    """Replace the file on or delete an 'other document' as admin."""
    staff = get_object_or_404(Staff, pk=staff_pk)
    document = get_object_or_404(StaffDocument, pk=pk, staff=staff)

    if request.method == 'PUT':
        new_file = request.FILES.get('document_file')
        if not new_file:
            return Response({'error': 'document_file is required.'}, status=status.HTTP_400_BAD_REQUEST)
        old_file = document.document_file
        document.document_file = new_file
        if 'label' in request.data:
            document.label = request.data.get('label') or ''
        _verify_doc_immediately(document, request.user)
        document.save()
        if old_file and old_file.name and old_file.name != document.document_file.name:
            old_file.delete(save=False)
        return Response(
            StaffDocumentSerializer(document, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )

    document.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


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


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def staff_changes_grouped(request):
    """Group change requests by staff member so the admin sees one card
    per teacher instead of one card per individual edit. Each group lists
    all the changes that staff has pending (or whatever status is filtered)."""
    queryset = (
        StaffChangeRequest.objects
        .select_related('staff', 'document', 'education', 'reviewed_by')
        .all()
    )
    status_filter = request.query_params.get('status', 'pending_review')
    if status_filter and status_filter != 'all':
        queryset = queryset.filter(status=status_filter)

    # Order so we can group cleanly: newest staff submission first, then
    # newest change within a group first.
    queryset = queryset.order_by('-submitted_at')

    groups: dict[int, dict] = {}
    for change in queryset:
        staff_pk = change.staff_id
        bucket = groups.get(staff_pk)
        if bucket is None:
            bucket = {
                'staff': change.staff_id,
                'staff_id': change.staff.staff_id,
                'staff_name': change.staff.get_full_name(),
                'change_count': 0,
                'latest_submitted_at': change.submitted_at.isoformat() if change.submitted_at else None,
                'changes': [],
            }
            groups[staff_pk] = bucket
        bucket['change_count'] += 1
        bucket['changes'].append(
            StaffChangeRequestSerializer(change, context={'request': request}).data
        )

    # Already in newest-staff-first order because we iterated ordered queryset
    return Response(list(groups.values()))


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def staff_change_approve(request, pk):
    """Approve a pending change.

    Three cases:
      1. Gated profile_field change — copy new_value onto the Staff record
         now and stamp applied_at. Until this point the Staff record kept
         the old value.
      2. Document upload/replace — mark the associated StaffDocument
         verified.
      3. Education create/update — mark the associated StaffEducation
         verified.

    Cases 2 and 3 (and non-gated profile rows) were already applied at
    submission time; approval is the verification stamp.
    """
    change = get_object_or_404(StaffChangeRequest, pk=pk)
    if change.status != 'pending_review':
        return Response(
            {'error': f'Change is already {change.status}.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    now = timezone.now()
    applied_at = change.applied_at

    if change.is_gated and change.change_type == 'profile_field':
        # The gated value has been waiting in change.new_value. Apply it.
        staff = change.staff
        field = change.field_name
        if hasattr(staff, field):
            setattr(staff, field, change.new_value or '')
            staff.save(update_fields=[field, 'updated_at'])
        applied_at = now

    change.status = 'approved'
    change.reviewed_by = request.user
    change.reviewed_at = now
    change.applied_at = applied_at
    change.review_notes = request.data.get('notes', '') or ''
    change.save()

    if change.document and change.change_type in ('document_upload', 'document_replace'):
        change.document.verified = True
        change.document.verified_by = request.user
        change.document.verified_at = now
        change.document.save(update_fields=['verified', 'verified_by', 'verified_at', 'updated_at'])

    if change.education and change.change_type in ('education_create', 'education_update'):
        change.education.verified = True
        change.education.verified_by = request.user
        change.education.verified_at = now
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
