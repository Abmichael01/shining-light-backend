import json
import os

# Practice Exam 1 - Basic Math
exam_1 = {
    "id": "PRACTICE-EXAM-001",
    "title": "Basic Mathematics Practice Test",
    "subject": "Mathematics",
    "subject_code": "MATH-BAS",
    "difficulty": "easy",
    "total_questions": 10,
    "duration_minutes": 20,
    "total_marks": 50,
    "instructions": "This is a basic mathematics practice test. Read each question carefully and select the best answer. You have 20 minutes to complete this test.",
    "questions": [
        {
            "id": 1,
            "question": "What is 5 + 3?",
            "question_type": "multiple_choice",
            "options": [
                {"id": "a", "text": "7"},
                {"id": "b", "text": "8", "is_correct": True},
                {"id": "c", "text": "9"},
                {"id": "d", "text": "10"}
            ],
            "points": 5,
            "explanation": "5 + 3 = 8"
        },
        {
            "id": 2,
            "question": "What is 12 - 4?",
            "question_type": "multiple_choice",
            "options": [
                {"id": "a", "text": "6"},
                {"id": "b", "text": "7"},
                {"id": "c", "text": "8", "is_correct": True},
                {"id": "d", "text": "9"}
            ],
            "points": 5,
            "explanation": "12 - 4 = 8"
        },
        {
            "id": 3,
            "question": "What is 3 × 4?",
            "question_type": "multiple_choice",
            "options": [
                {"id": "a", "text": "10"},
                {"id": "b", "text": "11"},
                {"id": "c", "text": "12", "is_correct": True},
                {"id": "d", "text": "13"}
            ],
            "points": 5,
            "explanation": "3 × 4 = 12"
        },
        {
            "id": 4,
            "question": "What is 15 ÷ 3?",
            "question_type": "multiple_choice",
            "options": [
                {"id": "a", "text": "3"},
                {"id": "b", "text": "4"},
                {"id": "c", "text": "5", "is_correct": True},
                {"id": "d", "text": "6"}
            ],
            "points": 5,
            "explanation": "15 ÷ 3 = 5"
        },
        {
            "id": 5,
            "question": "Which number is the smallest?",
            "question_type": "multiple_choice",
            "options": [
                {"id": "a", "text": "12"},
                {"id": "b", "text": "8", "is_correct": True},
                {"id": "c", "text": "15"},
                {"id": "d", "text": "20"}
            ],
            "points": 5,
            "explanation": "8 is smaller than 12, 15, and 20"
        },
        {
            "id": 6,
            "question": "What is 7 × 2?",
            "question_type": "multiple_choice",
            "options": [
                {"id": "a", "text": "12"},
                {"id": "b", "text": "13"},
                {"id": "c", "text": "14", "is_correct": True},
                {"id": "d", "text": "15"}
            ],
            "points": 5,
            "explanation": "7 × 2 = 14"
        },
        {
            "id": 7,
            "question": "What is 20 - 8?",
            "question_type": "multiple_choice",
            "options": [
                {"id": "a", "text": "10"},
                {"id": "b", "text": "11"},
                {"id": "c", "text": "12", "is_correct": True},
                {"id": "d", "text": "13"}
            ],
            "points": 5,
            "explanation": "20 - 8 = 12"
        },
        {
            "id": 8,
            "question": "What is 4 + 9?",
            "question_type": "multiple_choice",
            "options": [
                {"id": "a", "text": "11"},
                {"id": "b", "text": "12"},
                {"id": "c", "text": "13", "is_correct": True},
                {"id": "d", "text": "14"}
            ],
            "points": 5,
            "explanation": "4 + 9 = 13"
        },
        {
            "id": 9,
            "question": "What is 18 ÷ 3?",
            "question_type": "multiple_choice",
            "options": [
                {"id": "a", "text": "4"},
                {"id": "b", "text": "5"},
                {"id": "c", "text": "6", "is_correct": True},
                {"id": "d", "text": "7"}
            ],
            "points": 5,
            "explanation": "18 ÷ 3 = 6"
        },
        {
            "id": 10,
            "question": "What is 6 × 3?",
            "question_type": "multiple_choice",
            "options": [
                {"id": "a", "text": "15"},
                {"id": "b", "text": "16"},
                {"id": "c", "text": "17"},
                {"id": "d", "text": "18", "is_correct": True}
            ],
            "points": 5,
            "explanation": "6 × 3 = 18"
        }
    ]
}

# Practice Exam 2 - English Language
exam_2 = {
    "id": "PRACTICE-EXAM-002",
    "title": "English Language Practice Test",
    "subject": "English Language",
    "subject_code": "ENG-BAS",
    "difficulty": "medium",
    "total_questions": 15,
    "duration_minutes": 30,
    "total_marks": 75,
    "instructions": "This is an English language practice test. Read each question carefully and select the best answer. You have 30 minutes to complete this test.",
    "questions": [
        {
            "id": 1,
            "question": "Choose the correct form: I ___ to school every day.",
            "question_type": "multiple_choice",
            "options": [
                {"id": "a", "text": "go", "is_correct": True},
                {"id": "b", "text": "goes"},
                {"id": "c", "text": "going"},
                {"id": "d", "text": "went"}
            ],
            "points": 5,
            "explanation": "'go' is the correct present tense form for first person singular"
        },
        {
            "id": 2,
            "question": "What is the plural of 'child'?",
            "question_type": "multiple_choice",
            "options": [
                {"id": "a", "text": "childs"},
                {"id": "b", "text": "children", "is_correct": True},
                {"id": "c", "text": "childes"},
                {"id": "d", "text": "childen"}
            ],
            "points": 5,
            "explanation": "'children' is the irregular plural form of 'child'"
        },
        {
            "id": 3,
            "question": "Choose the synonym for 'happy':",
            "question_type": "multiple_choice",
            "options": [
                {"id": "a", "text": "sad"},
                {"id": "b", "text": "angry"},
                {"id": "c", "text": "joyful", "is_correct": True},
                {"id": "d", "text": "tired"}
            ],
            "points": 5,
            "explanation": "'joyful' means the same as 'happy'"
        }
    ]
}

# Save exams
os.makedirs("api/data/exam_practice", exist_ok=True)

with open("api/data/exam_practice/practice_exam_1.json", "w") as f:
    json.dump(exam_1, f, indent=2)

with open("api/data/exam_practice/practice_exam_2.json", "w") as f:
    json.dump(exam_2, f, indent=2)

print("Practice exams created successfully!")
