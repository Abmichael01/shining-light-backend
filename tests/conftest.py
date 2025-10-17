import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def api_client():
    """API client for making requests"""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def create_user():
    """Factory fixture for creating users"""
    def _create_user(email="test@example.com", password="testpass123", user_type="student", **kwargs):
        return User.objects.create_user(
            email=email,
            password=password,
            user_type=user_type,
            **kwargs
        )
    return _create_user


@pytest.fixture
def test_user(create_user):
    """Create a default test user"""
    return create_user()


@pytest.fixture
def admin_user(create_user):
    """Create an admin user"""
    return create_user(
        email="admin@example.com",
        password="adminpass123",
        user_type="admin",
        is_staff=True,
        is_superuser=True
    )


@pytest.fixture
def staff_user(create_user):
    """Create a staff user"""
    return create_user(
        email="staff@example.com",
        password="staffpass123",
        user_type="staff",
        is_staff=True
    )


@pytest.fixture
def authenticated_client(api_client, test_user):
    """API client with authenticated test user"""
    api_client.force_authenticate(user=test_user)
    return api_client

