"""
CBT Passcode Service - Cache-based passcode management
"""
import secrets
import string
from datetime import timedelta
from django.core.cache import cache 
from django.utils import timezone
from django.contrib.auth import get_user_model
from api.models import Student

User = get_user_model()


class CBTPasscodeService:
    """Service for managing CBT passcodes using cache"""
    
    CACHE_PREFIX = "cbt_passcode"
    CACHE_TIMEOUT = 7200  # 2 hours default
    
    @classmethod
    def generate_passcode(cls, student_id: str, expires_in_hours: int = 2, created_by: User = None) -> dict:
        """
        Generate a new CBT passcode and store it in cache
        
        Args:
            student_id: Student ID or admission number
            expires_in_hours: Hours until passcode expires
            created_by: Admin user who created the passcode
            
        Returns:
            dict: Passcode information
        """
        try:
            # Find student
            try:
                student = Student.objects.get(admission_number=student_id)
            except Student.DoesNotExist:
                try:
                    student = Student.objects.get(id=student_id)
                except Student.DoesNotExist:
                    raise ValueError("Student not found")
            
            # Check for existing active passcode
            existing_passcode = cls.get_active_passcode(student_id)
            if existing_passcode:
                raise ValueError(f"Student already has an active passcode: {existing_passcode['passcode']}")
            
            # Generate 6-digit passcode
            passcode = cls._generate_passcode()
            
            # Create passcode data - minimal data for authentication only
            passcode_data = {
                'passcode': passcode,
                'student_id': str(student.id),
                'student_admission_number': student.admission_number or '',
                'created_by_id': created_by.id if created_by else None,
                'created_by_name': created_by.email if created_by else None,
                'created_at': timezone.now().isoformat(),
                'expires_at': (timezone.now() + timedelta(hours=expires_in_hours)).isoformat(),
                'status': 'active',
                'used_at': None,
                'ip_address': None,
                'user_agent': None
            }
            
            # Store in cache
            cache_key = f"{cls.CACHE_PREFIX}:{passcode}"
            cache_timeout = expires_in_hours * 3600  # Convert to seconds
            cache.set(cache_key, passcode_data, cache_timeout)
            
            # Also store by student ID for quick lookup
            student_cache_key = f"{cls.CACHE_PREFIX}:student:{student_id}"
            cache.set(student_cache_key, passcode, cache_timeout)
            
            # Add to active list for admin view
            active_list = cache.get(f"{cls.CACHE_PREFIX}:active_list", [])
            if passcode not in active_list:
                active_list.append(passcode)
                cache.set(f"{cls.CACHE_PREFIX}:active_list", active_list, cache_timeout)
            
            return passcode_data
        
        except Exception as e:
            raise ValueError(f"Failed to generate passcode: {str(e)}")
    
    @classmethod
    def validate_passcode(cls, passcode: str, student_id: str = None) -> dict:
        """
        Validate a CBT passcode
        
        Args:
            passcode: 6-digit passcode
            student_id: Optional student ID for additional validation
            
        Returns:
            dict: Passcode data if valid
            
        Raises:
            ValueError: If passcode is invalid
        """
        cache_key = f"{cls.CACHE_PREFIX}:{passcode}"
        passcode_data = cache.get(cache_key)
        
        if not passcode_data:
            raise ValueError("Invalid or expired passcode")
        
        # Check if passcode is still active
        if passcode_data.get('status') != 'active':
            raise ValueError("Passcode has been used or revoked")
        
        # Check expiration
        expires_at = timezone.datetime.fromisoformat(passcode_data['expires_at'])
        if timezone.now() > expires_at:
            # Clean up expired passcode
            cache.delete(cache_key)
            student_cache_key = f"{cls.CACHE_PREFIX}:student:{passcode_data['student_id']}"
            cache.delete(student_cache_key)
            raise ValueError("Passcode has expired")
        
        # Additional student validation if provided
        if student_id and passcode_data['student_id'] != str(student_id):
            raise ValueError("Passcode does not belong to this student")
        
        return passcode_data
    
    @classmethod
    def use_passcode(cls, passcode: str, ip_address: str = None, user_agent: str = None) -> dict:
        """
        Use a passcode (mark as used)
        
        Args:
            passcode: 6-digit passcode
            ip_address: IP address of the user
            user_agent: User agent string
            
        Returns:
            dict: Updated passcode data
        """
        cache_key = f"{cls.CACHE_PREFIX}:{passcode}"
        passcode_data = cache.get(cache_key)
        
        if not passcode_data:
            raise ValueError("Invalid or expired passcode")
        
        # Mark as used
        passcode_data['status'] = 'used'
        passcode_data['used_at'] = timezone.now().isoformat()
        passcode_data['ip_address'] = ip_address
        passcode_data['user_agent'] = user_agent
        
        # Update cache
        cache.set(cache_key, passcode_data, cls.CACHE_TIMEOUT)
        
        # Clean up student cache
        student_cache_key = f"{cls.CACHE_PREFIX}:student:{passcode_data['student_id']}"
        cache.delete(student_cache_key)
        
        # Remove from active list
        active_list = cache.get(f"{cls.CACHE_PREFIX}:active_list", [])
        if passcode in active_list:
            active_list.remove(passcode)
            cache.set(f"{cls.CACHE_PREFIX}:active_list", active_list, cls.CACHE_TIMEOUT)
        
        return passcode_data
    
    @classmethod
    def revoke_passcode(cls, passcode: str) -> bool:
        """
        Revoke a passcode
        
        Args:
            passcode: 6-digit passcode
            
        Returns:
            bool: True if revoked successfully
        """
        cache_key = f"{cls.CACHE_PREFIX}:{passcode}"
        passcode_data = cache.get(cache_key)
        
        if not passcode_data:
            return False
        
        # Mark as revoked
        passcode_data['status'] = 'revoked'
        cache.set(cache_key, passcode_data, cls.CACHE_TIMEOUT)
        
        # Clean up student cache
        student_cache_key = f"{cls.CACHE_PREFIX}:student:{passcode_data['student_id']}"
        cache.delete(student_cache_key)
        
        return True
    
    @classmethod
    def get_active_passcode(cls, student_id: str) -> dict:
        """
        Get active passcode for a student
        
        Args:
            student_id: Student ID or admission number
            
        Returns:
            dict: Active passcode data or None
        """
        try:
            # Find student
            try:
                student = Student.objects.get(admission_number=student_id)
            except Student.DoesNotExist:
                try:
                    student = Student.objects.get(id=student_id)
                except Student.DoesNotExist:
                    return None
            
            # Get passcode from student cache
            student_cache_key = f"{cls.CACHE_PREFIX}:student:{student.id}"
            passcode = cache.get(student_cache_key)
            
            if not passcode:
                return None
            
            # Get full passcode data
            cache_key = f"{cls.CACHE_PREFIX}:{passcode}"
            passcode_data = cache.get(cache_key)
            
            if not passcode_data or passcode_data.get('status') != 'active':
                return None
            
            # Check expiration
            expires_at = timezone.datetime.fromisoformat(passcode_data['expires_at'])
            if timezone.now() > expires_at:
                # Clean up expired passcode
                cache.delete(cache_key)
                cache.delete(student_cache_key)
                return None
            
            return passcode_data
            
        except Exception:
            return None
    
    @classmethod
    def get_all_active_passcodes(cls) -> list:
        """
        Get all active passcodes (for admin view)
        """
        # Get the list of active passcodes from our tracking cache
        active_list = cache.get(f"{cls.CACHE_PREFIX}:active_list", [])
        active_passcodes = []
        now = timezone.now()
        
        for passcode in active_list:
            passcode_data = cache.get(f"{cls.CACHE_PREFIX}:{passcode}")
            if passcode_data and passcode_data.get('status') == 'active':
                # Check if not expired
                expires_at = timezone.datetime.fromisoformat(passcode_data['expires_at'])
                if now < expires_at:
                    # Calculate time remaining
                    time_remaining = expires_at - now
                    hours, remainder = divmod(time_remaining.seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                    
                    passcode_data['time_remaining'] = f"{hours}h {minutes}m"
                    active_passcodes.append(passcode_data)
                else:
                    # Mark as expired
                    passcode_data['status'] = 'expired'
                    cache.set(f"{cls.CACHE_PREFIX}:{passcode}", passcode_data, timeout=None)
                    # Remove from active list
                    active_list.remove(passcode)
                    cache.set(f"{cls.CACHE_PREFIX}:active_list", active_list, cls.CACHE_TIMEOUT)
        
        return active_passcodes
    
    @classmethod
    def cleanup_expired_passcodes(cls):
        """
        Clean up expired passcodes
        This should be run periodically via a cron job
        """
        # This would require scanning all cache keys
        # In production, use Redis with TTL or a background task
        pass
    
    @classmethod
    def _generate_passcode(cls) -> str:
        """Generate a 6-digit passcode"""
        return ''.join(secrets.choice(string.digits) for _ in range(6))
    
    @classmethod
    def get_passcode_stats(cls) -> dict:
        """
        Get passcode statistics
        """
        stats = {
            'total_passcodes': 0,
            'active_passcodes': 0,
            'used_passcodes': 0,
            'expired_passcodes': 0,
            'revoked_passcodes': 0
        }
        
        # Get the list of active passcodes from our tracking cache
        active_list = cache.get(f"{cls.CACHE_PREFIX}:active_list", [])
        now = timezone.now()
        
        for passcode in active_list:
            passcode_data = cache.get(f"{cls.CACHE_PREFIX}:{passcode}")
            if passcode_data:
                stats['total_passcodes'] += 1
                status = passcode_data.get('status', 'active')
                expires_at = timezone.datetime.fromisoformat(passcode_data['expires_at'])
                
                # Check if expired
                if status == 'active' and now >= expires_at:
                    status = 'expired'
                    passcode_data['status'] = 'expired'
                    cache.set(f"{cls.CACHE_PREFIX}:{passcode}", passcode_data, timeout=None)
                    # Remove from active list
                    active_list.remove(passcode)
                    cache.set(f"{cls.CACHE_PREFIX}:active_list", active_list, cls.CACHE_TIMEOUT)
                
                if status == 'active':
                    stats['active_passcodes'] += 1
                elif status == 'used':
                    stats['used_passcodes'] += 1
                elif status == 'expired':
                    stats['expired_passcodes'] += 1
                elif status == 'revoked':
                    stats['revoked_passcodes'] += 1
        
        return stats
