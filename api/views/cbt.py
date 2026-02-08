from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model
from api.services.cbt_passcode import CBTPasscodeService
from api.services.cbt_session import CBTSessionService
from api.permissions import IsAdminOrStaff
from api.authentication import CBTSessionAuthentication
from api.models import Exam, Student, Subject, Question
from api.serializers.academic import ExamSerializer, QuestionSerializer
from api.serializers.student import CBTStudentProfileSerializer
from django.utils import timezone
from django.conf import settings
from api.utils.exam_generator import generate_applicant_exam
from decimal import Decimal
import random
import json
import os

User = get_user_model()


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def generate_passcode(request):
    """Generate a new CBT passcode with optional exam and exam hall assignment"""
    try:
        student_id = request.data.get('student_id')
        expires_in_hours = request.data.get('expires_in_hours', 2)
        exam_id = request.data.get('exam_id')
        exam_hall_id = request.data.get('exam_hall_id')
        
        if not student_id:
            return Response(
                {'error': 'Student ID is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate expires_in_hours
        try:
            expires_in_hours = int(expires_in_hours)
            if not 1 <= expires_in_hours <= 24:
                raise ValueError()
        except (ValueError, TypeError):
            return Response(
                {'error': 'Expires in hours must be between 1 and 24'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate passcode with exam and hall assignment
        passcode_data = CBTPasscodeService.generate_passcode(
            student_id=student_id,
            expires_in_hours=expires_in_hours,
            created_by=request.user,
            exam_id=exam_id,
            exam_hall_id=exam_hall_id
        )
        
        return Response(passcode_data, status=status.HTTP_201_CREATED)
        
    except ValueError as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': f'Failed to generate passcode: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def login_with_passcode(request):
    """Student login with passcode"""
    try:
        admission_number = request.data.get('admission_number')
        passcode = request.data.get('passcode')
        
        if not all([admission_number, passcode]):
            return Response(
                {'error': 'Admission number and passcode are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate student credentials
        from api.models import Student
        try:
            student = Student.objects.get(admission_number=admission_number)
        except Student.DoesNotExist:
            return Response(
                {'error': 'Invalid admission number'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # No password check needed - passcode is sufficient
        
        try:
            passcode_data = CBTPasscodeService.validate_passcode(
                passcode=passcode,
                student_id=str(student.id)
            )
        except ValueError:
            return Response(
                {'error': 'Invalid admission number or passcode'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            used_passcode_data = CBTPasscodeService.use_passcode(
                passcode=passcode,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        except ValueError:
            return Response(
                {'error': 'Invalid admission number or passcode'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create CBT session
        session_data = CBTSessionService.create_session(
            student_id=student.admission_number,
            passcode=passcode,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # Return student, session, and passcode information - minimal data for authentication
        response = Response({
            'success': True,
            'message': 'Login successful',
            'student': {
                'id': student.id,
                'admission_number': student.admission_number or '',
            },
            'session': {
                'token': session_data['session_token'],
                'expires_at': session_data['expires_at'],
                'created_at': session_data['created_at']
            },
            'passcode': {
                'used_at': used_passcode_data.get('used_at'),
                'seat_number': used_passcode_data.get('seat_number'),
                'exam_hall_id': used_passcode_data.get('exam_hall_id'),
                'exam_id': used_passcode_data.get('exam_id'),
            }
        }, status=status.HTTP_200_OK)
        
        # Determine cookie settings based on standard session config
        cookie_kwargs = {
            'max_age': 7200,  # 2 hours
            'httponly': True,
            'secure': getattr(settings, 'SESSION_COOKIE_SECURE', False),
            'samesite': getattr(settings, 'SESSION_COOKIE_SAMESITE', 'Lax'),
        }
        cookie_domain = getattr(settings, 'SESSION_COOKIE_DOMAIN', None)
        if cookie_domain:
            cookie_kwargs['domain'] = cookie_domain
        
        # Set CBT session cookie
        response.set_cookie(
            'cbt_session_token',
            session_data['session_token'],
            **cookie_kwargs
        )
        
        return response
        
    except ValueError as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': f'Login failed: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def revoke_passcode(request):
    """Revoke a CBT passcode"""
    try:
        passcode = request.data.get('passcode')
        
        if not passcode:
            return Response(
                {'error': 'Passcode is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success = CBTPasscodeService.revoke_passcode(passcode)
        
        if success:
            return Response({
                'success': True,
                'message': 'Passcode revoked successfully'
            })
        else:
            return Response(
                {'error': 'Passcode not found or already expired'}, 
                status=status.HTTP_404_NOT_FOUND
            )
            
    except Exception as e:
        return Response(
            {'error': f'Failed to revoke passcode: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def get_active_passcode(request):
    """Get active passcode for a student"""
    try:
        student_id = request.query_params.get('student_id')
        
        if not student_id:
            return Response(
                {'error': 'Student ID is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        passcode_data = CBTPasscodeService.get_active_passcode(student_id)
        
        if passcode_data:
            return Response(passcode_data)
        else:
            return Response(
                {'error': 'No active passcode found for this student'}, 
                status=status.HTTP_404_NOT_FOUND
            )
            
    except Exception as e:
        return Response(
            {'error': f'Failed to get passcode: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def get_passcode_stats(request):
    """Get passcode statistics"""
    try:
        stats = CBTPasscodeService.get_passcode_stats()
        return Response(stats)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to get stats: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def get_all_active_passcodes(request):
    """Get all active passcodes (deprecated - use get_all_passcodes)"""
    try:
        include_expired = request.query_params.get('include_expired', 'false').lower() == 'true'
        passcodes = CBTPasscodeService.get_all_passcodes(include_expired=include_expired)
        return Response(passcodes)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to get passcodes: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def get_all_passcodes(request):
    """Get all passcodes, optionally including expired ones"""
    try:
        include_expired = request.query_params.get('include_expired', 'true').lower() == 'true'
        passcodes = CBTPasscodeService.get_all_passcodes(include_expired=include_expired)
        return Response(passcodes)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to get passcodes: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def delete_all_passcodes(request):
    """Delete all CBT passcodes"""
    try:
        deleted = CBTPasscodeService.delete_all_passcodes()
        return Response(
            {
                'success': True,
                'deleted_count': deleted,
                'message': 'All passcodes deleted successfully'
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'error': f'Failed to delete passcodes: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def get_all_passcodes(request):
    """Get all passcodes, optionally including expired ones"""
    try:
        include_expired = request.query_params.get('include_expired', 'true').lower() == 'true'
        passcodes = CBTPasscodeService.get_all_passcodes(include_expired=include_expired)
        return Response(passcodes)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to get passcodes: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# CBT Session Management Endpoints

@api_view(['GET'])
@permission_classes([AllowAny])
def validate_cbt_session(request):
    """Validate CBT session token"""
    try:
        session_token = request.META.get('HTTP_X_CBT_SESSION') or request.COOKIES.get('cbt_session_token')
        
        if not session_token:
            return Response(
                {'error': 'CBT session token required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        session_data = CBTSessionService.validate_session(session_token)
        
        return Response({
            'valid': True,
            'session': session_data
        }, status=status.HTTP_200_OK)
        
    except ValueError as e:
        return Response(
            {'valid': False, 'error': str(e)}, 
            status=status.HTTP_401_UNAUTHORIZED
        )
    except Exception as e:
        return Response(
            {'error': f'Failed to validate session: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_cbt_session(request):
    """Refresh CBT session token"""
    try:
        session_token = request.META.get('HTTP_X_CBT_SESSION') or request.COOKIES.get('cbt_session_token')
        
        if not session_token:
            return Response(
                {'error': 'CBT session token required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        session_data = CBTSessionService.refresh_session(session_token)
        
        response = Response({
            'success': True,
            'session': session_data
        }, status=status.HTTP_200_OK)
        
        cookie_kwargs = {
            'max_age': 7200,  # 2 hours
            'httponly': True,
            'secure': getattr(settings, 'SESSION_COOKIE_SECURE', False),
            'samesite': getattr(settings, 'SESSION_COOKIE_SAMESITE', 'Lax'),
        }
        cookie_domain = getattr(settings, 'SESSION_COOKIE_DOMAIN', None)
        if cookie_domain:
            cookie_kwargs['domain'] = cookie_domain
        
        # Update cookie
        response.set_cookie(
            'cbt_session_token',
            session_data['session_token'],
            **cookie_kwargs
        )
        
        return response
        
    except ValueError as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_401_UNAUTHORIZED
        )
    except Exception as e:
        return Response(
            {'error': f'Failed to refresh session: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def logout_cbt_session(request):
    """Logout CBT session"""
    try:
        session_token = request.META.get('HTTP_X_CBT_SESSION') or request.COOKIES.get('cbt_session_token')
        
        if not session_token:
            return Response(
                {'error': 'CBT session token required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        success = CBTSessionService.terminate_session(session_token)
        
        response = Response({
            'success': success,
            'message': 'Session terminated successfully' if success else 'Session not found'
        }, status=status.HTTP_200_OK)
        
        cookie_domain = getattr(settings, 'SESSION_COOKIE_DOMAIN', None)
        cookie_samesite = getattr(settings, 'SESSION_COOKIE_SAMESITE', 'Lax')
        
        # Clear cookie
        response.delete_cookie(
            'cbt_session_token',
            domain=cookie_domain,
            samesite=cookie_samesite
        )
        
        return response
        
    except Exception as e:
        return Response(
            {'error': f'Failed to logout: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrStaff])
def get_cbt_session_stats(request):
    """Get CBT session statistics"""
    try:
        stats = CBTSessionService.get_session_stats()
        return Response(stats, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'Failed to get session stats: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([CBTSessionAuthentication])
@permission_classes([AllowAny])
def get_cbt_student_profile(request):
    """Get minimal student profile for CBT portal"""
    try:
        session_student = request.user
        
        # Fetch actual student record with prefetch for subject registrations
        try:
            student = Student.objects.select_related('school', 'class_model').prefetch_related(
                'subject_registrations__subject',
                'subject_registrations__session_term'
            ).get(
                admission_number=session_student.admission_number
            )
        except Student.DoesNotExist:
            return Response(
                {'error': 'Student not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = CBTStudentProfileSerializer(student)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch student profile: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# CBT Exam Endpoints
@api_view(['GET'])
@authentication_classes([CBTSessionAuthentication])
@permission_classes([AllowAny])
def get_cbt_exams(request):
    """Get exams available for CBT students"""
    try:
        # Get student from CBT session
        student = request.user
        
        # Get student record
        from api.models import Student, StudentSubject
        try:
            student_obj = Student.objects.get(admission_number=student.admission_number)
        except Student.DoesNotExist:
            return Response(
                {'error': 'Student not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get student's registered subjects (active registrations only)
        registered_subjects = StudentSubject.objects.filter(
            student=student_obj,
            is_active=True
        ).values_list('subject_id', flat=True)
        
        print(f"DEBUG: Student {student_obj.admission_number} registered subjects: {list(registered_subjects)}")
        
        # Get exams that are active and for registered subjects
        exams = Exam.objects.filter(
            status='active',
            subject_id__in=registered_subjects  # Only exams for registered subjects
        ).order_by('-created_at')
        
        # Filter out exams that the student has already taken
        from api.models import StudentExam
        taken_exams = StudentExam.objects.filter(
            student=student_obj
        ).values_list('exam', flat=True)
        
        print(f"DEBUG: Student {student_obj.admission_number} has taken exams: {list(taken_exams)}")
        print(f"DEBUG: Total active exams for registered subjects: {exams.count()}")
        
        available_exams = exams.exclude(id__in=taken_exams)
        
        print(f"DEBUG: Available exams after filtering: {available_exams.count()}")
        
        # Serialize exams
        serializer = ExamSerializer(available_exams, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch exams: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([CBTSessionAuthentication])
@permission_classes([AllowAny])
def get_cbt_exam(request, exam_id):
    """Get a specific exam for CBT students"""
    try:
        # Get student from CBT session
        student = request.user
        
        # Get exam
        try:
            exam = Exam.objects.get(id=exam_id, status='active')
        except Exam.DoesNotExist:
            return Response(
                {'error': 'Exam not found or not available'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if exam is currently active
        now = timezone.now()
        # Check if exam is active (admin-controlled)
        if exam.status != 'active':
            return Response(
                {'error': 'Exam is not currently active'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Serialize exam
        context = {'request': request}
        
        # If it's an applicant exam, ensure we have a generated set of questions
        if exam.is_applicant_exam:
            # We need the real Student object
            from api.models import Student
            try:
                student_obj = Student.objects.get(admission_number=student.admission_number)
                
                # Generate or get existing exam session with randomized questions
                student_exam = generate_applicant_exam(student_obj, exam)
                
                # If we have a question order, pass it to the serializer
                if student_exam and student_exam.question_order:
                    context['specific_question_ids'] = student_exam.question_order
                    print(f"DEBUG: Serving specific questions for applicant: {len(student_exam.question_order)}")
            except Student.DoesNotExist:
                pass  # Fallback to default behavior if student not found (shouldn't happen)
                
        serializer = ExamSerializer(exam, context=context)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch exam: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Practice CBT Endpoints
@api_view(['GET'])
@permission_classes([AllowAny])
def get_practice_subjects(request):
    """Get available subjects for practice exams"""
    try:
        subjects = Subject.objects.all().values(
            'id', 'name', 'code'
        )
        return Response(list(subjects), status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch subjects: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def create_practice_exam(request):
    """Create a practice exam with dummy data from JSON files"""
    try:
        subject_id = request.data.get('subject_id')
        question_count = request.data.get('question_count', 10)
        difficulty = request.data.get('difficulty', 'medium')
        
        # Load practice exam data from JSON files
        practice_exams_dir = os.path.join(settings.BASE_DIR, 'api', 'data', 'exam_practice')
        
        # Select a practice exam file based on random selection
        practice_exam_files = [f for f in os.listdir(practice_exams_dir) if f.endswith('.json')]
        
        if not practice_exam_files:
            return Response(
                {'error': 'No practice exams available'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Select random practice exam
        selected_file = random.choice(practice_exam_files)
        file_path = os.path.join(practice_exams_dir, selected_file)
        
        # Load practice exam data
        with open(file_path, 'r') as f:
            practice_exam = json.load(f)
        
        # Update some fields to make it dynamic
        practice_exam['created_at'] = timezone.now().isoformat()
        practice_exam['is_practice'] = True
        practice_exam['id'] = f"PRACTICE-{random.randint(100000, 999999)}"
        
        return Response(practice_exam, status=status.HTTP_200_OK)
        
    except FileNotFoundError:
        return Response(
            {'error': 'Practice exam data not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'Failed to create practice exam: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@authentication_classes([CBTSessionAuthentication])
@permission_classes([AllowAny])
def submit_cbt_exam(request, exam_id):
    """Submit CBT exam answers and get results"""
    try:
        answers = request.data.get('answers', [])
        
        if not exam_id:
            return Response(
                {'error': 'Exam ID is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get student from CBT session
        student = request.user
        
        # Get exam
        try:
            exam = Exam.objects.get(id=exam_id, status='active')
        except Exam.DoesNotExist:
            return Response(
                {'error': 'Exam not found or not available'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get student record
        from api.models import Student, StudentExam, StudentAnswer, StudentSubject
        try:
            student_obj = Student.objects.get(admission_number=student.admission_number)
        except Student.DoesNotExist:
            return Response(
                {'error': 'Student not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if student has already taken this exam
        if StudentExam.objects.filter(student=student_obj, exam=exam).exists():
            print(f"DEBUG: Student {student_obj.admission_number} has already taken exam {exam.id}")
            return Response(
                {'error': 'You have already taken this exam'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate score based on correct answers
        questions_list = list(exam.questions.all())
        total_questions = len(questions_list)
        correct_answers = 0
        
        for answer in answers:
            question_id = answer.get('question_id')
            selected_option = answer.get('selected_option')
            
            # Find the question and check if answer is correct
            for question in questions_list:
                if str(question.id) == str(question_id):
                    if question.correct_answer.upper() == selected_option.upper():
                        correct_answers += 1
                    break
        
        score = (correct_answers / total_questions * 100) if total_questions > 0 else 0
        
        # Determine grade
        if score >= 80:
            grade = 'A'
        elif score >= 70:
            grade = 'B'
        elif score >= 60:
            grade = 'C'
        elif score >= 50:
            grade = 'D'
        else:
            grade = 'F'
        
        # Generate feedback
        feedback = []
        if score >= exam.pass_mark:
            feedback.append(f"Congratulations! You passed with {score:.1f}%")
        else:
            feedback.append(f"You scored {score:.1f}%. The pass mark is {exam.pass_mark}%. Keep studying!")
        
        if score >= 90:
            feedback.append("Outstanding performance!")
        elif score >= 80:
            feedback.append("Excellent work!")
        elif score >= 70:
            feedback.append("Good job!")
        elif score >= 60:
            feedback.append("Satisfactory performance.")
        else:
            feedback.append("Keep practicing and reviewing the material.")
        
        # Create StudentExam record
        student_exam = StudentExam.objects.create(
            student=student_obj,
            exam=exam,
            status='submitted',
            score=round(score, 2),
            percentage=round(score, 2),
            passed=score >= exam.pass_mark,
            started_at=timezone.now(),
            submitted_at=timezone.now()
        )
        
        print(f"DEBUG: Created StudentExam record: {student_exam.id} for student {student_obj.admission_number} and exam {exam.id}")
        
        # Create StudentAnswer records for each answer
        for answer in answers:
            question_id = answer.get('question_id')
            selected_option = answer.get('selected_option')
            
            # Find the question and its position
            for index, question in enumerate(questions_list):
                if str(question.id) == str(question_id):
                    is_correct = question.correct_answer.upper() == selected_option.upper()
                    marks_obtained = question.marks if is_correct else 0
                    
                    StudentAnswer.objects.create(
                        student_exam=student_exam,
                        question=question,
                        question_number=index + 1,
                        answer_text=selected_option,
                        is_correct=is_correct,
                        marks_obtained=marks_obtained
                    )
                    break
        
        # update CA score or Exam score in StudentSubject
        if not exam.is_applicant_exam and exam.subject:
            try:
                # Find the subject registration for the current session/term
                student_subject = StudentSubject.objects.get(
                    student=student_obj,
                    subject=exam.subject,
                    session_term=exam.session_term
                )
                
                # Calculate scaled score based on percentage
                # We use school-level max scores for the final grading record
                if exam.exam_type == 'test':
                    ca_max = float(student_obj.school.ca_max_score)
                    student_subject.ca_score = round(Decimal(str(score)) / 100 * Decimal(str(ca_max)), 2)
                    print(f"DEBUG: Updated CA score for {student_obj.admission_number}: {student_subject.ca_score}")
                elif exam.exam_type == 'exam':
                    exam_max = float(student_obj.school.exam_max_score)
                    student_subject.exam_score = round(Decimal(str(score)) / 100 * Decimal(str(exam_max)), 2)
                    print(f"DEBUG: Updated Exam score for {student_obj.admission_number}: {student_subject.exam_score}")
                
                student_subject.save()
            except StudentSubject.DoesNotExist:
                print(f"DEBUG: No StudentSubject found for {student_obj.admission_number} and subject {exam.subject.code}")
            except Exception as e:
                print(f"DEBUG: Failed to update StudentSubject result: {str(e)}")

        result = {
            'exam_id': exam_id,
            'exam_title': exam.title,
            'student_name': student_obj.name if hasattr(student_obj, 'name') else student_obj.admission_number,
            'total_questions': total_questions,
            'correct_answers': correct_answers,
            'score': round(score, 2),
            'grade': grade,
            'pass_mark': exam.pass_mark,
            'passed': score >= exam.pass_mark,
            'feedback': feedback,
            'submitted_at': timezone.now().isoformat()
        }
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to submit exam: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def submit_practice_exam(request):
    """Submit practice exam answers and get results"""
    try:
        exam_id = request.data.get('exam_id')
        answers = request.data.get('answers', [])
        student_name = request.data.get('student_name', 'Practice Student')
        
        if not exam_id:
            return Response(
                {'error': 'Exam ID is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # For practice exams, we'll simulate scoring
        # In a real implementation, you'd store the practice session and calculate actual scores
        total_questions = len(answers)
        correct_answers = random.randint(0, total_questions)  # Simulate random performance
        
        score = (correct_answers / total_questions * 100) if total_questions > 0 else 0
        
        # Generate feedback
        feedback = []
        if score >= 80:
            feedback.append("Excellent work! You have a strong understanding of this subject.")
        elif score >= 60:
            feedback.append("Good job! You're on the right track, but there's room for improvement.")
        else:
            feedback.append("Keep practicing! Review the topics and try again.")
        
        result = {
            'exam_id': exam_id,
            'student_name': student_name,
            'total_questions': total_questions,
            'correct_answers': correct_answers,
            'score': round(score, 2),
            'grade': 'A' if score >= 80 else 'B' if score >= 60 else 'C' if score >= 40 else 'D',
            'feedback': feedback,
            'submitted_at': timezone.now().isoformat()
        }
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to submit practice exam: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )