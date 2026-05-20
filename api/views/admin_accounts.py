"""
Admin account management — list, create, toggle active state for users
with user_type='admin'. Used by the Admin Accounts settings tab.
"""
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from api.models import User
from api.permissions import IsSchoolAdmin


def _serialize_admin(user: User) -> dict:
    return {
        'id': user.id,
        'email': user.email,
        'is_active': user.is_active,
        'is_superuser': user.is_superuser,
        'date_joined': user.date_joined.isoformat() if user.date_joined else None,
    }


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def admin_accounts(request):
    """List all admin accounts or create a new one."""
    if request.method == 'GET':
        admins = User.objects.filter(user_type='admin').order_by('-date_joined')
        return Response([_serialize_admin(u) for u in admins])

    email = (request.data.get('email') or '').strip().lower()
    password = request.data.get('password') or ''

    if not email or '@' not in email:
        return Response({'error': 'A valid email is required.'}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(email__iexact=email).exists():
        return Response({'error': 'A user with this email already exists.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        validate_password(password)
    except DjangoValidationError as e:
        return Response({'error': ' '.join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(
        email=email,
        password=password,
        user_type='admin',
        is_staff=True,
        is_active=True,
    )
    return Response(_serialize_admin(user), status=status.HTTP_201_CREATED)


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated, IsSchoolAdmin])
def admin_account_detail(request, pk):
    """Toggle active state or delete an admin account.

    Safety rails:
    - You cannot deactivate or delete your own account.
    - You cannot deactivate or delete the last active admin.
    - You cannot delete superusers (Django superuser must be managed in shell).
    """
    try:
        target = User.objects.get(pk=pk, user_type='admin')
    except User.DoesNotExist:
        return Response({'error': 'Admin not found.'}, status=status.HTTP_404_NOT_FOUND)

    if target.pk == request.user.pk:
        return Response({'error': 'You cannot modify your own account here.'}, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        if target.is_superuser:
            return Response({'error': 'Superusers cannot be deleted from this page.'}, status=status.HTTP_400_BAD_REQUEST)
        active_others = User.objects.filter(user_type='admin', is_active=True).exclude(pk=target.pk).count()
        if active_others == 0:
            return Response({'error': 'At least one active admin must remain.'}, status=status.HTTP_400_BAD_REQUEST)
        target.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PATCH
    new_active = request.data.get('is_active')
    if new_active is not None:
        new_active = bool(new_active)
        if not new_active:
            active_others = User.objects.filter(user_type='admin', is_active=True).exclude(pk=target.pk).count()
            if active_others == 0:
                return Response({'error': 'At least one active admin must remain.'}, status=status.HTTP_400_BAD_REQUEST)
        target.is_active = new_active
        target.save(update_fields=['is_active'])

    new_password = request.data.get('password')
    if new_password:
        try:
            validate_password(new_password)
        except DjangoValidationError as e:
            return Response({'error': ' '.join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
        target.set_password(new_password)
        target.save()

    return Response(_serialize_admin(target), status=status.HTTP_200_OK)
