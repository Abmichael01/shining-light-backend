from api.models import Exam, StudentExam, Question
from django.db.models import Count
import random

def generate_applicant_exam(student, exam):
    """
    Get or create a StudentExam for an applicant with randomized questions.
    
    Args:
        student (Student): The applicant/student taking the exam
        exam (Exam): The exam definition
        
    Returns:
        StudentExam: The student's exam session with locked question order
    """
    # Check if this is an applicant exam with randomization enabled
    if not (exam.is_applicant_exam and exam.question_selection_count):
        # Fallback for regular exams - just return/create without special selection logic
        student_exam, created = StudentExam.objects.get_or_create(
            student=student,
            exam=exam,
            defaults={'status': 'not_started'}
        )
        return student_exam

    # Check for existing attempt
    existing_attempt = StudentExam.objects.filter(
        student=student, 
        exam=exam
    ).first()
    
    if existing_attempt:
        return existing_attempt

    # Select random questions
    # Get all valid questions for this exam
    # If the exam has specific questions assigned, select from those
    # If no specific questions, select from the topics
    pool_questions = []
    
    if exam.questions.exists():
        pool_questions = list(exam.questions.values_list('id', flat=True))
    elif exam.topics.exists():
        pool_questions = list(Question.objects.filter(
            topic_model__in=exam.topics.all()
        ).values_list('id', flat=True))
    else:
        # Fallback: Get questions from the exam's subject
        if exam.subject:
            pool_questions = list(Question.objects.filter(
                subject=exam.subject
            ).values_list('id', flat=True))
        elif exam.exam_class:
            # General admission exam for a class - might need to fetch from multiple subjects?
            # For now, let's assume questions are linked via Topic or Subject
            pass
            
    # Randomly select the requested count
    selection_count = min(len(pool_questions), exam.question_selection_count)
    selected_question_ids = random.sample(pool_questions, selection_count)
    
    # Create the StudentExam with these questions locked in
    student_exam = StudentExam.objects.create(
        student=student,
        exam=exam,
        status='not_started',
        question_order=selected_question_ids
    )
    
    return student_exam
