from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from api.models import Exam, Student, StudentSubject, StudentExam, StudentAnswer
from api.serializers.academic import ExamSerializer
from api.authentication import CBTSessionAuthentication
from api.utils.exam_generator import generate_applicant_exam

@api_view(['GET'])
@authentication_classes([CBTSessionAuthentication])
@permission_classes([AllowAny])
def get_cbt_exams(request):
    try:
        student_obj = Student.objects.get(admission_number=request.user.admission_number)
        registered_subjects = StudentSubject.objects.filter(student=student_obj, is_active=True).values_list('subject_id', flat=True)
        taken_exams = StudentExam.objects.filter(student=student_obj).values_list('exam', flat=True)
        available_exams = Exam.objects.filter(status='active', subject_id__in=registered_subjects).exclude(id__in=taken_exams).order_by('-created_at')
        return Response(ExamSerializer(available_exams, many=True, context={'request': request}).data, status=status.HTTP_200_OK)
    except Exception as e: return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@authentication_classes([CBTSessionAuthentication])
@permission_classes([AllowAny])
def get_cbt_exam(request, exam_id):
    try:
        exam = Exam.objects.get(id=exam_id, status='active')
        context = {'request': request}
        if exam.is_applicant_exam:
            student_obj = Student.objects.get(admission_number=request.user.admission_number)
            student_exam = generate_applicant_exam(student_obj, exam)
            if student_exam and student_exam.question_order: context['specific_question_ids'] = student_exam.question_order
        return Response(ExamSerializer(exam, context=context).data, status=status.HTTP_200_OK)
    except Exception as e: return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@authentication_classes([CBTSessionAuthentication])
@permission_classes([AllowAny])
def submit_cbt_exam(request, exam_id):
    try:
        answers = request.data.get('answers', [])
        exam = Exam.objects.get(id=exam_id, status='active')
        student_obj = Student.objects.get(admission_number=request.user.admission_number)
        if StudentExam.objects.filter(student=student_obj, exam=exam).exists():
            return Response({'error': 'Already taken this exam'}, status=status.HTTP_400_BAD_REQUEST)
        
        questions_qs = list(exam.questions.all())
        questions_dict = {str(q.id): q for q in questions_qs}
        
        score = 0
        total_marks = sum(q.marks or 1 for q in questions_qs)
        student_answers_to_create = []

        for i, answer_data in enumerate(answers):
            q_id = str(answer_data.get('question_id'))
            selected = answer_data.get('selected_option', '').upper()
            question = questions_dict.get(q_id)
            
            if question:
                is_correct = selected == question.correct_answer.upper()
                marks_obtained = float(question.marks or 1) if is_correct else 0
                score += marks_obtained
                
                student_answers_to_create.append(
                    StudentAnswer(
                        question=question,
                        question_number=i + 1,
                        answer_text=selected,
                        is_correct=is_correct,
                        marks_obtained=marks_obtained
                    )
                )

        percentage = (score / total_marks * 100) if total_marks > 0 else 0
        
        student_exam = StudentExam.objects.create(
            student=student_obj, 
            exam=exam, 
            status='graded', 
            score=round(score, 2), 
            percentage=round(percentage, 2), 
            passed=score >= exam.pass_mark, 
            started_at=timezone.now(), 
            submitted_at=timezone.now()
        )
        
        # Associate answers with exam attempt and insert
        for sa in student_answers_to_create:
            sa.student_exam = student_exam
        if student_answers_to_create:
            StudentAnswer.objects.bulk_create(student_answers_to_create)
        
        student_subject = StudentSubject.objects.filter(student=student_obj, subject=exam.subject, is_active=True).first()
        if student_subject:
            # Map the CBT score to the correct field based on the Exam Type
            if exam.exam_type == 'test':
                student_subject.ca_score = round(score, 2)
            elif exam.exam_type == 'exam':
                student_subject.objective_score = round(score, 2)
            student_subject.save()
            
        return Response({
            'success': True, 
            'score': round(score, 2), 
            'total': total_marks,
            'percentage': round(percentage, 2),
            'passed': score >= exam.pass_mark
        }, status=status.HTTP_200_OK)
    except Exception as e: return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
