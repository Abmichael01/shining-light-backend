from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.conf import settings
from api.models import Subject
import random, json, os

@api_view(['GET'])
@permission_classes([AllowAny])
def get_practice_subjects(request):
    try:
        subjects = Subject.objects.all().values('id', 'name', 'code')
        return Response(list(subjects), status=status.HTTP_200_OK)
    except Exception as e: return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_practice_exam(request):
    try:
        practice_dir = os.path.join(settings.BASE_DIR, 'api', 'data', 'exam_practice')
        files = [f for f in os.listdir(practice_dir) if f.endswith('.json')]
        if not files: return Response({'error': 'No practice exams'}, status=status.HTTP_404_NOT_FOUND)
        with open(os.path.join(practice_dir, random.choice(files)), 'r') as f:
            data = json.load(f)
        data.update({'created_at': timezone.now().isoformat(), 'is_practice': True, 'id': f"PRACT-{random.randint(100, 999)}"})
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e: return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def submit_practice_exam(request):
    """Submit answers for a practice exam and return the score"""
    try:
        answers = request.data.get('answers', {})
        questions = request.data.get('questions', [])
        if not questions:
            return Response({'error': 'No questions provided'}, status=status.HTTP_400_BAD_REQUEST)
        correct = 0
        total = len(questions)
        results = []
        for q in questions:
            q_id = str(q.get('id', ''))
            correct_answer = q.get('correct_answer', '')
            student_answer = answers.get(q_id, '')
            is_correct = student_answer == correct_answer
            if is_correct:
                correct += 1
            results.append({
                'question_id': q_id,
                'student_answer': student_answer,
                'correct_answer': correct_answer,
                'is_correct': is_correct,
            })
        score = round((correct / total) * 100, 1) if total > 0 else 0
        return Response({
            'score': score,
            'correct': correct,
            'total': total,
            'results': results,
            'submitted_at': timezone.now().isoformat(),
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
