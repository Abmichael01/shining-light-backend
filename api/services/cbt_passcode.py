"""
CBT Passcode Service - Database and cache-based passcode management
"""
import secrets
import string
from datetime import timedelta
from django.core.cache import cache 
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from api.models import Student, Exam, ExamHall, CBTExamCode

User = get_user_model()


class CBTPasscodeService:
    """Service for managing CBT passcodes using cache"""
    
    CACHE_PREFIX = "cbt_passcode"
    CACHE_TIMEOUT = 7200  # 2 hours default
    
    @classmethod
    def generate_passcode(cls, student_id: str, expires_in_hours: int = 2, created_by: User = None, 
                          exam_id: str = None, exam_hall_id: str = None) -> dict:
        """
        Generate a new CBT passcode and store it in database and cache
        
        Args:
            student_id: Student ID or admission number
            expires_in_hours: Hours until passcode expires
            created_by: Admin user who created the passcode
            exam_id: Optional exam ID this code is for
            exam_hall_id: Optional exam hall ID to assign student to
            
        Returns:
            dict: Passcode information including seat assignment
        """
        try:
            with transaction.atomic():
                # Find student
                try:
                    student = Student.objects.get(admission_number=student_id)
                except Student.DoesNotExist:
                    try:
                        student = Student.objects.get(id=student_id)
                    except Student.DoesNotExist:
                        raise ValueError("Student not found")
                
                # Check for existing active passcode for this student
                existing_code = CBTExamCode.objects.filter(
                    student=student,
                    is_used=False,
                    expires_at__gt=timezone.now()
                ).first()
                
                if existing_code:
                    raise ValueError(f"Student already has an active passcode: {existing_code.code}")
                
                # Get exam if provided
                exam = None
                if exam_id:
                    try:
                        exam = Exam.objects.get(id=exam_id)
                    except Exam.DoesNotExist:
                        raise ValueError("Exam not found")
                
                # Get exam hall and assign seat if provided
                exam_hall = None
                seat_number = None
                
                if exam_hall_id:
                    try:
                        exam_hall = ExamHall.objects.get(id=exam_hall_id, is_active=True)
                    except ExamHall.DoesNotExist:
                        raise ValueError("Exam hall not found or inactive")
                    
                    # Find next available seat in the hall
                    # Get today's date to check same-day seat assignments
                    today = timezone.now().date()
                    
                    # Get all seats that are occupied on the same day (not used yet)
                    # This ensures no two students get the same seat on the same day
                    # Once a student finishes (is_used=True), the seat becomes available
                    occupied_seats_today = CBTExamCode.objects.filter(
                        exam_hall=exam_hall,
                        created_at__date=today,
                        is_used=False,
                        seat_number__isnull=False
                    ).values_list('seat_number', flat=True).distinct()
                    
                    # If exam is provided, also consider exam-specific seats
                    if exam:
                        exam_occupied_seats = CBTExamCode.objects.filter(
                            exam=exam,
                            exam_hall=exam_hall,
                            created_at__date=today,
                            is_used=False,
                            seat_number__isnull=False
                        ).values_list('seat_number', flat=True).distinct()
                        # Combine both sets
                        used_seats = set(list(occupied_seats_today) + list(exam_occupied_seats))
                    else:
                        used_seats = set(occupied_seats_today)
                    
                    # Find first available seat that is not occupied today
                    for seat in range(1, exam_hall.number_of_seats + 1):
                        if seat not in used_seats:
                            seat_number = seat
                            break
                    
                    if not seat_number:
                        raise ValueError(f"No available seats in {exam_hall.name}. All {exam_hall.number_of_seats} seats are occupied.")
                
                # Generate 6-digit passcode (ensure uniqueness)
                passcode = cls._generate_passcode()
                while CBTExamCode.objects.filter(code=passcode).exists():
                    passcode = cls._generate_passcode()
                
                expires_at = timezone.now() + timedelta(hours=expires_in_hours)
                
                # Save to database
                cbt_code = CBTExamCode.objects.create(
                    code=passcode,
                    exam=exam,
                    student=student,
                    exam_hall=exam_hall,
                    seat_number=seat_number,
                    expires_at=expires_at,
                    created_by=created_by,
                    is_used=False
                )
                
                # Create passcode data for cache and response
                passcode_data = {
                    'passcode': passcode,
                    'id': cbt_code.id,
                    'student_id': str(student.id),
                    'student_admission_number': student.admission_number or '',
                    'student_name': student.get_full_name() if hasattr(student, 'get_full_name') else '',
                    'exam_id': exam.id if exam else None,
                    'exam_title': exam.title if exam else None,
                    'exam_hall_id': exam_hall.id if exam_hall else None,
                    'exam_hall_name': exam_hall.name if exam_hall else None,
                    'seat_number': seat_number,
                    'created_by_id': created_by.id if created_by else None,
                    'created_by_name': created_by.email if created_by else None,
                    'created_at': timezone.now().isoformat(),
                    'expires_at': expires_at.isoformat(),
                    'status': 'active',
                    'used_at': None,
                    'is_used': False
                }
                
                # Store in cache for quick lookup
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
        Validate a CBT passcode (checks both database and cache)
        
        Args:
            passcode: 6-digit passcode
            student_id: Optional student ID for additional validation
            
        Returns:
            dict: Passcode data if valid
            
        Raises:
            ValueError: If passcode is invalid
        """
        # First check cache for quick lookup
        cache_key = f"{cls.CACHE_PREFIX}:{passcode}"
        passcode_data = cache.get(cache_key)
        
        # If not in cache, check database
        if not passcode_data:
            try:
                cbt_code = CBTExamCode.objects.get(code=passcode)
                
                # Check if used
                if cbt_code.is_used:
                    raise ValueError("Passcode has already been used")
                
                # Check expiration
                if timezone.now() > cbt_code.expires_at:
                    raise ValueError("Passcode has expired")
                
                # Build passcode data from database record
                passcode_data = {
                    'passcode': cbt_code.code,
                    'id': cbt_code.id,
                    'student_id': str(cbt_code.student.id),
                    'student_admission_number': cbt_code.student.admission_number or '',
                    'student_name': cbt_code.student.get_full_name() if hasattr(cbt_code.student, 'get_full_name') else '',
                    'exam_id': cbt_code.exam.id if cbt_code.exam else None,
                    'exam_title': cbt_code.exam.title if cbt_code.exam else None,
                    'exam_hall_id': cbt_code.exam_hall.id if cbt_code.exam_hall else None,
                    'exam_hall_name': cbt_code.exam_hall.name if cbt_code.exam_hall else None,
                    'seat_number': cbt_code.seat_number,
                    'created_by_id': cbt_code.created_by.id if cbt_code.created_by else None,
                    'created_at': cbt_code.created_at.isoformat(),
                    'expires_at': cbt_code.expires_at.isoformat(),
                    'status': 'active',
                    'is_used': False
                }
                
                # Cache it for future lookups
                time_remaining = (cbt_code.expires_at - timezone.now()).total_seconds()
                if time_remaining > 0:
                    cache.set(cache_key, passcode_data, int(time_remaining))
            except CBTExamCode.DoesNotExist:
                raise ValueError("Invalid passcode")
        
        # Check if passcode is still active
        if passcode_data.get('status') != 'active' or passcode_data.get('is_used'):
            raise ValueError("Passcode has been used or revoked")
        
        # Check expiration
        if isinstance(passcode_data['expires_at'], str):
            expires_at = timezone.datetime.fromisoformat(passcode_data['expires_at'])
        else:
            expires_at = passcode_data['expires_at']
            
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
        Use a passcode (mark as used in database and cache)
        
        Args:
            passcode: 6-digit passcode
            ip_address: IP address of the user
            user_agent: User agent string
            
        Returns:
            dict: Updated passcode data
        """
        with transaction.atomic():
            # Get from database
            try:
                cbt_code = CBTExamCode.objects.get(code=passcode)
            except CBTExamCode.DoesNotExist:
                raise ValueError("Invalid passcode")
            
            # Validate it's not already used
            if cbt_code.is_used:
                raise ValueError("Passcode has already been used")
            
            # Mark as used in database
            cbt_code.mark_as_used()
            
            # Build updated passcode data
            passcode_data = {
                'passcode': cbt_code.code,
                'id': cbt_code.id,
                'student_id': str(cbt_code.student.id),
                'student_admission_number': cbt_code.student.admission_number or '',
                'student_name': cbt_code.student.get_full_name() if hasattr(cbt_code.student, 'get_full_name') else '',
                'exam_id': cbt_code.exam.id if cbt_code.exam else None,
                'exam_title': cbt_code.exam.title if cbt_code.exam else None,
                'exam_hall_id': cbt_code.exam_hall.id if cbt_code.exam_hall else None,
                'exam_hall_name': cbt_code.exam_hall.name if cbt_code.exam_hall else None,
                'seat_number': cbt_code.seat_number,
                'created_by_id': cbt_code.created_by.id if cbt_code.created_by else None,
                'created_at': cbt_code.created_at.isoformat(),
                'expires_at': cbt_code.expires_at.isoformat(),
                'status': 'used',
                'is_used': True,
                'used_at': cbt_code.used_at.isoformat() if cbt_code.used_at else None,
                'ip_address': ip_address,
                'user_agent': user_agent
            }
            
            # Update cache
            cache_key = f"{cls.CACHE_PREFIX}:{passcode}"
            cache.set(cache_key, passcode_data, cls.CACHE_TIMEOUT)
            
            # Clean up student cache
            student_cache_key = f"{cls.CACHE_PREFIX}:student:{cbt_code.student.id}"
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
        Revoke a passcode (mark as used in database)
        
        Args:
            passcode: 6-digit passcode
            
        Returns:
            bool: True if revoked successfully
        """
        try:
            cbt_code = CBTExamCode.objects.get(code=passcode)
            
            # Mark as used (we use is_used instead of a separate revoked status)
            if not cbt_code.is_used:
                cbt_code.mark_as_used()
            
            # Update cache
            cache_key = f"{cls.CACHE_PREFIX}:{passcode}"
            passcode_data = cache.get(cache_key)
            if passcode_data:
                passcode_data['status'] = 'revoked'
                passcode_data['is_used'] = True
                cache.set(cache_key, passcode_data, cls.CACHE_TIMEOUT)
            
            # Clean up student cache
            student_cache_key = f"{cls.CACHE_PREFIX}:student:{cbt_code.student.id}"
            cache.delete(student_cache_key)
            
            return True
        except CBTExamCode.DoesNotExist:
            return False
    
    @classmethod
    def get_active_passcode(cls, student_id: str) -> dict:
        """
        Get active passcode for a student (checks both database and cache)
        
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
            
            # Get passcode from student cache first
            student_cache_key = f"{cls.CACHE_PREFIX}:student:{student.id}"
            passcode = cache.get(student_cache_key)
            
            # If not in cache, check database
            if not passcode:
                cbt_code = CBTExamCode.objects.filter(
                    student=student,
                    is_used=False,
                    expires_at__gt=timezone.now()
                ).order_by('-created_at').first()
                
                if not cbt_code:
                    return None
                
                passcode = cbt_code.code
            
            # Get full passcode data from cache or database
            cache_key = f"{cls.CACHE_PREFIX}:{passcode}"
            passcode_data = cache.get(cache_key)
            
            if not passcode_data:
                # Get from database
                try:
                    cbt_code = CBTExamCode.objects.get(code=passcode, student=student)
                    if cbt_code.is_used or timezone.now() > cbt_code.expires_at:
                        return None
                    
                    passcode_data = {
                        'passcode': cbt_code.code,
                        'id': cbt_code.id,
                        'student_id': str(cbt_code.student.id),
                        'student_admission_number': cbt_code.student.admission_number or '',
                        'student_name': cbt_code.student.get_full_name() if hasattr(cbt_code.student, 'get_full_name') else '',
                        'exam_id': cbt_code.exam.id if cbt_code.exam else None,
                        'exam_title': cbt_code.exam.title if cbt_code.exam else None,
                        'exam_hall_id': cbt_code.exam_hall.id if cbt_code.exam_hall else None,
                        'exam_hall_name': cbt_code.exam_hall.name if cbt_code.exam_hall else None,
                        'seat_number': cbt_code.seat_number,
                        'created_at': cbt_code.created_at.isoformat(),
                        'expires_at': cbt_code.expires_at.isoformat(),
                        'status': 'active',
                        'is_used': False
                    }
                    
                    # Cache it
                    time_remaining = (cbt_code.expires_at - timezone.now()).total_seconds()
                    if time_remaining > 0:
                        cache.set(cache_key, passcode_data, int(time_remaining))
                        cache.set(student_cache_key, passcode, int(time_remaining))
                except CBTExamCode.DoesNotExist:
                    return None
            
            if not passcode_data or passcode_data.get('status') != 'active' or passcode_data.get('is_used'):
                return None
            
            # Check expiration
            if isinstance(passcode_data['expires_at'], str):
                expires_at = timezone.datetime.fromisoformat(passcode_data['expires_at'])
            else:
                expires_at = passcode_data['expires_at']
                
            if timezone.now() > expires_at:
                # Clean up expired passcode
                cache.delete(cache_key)
                cache.delete(student_cache_key)
                return None
            
            return passcode_data
            
        except Exception:
            return None
    
    @classmethod
    def get_all_passcodes(cls, include_expired: bool = False) -> list:
        """
        Get all passcodes (for admin view) - from database
        Can include expired passcodes if include_expired is True
        
        Args:
            include_expired: If True, include expired and used passcodes
            
        Returns:
            list: List of passcode dictionaries
        """
        now = timezone.now()
        
        if include_expired:
            # Get all passcodes
            codes = CBTExamCode.objects.all()
        else:
            # Get only active passcodes
            codes = CBTExamCode.objects.filter(
                is_used=False,
                expires_at__gt=now
            )
        
        codes = codes.select_related('student', 'exam', 'exam_hall', 'created_by').order_by('-created_at')
        
        passcodes = []
        for cbt_code in codes:
            # Determine status
            if cbt_code.is_used:
                status = 'used'
            elif cbt_code.expires_at <= now:
                status = 'expired'
            else:
                status = 'active'
            
            # Calculate time remaining for active passcodes
            time_remaining = None
            if status == 'active':
                time_remaining = cbt_code.expires_at - now
                hours, remainder = divmod(time_remaining.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                time_remaining = f"{hours}h {minutes}m"
            
            passcode_data = {
                'passcode': cbt_code.code,
                'id': cbt_code.id,
                'student_id': str(cbt_code.student.id),
                'student_admission_number': cbt_code.student.admission_number or '',
                'student_name': cbt_code.student.get_full_name() if hasattr(cbt_code.student, 'get_full_name') else '',
                'exam_id': cbt_code.exam.id if cbt_code.exam else None,
                'exam_title': cbt_code.exam.title if cbt_code.exam else None,
                'exam_hall_id': cbt_code.exam_hall.id if cbt_code.exam_hall else None,
                'exam_hall_name': cbt_code.exam_hall.name if cbt_code.exam_hall else None,
                'seat_number': cbt_code.seat_number,
                'status': status,
                'is_used': cbt_code.is_used,
                'created_by_id': cbt_code.created_by.id if cbt_code.created_by else None,
                'created_by_name': cbt_code.created_by.email if cbt_code.created_by else None,
                'created_at': cbt_code.created_at.isoformat(),
                'expires_at': cbt_code.expires_at.isoformat(),
                'used_at': cbt_code.used_at.isoformat() if cbt_code.used_at else None,
                'time_remaining': time_remaining
            }
            passcodes.append(passcode_data)
        
        return passcodes
    
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
        Get passcode statistics from database
        """
        now = timezone.now()
        
        # Get stats from database
        stats = {
            'total_passcodes': CBTExamCode.objects.count(),
            'active_passcodes': CBTExamCode.objects.filter(is_used=False, expires_at__gt=now).count(),
            'used_passcodes': CBTExamCode.objects.filter(is_used=True).count(),
            'expired_passcodes': CBTExamCode.objects.filter(is_used=False, expires_at__lte=now).count(),
            'revoked_passcodes': 0  # Not tracked separately currently
        }
        
        return stats
