"""
AI Question Generator Service

Generates exam questions in a structured shape that maps directly onto the
existing `Question` model. Uses OpenAI's structured outputs (JSON schema mode)
so we never have to parse free-form text — the model is forced to return
exactly the fields we ask for.

Flow:
    1. Caller passes (subject, topic, count, difficulty, question_type, format_style)
    2. We pull `Topic.description` to ground the AI in the school's curriculum
    3. We build a prompt and call OpenAI with a strict JSON schema
    4. We return draft questions (not yet persisted) for teacher review
    5. After teacher review, `save_questions()` persists with is_verified=False
"""

import json
from typing import List, Dict, Any, Optional

from django.db import transaction
from api.models import Question, Subject, Topic
from .openai_client import get_openai_client, get_default_model


# Hard caps to keep API costs predictable and prevent abuse
MAX_QUESTIONS_PER_REQUEST = 20
MIN_QUESTIONS_PER_REQUEST = 1
MAX_EXTRA_CONTEXT_CHARS = 8000  # HTML overhead means ~2000 tokens worst case — still safe

VALID_DIFFICULTIES = {'easy', 'medium', 'hard'}
VALID_QUESTION_TYPES = {'multiple_choice', 'true_false'}  # MVP: only auto-gradeable types
VALID_FORMAT_STYLES = {'waec', 'jamb', 'general'}


# ---------------------------------------------------------------------------
# JSON Schema for OpenAI structured output
# ---------------------------------------------------------------------------
# This schema is enforced by OpenAI — the model CANNOT return malformed JSON
# or skip required fields. That eliminates a whole class of "AI returned junk"
# bugs we'd otherwise have to handle.

QUESTION_OUTPUT_SCHEMA = {
    "name": "generated_questions",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["questions"],
        "properties": {
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "question_text", "option_a", "option_b", "option_c",
                        "option_d", "correct_answer", "explanation",
                    ],
                    "properties": {
                        "question_text": {"type": "string"},
                        "option_a": {"type": "string"},
                        "option_b": {"type": "string"},
                        "option_c": {"type": "string"},
                        "option_d": {"type": "string"},
                        "correct_answer": {
                            "type": "string",
                            "enum": ["A", "B", "C", "D"],
                        },
                        "explanation": {"type": "string"},
                    },
                },
            }
        },
    },
}


