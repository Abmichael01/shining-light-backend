"""
Custom admin views for exam management
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.db.models import Q, Avg
from .models import StudentExam, StudentAnswer, Student, Exam


@staff_member_required
def exam_results_view(request, student_exam_id):
    """
    Detailed view of a student's exam results
    """
    student_exam = get_object_or_404(StudentExam, id=student_exam_id)
    student_answers = StudentAnswer.objects.filter(
        student_exam=student_exam
    ).order_by('question_number')
    
    context = {
        'student_exam': student_exam,
        'student_answers': student_answers,
        'title': f'Exam Results - {student_exam.student.admission_number}',
    }
    
    return render(request, 'admin/exam_results.html', context)


@staff_member_required
def student_exam_history(request, student_id):
    """
    View all exam attempts for a specific student
    """
    student = get_object_or_404(Student, id=student_id)
    student_exams = StudentExam.objects.filter(
        student=student
    ).order_by('-submitted_at', '-created_at')
    
    context = {
        'student': student,
        'student_exams': student_exams,
        'title': f'Exam History - {student.admission_number}',
    }
    
    return render(request, 'admin/student_exam_history.html', context)


@staff_member_required
def exam_analytics(request, exam_id):
    """
    Analytics view for a specific exam
    """
    exam = get_object_or_404(Exam, id=exam_id)
    student_exams = StudentExam.objects.filter(exam=exam)
    
    # Calculate statistics
    total_attempts = student_exams.count()
    completed_attempts = student_exams.filter(status='submitted').count()
    passed_attempts = student_exams.filter(passed=True).count()
    
    if completed_attempts > 0:
        pass_rate = (passed_attempts / completed_attempts) * 100
        avg_score = student_exams.filter(status='submitted').aggregate(
            avg_score=Avg('score')
        )['avg_score'] or 0
    else:
        pass_rate = 0
        avg_score = 0
    
    # Get score distribution
    score_ranges = {
        '0-20': student_exams.filter(score__gte=0, score__lt=20).count(),
        '20-40': student_exams.filter(score__gte=20, score__lt=40).count(),
        '40-60': student_exams.filter(score__gte=40, score__lt=60).count(),
        '60-80': student_exams.filter(score__gte=60, score__lt=80).count(),
        '80-100': student_exams.filter(score__gte=80, score__lte=100).count(),
    }
    
    context = {
        'exam': exam,
        'total_attempts': total_attempts,
        'completed_attempts': completed_attempts,
        'passed_attempts': passed_attempts,
        'pass_rate': round(pass_rate, 2),
        'avg_score': round(avg_score, 2),
        'score_ranges': score_ranges,
        'title': f'Exam Analytics - {exam.title}',
    }
    
    return render(request, 'admin/exam_analytics.html', context)


@staff_member_required
def get_question_analysis(request, exam_id):
    """
    AJAX endpoint for question analysis
    """
    exam = get_object_or_404(Exam, id=exam_id)
    
    # Get all student answers for this exam
    student_answers = StudentAnswer.objects.filter(
        student_exam__exam=exam
    ).select_related('question', 'student_exam__student')
    
    # Group by question
    question_analysis = {}
    for answer in student_answers:
        question_id = answer.question.id
        if question_id not in question_analysis:
            question_analysis[question_id] = {
                'question': answer.question,
                'total_attempts': 0,
                'correct_attempts': 0,
                'answer_distribution': {},
                'difficulty': answer.question.difficulty,
                'marks': answer.question.marks,
            }
        
        analysis = question_analysis[question_id]
        analysis['total_attempts'] += 1
        if answer.is_correct:
            analysis['correct_attempts'] += 1
        
        # Track answer distribution
        answer_text = answer.answer_text
        if answer_text not in analysis['answer_distribution']:
            analysis['answer_distribution'][answer_text] = 0
        analysis['answer_distribution'][answer_text] += 1
    
    # Calculate percentages
    for question_id, analysis in question_analysis.items():
        if analysis['total_attempts'] > 0:
            analysis['correct_percentage'] = (analysis['correct_attempts'] / analysis['total_attempts']) * 100
        else:
            analysis['correct_percentage'] = 0
    
    return JsonResponse({
        'question_analysis': question_analysis,
        'exam_title': exam.title,
        'total_questions': exam.questions.count(),
    })
