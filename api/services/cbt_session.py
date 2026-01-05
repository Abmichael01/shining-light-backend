"""
CBT Session Service - Manages CBT-specific session tokens
"""
import secrets
import string
from datetime import timedelta
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth import get_user_model
from api.models import Student

User = get_user_model()


class CBTSessionService:
    """Service for managing CBT session tokens"""
    
    CACHE_PREFIX = "cbt_session"
    SESSION_TIMEOUT = 7200  # 2 hours default
    
    @classmethod
    def create_session(cls, student_id: str, passcode: str, ip_address: str = None, user_agent: str = None) -> dict:
        """
        Create a CBT session after successful passcode validation
        
        Args:
            student_id: Student ID or admission number
            passcode: Valid passcode
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            dict: Session information
        """
        try:
            # Find student - try admission number, application number, then ID
            try:
                student = Student.objects.get(admission_number=student_id)
            except Student.DoesNotExist:
                try:
                    student = Student.objects.get(application_number=student_id)
                except Student.DoesNotExist:
                    try:
                        student = Student.objects.get(id=student_id)
                    except Student.DoesNotExist:
                        raise ValueError("Student not found")
            
            # Generate session token
            session_token = cls._generate_session_token()
            
            # Create session data - minimal data for authentication only
            session_data = {
                'session_token': session_token,
                'student_id': str(student.id),
                'student_admission_number': student.admission_number or '',
                'created_at': timezone.now().isoformat(),
                'expires_at': (timezone.now() + timedelta(seconds=cls.SESSION_TIMEOUT)).isoformat(),
                'ip_address': ip_address,
                'user_agent': user_agent,
                'is_active': True,
                'last_activity': timezone.now().isoformat()
            }
            
            # Store session in cache
            cache_key = f"{cls.CACHE_PREFIX}:{session_token}"
            cache.set(cache_key, session_data, cls.SESSION_TIMEOUT)
            
            # Store student session mapping
            student_session_key = f"{cls.CACHE_PREFIX}:student:{student.id}"
            cache.set(student_session_key, session_token, cls.SESSION_TIMEOUT)
            
            return session_data
            
        except Exception as e:
            raise ValueError(f"Failed to create CBT session: {str(e)}")
    
    @classmethod
    def validate_session(cls, session_token: str) -> dict:
        """
        Validate a CBT session token
        
        Args:
            session_token: Session token to validate
            
        Returns:
            dict: Session data if valid
            
        Raises:
            ValueError: If session is invalid or expired
        """
        cache_key = f"{cls.CACHE_PREFIX}:{session_token}"
        session_data = cache.get(cache_key)
        
        print(f"DEBUG: Session validation - Cache key: {cache_key}")
        print(f"DEBUG: Session validation - Session data: {session_data}")
        
        if not session_data:
            print("DEBUG: Session validation - No session data found in cache")
            raise ValueError("Invalid or expired session")
        
        # Check if session is active
        if not session_data.get('is_active', False):
            print("DEBUG: Session validation - Session is not active")
            raise ValueError("Session has been terminated")
        
        # Check expiration
        expires_at = timezone.datetime.fromisoformat(session_data['expires_at'])
        if timezone.now() > expires_at:
            print("DEBUG: Session validation - Session has expired")
            # Clean up expired session
            cache.delete(cache_key)
            student_session_key = f"{cls.CACHE_PREFIX}:student:{session_data['student_id']}"
            cache.delete(student_session_key)
            raise ValueError("Session has expired")
        
        # Update last activity
        session_data['last_activity'] = timezone.now().isoformat()
        cache.set(cache_key, session_data, cls.SESSION_TIMEOUT)
        
        print("DEBUG: Session validation - Session is valid")
        return session_data
    
    @classmethod
    def refresh_session(cls, session_token: str) -> dict:
        """
        Refresh a CBT session (extend expiration)
        
        Args:
            session_token: Session token to refresh
            
        Returns:
            dict: Updated session data
        """
        session_data = cls.validate_session(session_token)
        
        # Extend expiration
        session_data['expires_at'] = (timezone.now() + timedelta(seconds=cls.SESSION_TIMEOUT)).isoformat()
        
        # Update cache
        cache_key = f"{cls.CACHE_PREFIX}:{session_token}"
        cache.set(cache_key, session_data, cls.SESSION_TIMEOUT)
        
        return session_data
    
    @classmethod
    def terminate_session(cls, session_token: str) -> bool:
        """
        Terminate a CBT session
        
        Args:
            session_token: Session token to terminate
            
        Returns:
            bool: True if terminated successfully
        """
        cache_key = f"{cls.CACHE_PREFIX}:{session_token}"
        session_data = cache.get(cache_key)
        
        if not session_data:
            return False
        
        # Mark as inactive
        session_data['is_active'] = False
        session_data['terminated_at'] = timezone.now().isoformat()
        
        # Update cache
        cache.set(cache_key, session_data, cls.SESSION_TIMEOUT)
        
        # Clean up student session mapping
        student_session_key = f"{cls.CACHE_PREFIX}:student:{session_data['student_id']}"
        cache.delete(student_session_key)
        
        return True
    
    @classmethod
    def get_student_session(cls, student_id: str) -> dict:
        """
        Get active session for a student
        
        Args:
            student_id: Student ID or admission number
            
        Returns:
            dict: Session data or None
        """
        try:
            # Find student - try admission number, application number, then ID
            try:
                student = Student.objects.get(admission_number=student_id)
            except Student.DoesNotExist:
                try:
                    student = Student.objects.get(application_number=student_id)
                except Student.DoesNotExist:
                    try:
                        student = Student.objects.get(id=student_id)
                    except Student.DoesNotExist:
                        return None
            
            # Get session token
            student_session_key = f"{cls.CACHE_PREFIX}:student:{student.id}"
            session_token = cache.get(student_session_key)
            
            if not session_token:
                return None
            
            # Get session data
            return cls.validate_session(session_token)
            
        except Exception:
            return None
    
    @classmethod
    def cleanup_expired_sessions(cls):
        """
        Clean up expired sessions
        This should be run periodically via a cron job
        """
        # This would require scanning all cache keys
        # In production, use Redis with TTL or a background task
        pass
    
    @classmethod
    def get_session_stats(cls) -> dict:
        """
        Get session statistics
        """
        # This would require scanning all cache keys
        # For production, consider maintaining stats in a separate cache key
        return {
            'active_sessions': 0,
            'total_sessions_created': 0,
            'expired_sessions': 0
        }
    
    @classmethod
    def _generate_session_token(cls) -> str:
        """Generate a secure session token"""
        return secrets.token_urlsafe(32)