class QuestionGeneratorService:
    """Service class for AI question generation operations."""

    @staticmethod
    def validate_inputs(count: int, difficulty: str, question_type: str, format_style: str) -> None:
        """Raise ValueError if any input is out of bounds."""
        if not (MIN_QUESTIONS_PER_REQUEST <= count <= MAX_QUESTIONS_PER_REQUEST):
            raise ValueError(
                f"Question count must be between {MIN_QUESTIONS_PER_REQUEST} "
                f"and {MAX_QUESTIONS_PER_REQUEST}"
            )
        if difficulty not in VALID_DIFFICULTIES:
            raise ValueError(f"Difficulty must be one of: {sorted(VALID_DIFFICULTIES)}")
        if question_type not in VALID_QUESTION_TYPES:
            raise ValueError(f"Question type must be one of: {sorted(VALID_QUESTION_TYPES)}")
        if format_style not in VALID_FORMAT_STYLES:
            raise ValueError(f"Format style must be one of: {sorted(VALID_FORMAT_STYLES)}")

    @staticmethod
    def _build_prompt(
        subject: Subject,
        topic: Optional[Topic],
        count: int,
        difficulty: str,
        format_style: str,
        extra_context: Optional[str] = None,
    ) -> str:
        """
        Build the user prompt sent to OpenAI.

        ============================================================
        TODO (HUMAN INPUT): Customize this prompt with Nigerian-flavor
        ============================================================
        The AI's output quality depends almost entirely on this prompt.
        You know what good WAEC/JAMB questions look like — I don't.

        Things to customize below:
          - Tone: formal exam-board English vs friendly classroom tone
          - Phrasing: "Which of the following..." vs "Which one is..."
          - Local grounding: prefer Nigerian examples (Lagos/Abuja distance,
            Naira inflation, local plants/animals/history) over US/UK
          - Forbidden patterns: e.g. don't ask "all of the above" / "none of
            the above" if WAEC frowns on those
          - Difficulty calibration: what does "hard" mean for SS2 Biology?

        Recommended prompt structure (5–10 lines is enough):
          1. State the role: "You are a Nigerian secondary school exam author..."
          2. State the constraint: subject, topic, class level, count
          3. State the format style explicitly (WAEC vs JAMB vs general)
          4. Give 1–2 quality rules (clear stem, only one correct answer)
          5. Tell it what to avoid (trick questions, ambiguity, foreign refs)
        ============================================================
        """

        topic_context = ""
        if topic:
            desc = (topic.description or '').strip()
            topic_context = f"Topic: {topic.name}"
            if desc:
                topic_context += f"\nTopic syllabus / scope: {desc}"
        else:
            topic_context = f"Topic: General {subject.name}"

        class_level = ""
        if hasattr(subject, 'class_model') and subject.class_model:
            class_level = f"Class level: {subject.class_model.name}\n"

        format_label = {
            'waec': 'WAEC (West African Examinations Council)',
            'jamb': 'JAMB (Joint Admissions and Matriculation Board)',
            'general': 'general school examination',
        }[format_style]

        extra_context_block = ""
        if extra_context:
            trimmed = extra_context.strip()[:MAX_EXTRA_CONTEXT_CHARS]
            if trimmed:
                extra_context_block = (
                    "\nReference material the questions MUST be based on "
                    "(it may contain HTML markup and math in LaTeX/KaTeX form — "
                    "interpret formatting and equations, prioritise this over general knowledge):\n"
                    f"\"\"\"\n{trimmed}\n\"\"\"\n"
                )

        # >>> EDIT EVERYTHING BELOW THIS LINE TO TUNE QUALITY <<<
        prompt = f"""You are an experienced Nigerian secondary school examiner.

Generate {count} multiple-choice questions for the following:
Subject: {subject.name}
{class_level}{topic_context}
Difficulty: {difficulty}
Format style: {format_label}
{extra_context_block}
Rules:
- Each question must have exactly 4 options (A, B, C, D) with one correct answer.
- Questions must be clear, unambiguous, and grounded in the syllabus above.
- If reference material is provided, base every question strictly on it.
- For any mathematical, scientific, or chemical expressions, use inline LaTeX
  delimited by single dollar signs, e.g. $x^2 + y^2 = z^2$, $\\frac{{a}}{{b}}$,
  $H_2O$. Use $$...$$ only for full display equations. This applies to question
  text, options, and explanations.
- Output PLAIN TEXT for everything else — do NOT use HTML tags in the output.
- Provide a brief explanation (1-2 sentences) for the correct answer.

(TODO: add your own Nigerian-context rules here.)
"""
        return prompt

    @staticmethod
    def generate(
        subject_id: str,
        topic_id: Optional[int],
        count: int,
        difficulty: str,
        question_type: str,
        format_style: str,
        extra_context: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Generate draft questions. Does NOT persist anything.

        Note: subject_id is a string (Subject uses a CharField PK like
        "ENGLISH-LANGUAGE-SS1"), but topic_id is an integer.

        `extra_context` lets the admin paste lesson notes / a passage / specific
        points the AI must use as the basis for questions. Capped at
        MAX_EXTRA_CONTEXT_CHARS to keep prompt size predictable.
        """
        QuestionGeneratorService.validate_inputs(count, difficulty, question_type, format_style)

        try:
            subject = Subject.objects.select_related('class_model', 'school').get(id=subject_id)
        except Subject.DoesNotExist:
            raise ValueError(f"Subject with id {subject_id} not found")

        topic = None
        if topic_id:
            try:
                topic = Topic.objects.get(id=topic_id, subject=subject)
            except Topic.DoesNotExist:
                raise ValueError(f"Topic with id {topic_id} not found for this subject")

        prompt = QuestionGeneratorService._build_prompt(
            subject=subject,
            topic=topic,
            count=count,
            difficulty=difficulty,
            format_style=format_style,
            extra_context=extra_context,
        )

        client = get_openai_client()
        response = client.chat.completions.create(
            model=get_default_model(),
            messages=[
                {"role": "system", "content": "You generate exam questions as strict JSON."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_schema", "json_schema": QUESTION_OUTPUT_SCHEMA},
            temperature=0.7,
        )

        raw = response.choices[0].message.content
        data = json.loads(raw)
        questions = data.get('questions', [])

        # Tag each draft with the metadata the UI / save step needs
        for q in questions:
            q['subject_id'] = subject.id  # string PK
            q['topic_id'] = topic.id if topic else None  # integer or None
            q['difficulty'] = difficulty
            q['question_type'] = question_type

        return questions

    @staticmethod
    @transaction.atomic
    def save_questions(
        questions: List[Dict[str, Any]],
        created_by,
        marks: int = 1,
    ) -> List[Question]:
        """Persist reviewed/edited questions with is_verified=False.

        Teachers must explicitly verify each question via the existing
        question-bank UI before it can be used in real exams.
        """
        saved = []
        for q in questions:
            question = Question.objects.create(
                subject_id=q['subject_id'],
                topic_model_id=q.get('topic_id'),
                question_text=q['question_text'],
                question_type=q.get('question_type', 'multiple_choice'),
                difficulty=q.get('difficulty', 'medium'),
                option_a=q.get('option_a'),
                option_b=q.get('option_b'),
                option_c=q.get('option_c'),
                option_d=q.get('option_d'),
                correct_answer=q['correct_answer'],
                explanation=q.get('explanation', ''),
                marks=marks,
                is_verified=False,
                created_by=created_by,
            )
            saved.append(question)
        return saved
