"""
Staff document upload/replace endpoints + admin review queue for staff
change requests (documents AND profile field edits).

Staff side:
    GET  /staff-portal/documents/            list my documents
    POST /staff-portal/documents/            upload a new document
    PUT  /staff-portal/documents/{id}/       replace the file on an existing doc
    DELETE /staff-portal/documents/{id}/     delete a document

Admin side:
    GET  /staff-changes/                     list pending change requests
    POST /staff-changes/{id}/approve/        mark as approved (verifies docs)
    POST /staff-changes/{id}/reject/         mark as rejected (admin should
                                             manually revert the change if needed)
"""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from api.models import Staff, StaffChangeRequest, StaffDocument
from api.pagination import StandardResultsSetPagination
from api.permissions import IsSchoolAdmin
from api.serializers import StaffChangeRequestSerializer, StaffDocumentSerializer
from api.services.staff_audit import record_document_change


def _resolve_staff(user):
    return Staff.objects.filter(user=user).first()


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def my_staff_documents(request):
    """List or upload documents for the authenticated staff member."""
    staff = _resolve_staff(request.user)
    if not staff:
        return Response({'error': 'Staff profile not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        docs = staff.staff_documents.all()
        serializer = StaffDocumentSerializer(docs, many=True, context={'request': request})
        return Response(serializer.data)

    serializer = StaffDocumentSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    document = serializer.save(staff=staff)

    record_document_change(
        staff=staff,
        document=document,
        change_type='document_upload',
        new_filename=document.document_file.name,
    )
    return Response(
        StaffDocumentSerializer(document, context={'request': request}).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def my_staff_document_detail(request, pk):
    """Replace the file on a document or delete it. Either action creates an
    audit row so admin sees what changed."""
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
        # New uploads always need re-verification by admin.
        document.verified = False
        document.verified_by = None
        document.verified_at = None
        # Optional re-labelling on replace
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
# Admin review queue
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def staff_changes_list(request):
    """List staff change requests. Defaults to pending_review."""
    queryset = (
        StaffChangeRequest.objects
        .select_related('staff', 'document', 'reviewed_by')
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
    """Admin acknowledges the change is acceptable. If it's a document
    change, the associated document is also marked verified."""
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

    return Response(
        StaffChangeRequestSerializer(change, context={'request': request}).data,
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def staff_change_reject(request, pk):
    """Admin rejects the change. Note: the underlying record was already
    updated by the staff member — admin must manually correct it if a rollback
    is needed. We store the rejection so the audit trail stays accurate."""
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
