import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.auth
class TestLogin:
    """Test login endpoint"""
    
    def test_login_success(self, api_client, test_user):
        """Test successful login with valid credentials"""
        url = reverse('rest_login')
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        response = api_client.post(url, data)
        
        assert response.status_code == 200
        assert 'user' in response.data
        assert response.data['user']['email'] == 'test@example.com'
        assert response.data['user']['user_type'] == 'student'
    
    def test_login_invalid_email(self, api_client):
        """Test login with invalid email"""
        url = reverse('rest_login')
        data = {
            'email': 'nonexistent@example.com',
            'password': 'testpass123'
        }
        response = api_client.post(url, data)
        
        assert response.status_code == 400
    
    def test_login_invalid_password(self, api_client, test_user):
        """Test login with wrong password"""
        url = reverse('rest_login')
        data = {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }
        response = api_client.post(url, data)
        
        assert response.status_code == 400
    
    def test_login_missing_fields(self, api_client):
        """Test login with missing required fields"""
        url = reverse('rest_login')
        
        # Missing password
        response = api_client.post(url, {'email': 'test@example.com'})
        assert response.status_code == 400
        
        # Missing email
        response = api_client.post(url, {'password': 'testpass123'})
        assert response.status_code == 400
    
    def test_login_inactive_user(self, api_client, create_user):
        """Test login with inactive user"""
        inactive_user = create_user(
            email='inactive@example.com',
            password='testpass123',
            is_active=False
        )
        
        url = reverse('rest_login')
        data = {
            'email': 'inactive@example.com',
            'password': 'testpass123'
        }
        response = api_client.post(url, data)
        
        assert response.status_code == 400


@pytest.mark.django_db
@pytest.mark.auth
class TestLogout:
    """Test logout endpoint"""
    
    def test_logout_authenticated_user(self, api_client, test_user):
        """Test logout for authenticated user"""
        # Login first
        api_client.force_authenticate(user=test_user)
        
        url = reverse('rest_logout')
        response = api_client.post(url)
        
        assert response.status_code == 200
        assert 'detail' in response.data
    
    def test_logout_unauthenticated_user(self, api_client):
        """Test logout without authentication"""
        url = reverse('rest_logout')
        response = api_client.post(url)
        
        # Should still return 200 even if not authenticated
        assert response.status_code in [200, 401, 403]


@pytest.mark.django_db
@pytest.mark.auth
class TestUserDetails:
    """Test user details endpoint"""
    
    def test_get_user_details_authenticated(self, authenticated_client, test_user):
        """Test getting current user details when authenticated"""
        url = reverse('rest_user_details')
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        assert response.data['email'] == test_user.email
        assert response.data['user_type'] == test_user.user_type
        assert 'id' in response.data
    
    def test_get_user_details_unauthenticated(self, api_client):
        """Test getting user details without authentication"""
        url = reverse('rest_user_details')
        response = api_client.get(url)
        
        assert response.status_code == 403
    
    def test_update_user_details(self, authenticated_client, test_user):
        """Test updating user details"""
        url = reverse('rest_user_details')
        # Note: Only certain fields should be updatable
        response = authenticated_client.patch(url, {})
        
        # Should succeed or return validation error
        assert response.status_code in [200, 400]


@pytest.mark.django_db
@pytest.mark.auth
class TestPasswordChange:
    """Test password change endpoint"""
    
    def test_change_password_success(self, authenticated_client, test_user):
        """Test successful password change"""
        url = reverse('rest_password_change')
        data = {
            'old_password': 'testpass123',
            'new_password1': 'newpass456!',
            'new_password2': 'newpass456!'
        }
        response = authenticated_client.post(url, data)
        
        assert response.status_code == 200
        
        # Verify new password works
        test_user.refresh_from_db()
        assert test_user.check_password('newpass456!')
    
    def test_change_password_wrong_old_password(self, authenticated_client):
        """Test password change with wrong old password"""
        url = reverse('rest_password_change')
        data = {
            'old_password': 'wrongpassword',
            'new_password1': 'newpass456!',
            'new_password2': 'newpass456!'
        }
        response = authenticated_client.post(url, data)
        
        assert response.status_code == 400
    
    def test_change_password_mismatch(self, authenticated_client):
        """Test password change with mismatched new passwords"""
        url = reverse('rest_password_change')
        data = {
            'old_password': 'testpass123',
            'new_password1': 'newpass456!',
            'new_password2': 'differentpass789!'
        }
        response = authenticated_client.post(url, data)
        
        assert response.status_code == 400
    
    def test_change_password_unauthenticated(self, api_client):
        """Test password change without authentication"""
        url = reverse('rest_password_change')
        data = {
            'old_password': 'testpass123',
            'new_password1': 'newpass456!',
            'new_password2': 'newpass456!'
        }
        response = api_client.post(url, data)
        
        assert response.status_code == 403
    
    def test_change_password_weak_password(self, authenticated_client):
        """Test password change with weak password"""
        url = reverse('rest_password_change')
        data = {
            'old_password': 'testpass123',
            'new_password1': '123',  # Too short
            'new_password2': '123'
        }
        response = authenticated_client.post(url, data)
        
        assert response.status_code == 400


@pytest.mark.django_db
@pytest.mark.auth
class TestUserTypes:
    """Test different user types"""
    
    def test_admin_user_login(self, api_client, admin_user):
        """Test admin user can login"""
        url = reverse('rest_login')
        data = {
            'email': 'admin@example.com',
            'password': 'adminpass123'
        }
        response = api_client.post(url, data)
        
        assert response.status_code == 200
        assert response.data['user']['user_type'] == 'admin'
    
    def test_staff_user_login(self, api_client, staff_user):
        """Test staff user can login"""
        url = reverse('rest_login')
        data = {
            'email': 'staff@example.com',
            'password': 'staffpass123'
        }
        response = api_client.post(url, data)
        
        assert response.status_code == 200
        assert response.data['user']['user_type'] == 'staff'
    
    def test_create_applicant_user(self, create_user):
        """Test creating applicant user"""
        user = create_user(
            email='applicant@example.com',
            password='testpass123',
            user_type='applicant'
        )
        
        assert user.user_type == 'applicant'
        assert user.is_active is True
        assert user.is_staff is False

