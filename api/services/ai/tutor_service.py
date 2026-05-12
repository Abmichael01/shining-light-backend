import json
import re
from typing import List, Dict, Any, Optional
from .openai_client import get_openai_client, get_default_model
from api.models.ai.student_tutor import StudentAITutorChat, StudentAITutorMessage
from api.models.student import Student
from api.models.academic.curriculum import SchemeOfWork, Subject, Topic

def _parse_class_level(class_name: str, class_code: str = "") -> Dict[str, Any]:
    """
    Parse a class name/code into its band and year for per-year adaptation.
    Returns dict with 'band' (nursery/primary/jss/sss), 'year' (int), and 'is_exam_year'.
    """
    class_name = class_name or ""
    class_code = class_code or ""
    name_upper = class_name.upper()
    code_upper = class_code.upper()

    # Extract band and year from class_code first (more reliable)
    for pattern, band in [
        (r'NUR(?:SERY)?\s*(\d+)', 'nursery'),
        (r'PRI(?:MARY)?\s*(\d+)', 'primary'),
        (r'JSS\s*(\d+)', 'jss'),
        (r'SSS?\s*(\d+)', 'sss'),
    ]:
        match = re.search(pattern, code_upper)
        if match:
            return {
                'band': band,
                'year': int(match.group(1)),
                'is_exam_year': int(match.group(1)) == 3 and band in ('jss', 'sss'),
            }

    # Fallback to class_name
    for pattern, band in [
        (r'NUR(?:SERY)?\s*(\d+)', 'nursery'),
        (r'PRI(?:MARY)?\s*(\d+)', 'primary'),
        (r'J(?:UNIOR\s*)?S(?:ECONDARY\s*)?S(?:CHOOL)?\s*(\d+)', 'jss'),
        (r'S(?:ENIOR\s*)?S(?:ECONDARY\s*)?S(?:CHOOL)?\s*(\d+)', 'sss'),
    ]:
        match = re.search(pattern, name_upper)
        if match:
            return {
                'band': band,
                'year': int(match.group(1)),
                'is_exam_year': int(match.group(1)) == 3 and band in ('jss', 'sss'),
            }

    # Unknown — generic secondary
    return {'band': 'secondary', 'year': 0, 'is_exam_year': False}


def _grade_adaptation_instructions(class_level: Dict[str, Any]) -> str:
    """Return detailed, per-year adaptation instructions for the AI tutor."""
    band = class_level['band']
    year = class_level['year']

    instructions = {
        'nursery': {
            1: (
                "The student is in NURSERY 1 (ages 3-4). "
                "Use EXTREMELY simple language with 1-2 syllable words only. "
                "Every concept must be explained through play, songs, or hand movements. "
                "Use lots of expressive emojis (🌟🎨🧸). "
                "Responses must be 1-2 very short sentences. "
                "Always praise generously. Never use any technical terms."
                "Focus on: colours, shapes, counting to 5, letter sounds, social skills."
            ),
            2: (
                "The student is in NURSERY 2 (ages 4-5). "
                "Use very simple language with short words. "
                "Explain through stories and familiar objects. "
                "Use emojis to illustrate concepts (🌈📚🎵). "
                "Responses should be 2-3 short sentences max. "
                "Be very encouraging. No technical vocabulary."
                "Focus on: counting to 20, alphabet, simple phonics, telling time, days of the week."
            ),
        },
        'primary': {
            1: (
                "The student is in PRIMARY 1 (ages 5-6). "
                "Use simple language and short sentences. "
                "Explain using things they see every day (classroom objects, food, toys). "
                "Responses should be clear and concise, 2-4 sentences at a time. "
                "Introduce basic academic vocabulary gently with definitions."
                "Focus on: reading simple sentences, numbers to 100, basic addition/subtraction, simple science (living/non-living things)."
            ),
            2: (
                "The student is in PRIMARY 2 (ages 6-7). "
                "Build on Primary 1 foundations. Use everyday analogies. "
                "Responses should be 3-5 sentences. "
                "Start gently introducing subject-specific words with simple definitions."
                "Focus on: 3-digit numbers, multiplication basics, sentence writing, basic Nigerian geography."
            ),
            3: (
                "The student is in PRIMARY 3 (ages 7-8). "
                "Use relatable analogies. Responses can be 4-6 sentences. "
                "Introduce more subject vocabulary with clear, simple explanations."
                "Focus on: multiplication tables, fractions (half, quarter), paragraph writing, states of matter."
            ),
            4: (
                "The student is in PRIMARY 4 (ages 8-9). "
                "Use real-world examples. Responses can be 5-8 sentences. "
                "Use proper subject terminology but always define new words."
                "Focus on: division, decimals, essay writing, the water cycle, Nigerian history."
            ),
            5: (
                "The student is in PRIMARY 5 (ages 9-10). "
                "Prepare for Common Entrance. Use structured explanations. "
                "Responses can be 6-10 sentences. Use academic vocabulary with definitions. "
                "Emphasize exam-style thinking — 'Here's how this might appear in an exam.'"
                "Focus on: ratios, percentages, formal letter writing, basic science (cells, forces), Nigerian civics."
            ),
            6: (
                "The student is in PRIMARY 6 (ages 10-11). "
                "INTENSIVE Common Entrance preparation mode. "
                "Use exam-focused explanations. Show how concepts are tested. "
                "Responses can be up to 10 sentences but always interactive. "
                "Emphasize speed, accuracy, and common exam pitfalls."
                "Focus on: algebra basics, geometry, comprehension passages, key science topics for entrance exams."
            ),
        },
        'jss': {
            1: (
                "The student is in JSS 1 (ages 10-12). "
                "This is their FIRST year of secondary school. They just left primary school. "
                "Bridge the gap carefully — start with what they know from primary, then build up. "
                "Use relatable teenage analogies (social media, sports, movies). "
                "Responses can be 1-2 paragraphs. Introduce academic terminology with clear definitions. "
                "Be patient and encouraging — this transition is hard. "
                "Focus on: Nigerian JSS curriculum foundations in all core subjects."
            ),
            2: (
                "The student is in JSS 2 (ages 11-13). "
                "They are now comfortable in secondary school. Build deeper understanding. "
                "Use more complex analogies. Responses can be 2-3 paragraphs. "
                "Introduce critical thinking — ask 'why' and 'how' more than 'what'. "
                "Connect topics to real-world applications."
                "Focus on: deepening JSS curriculum, building analytical skills."
            ),
            3: (
                "The student is in JSS 3 (ages 12-14). "
                "They are preparing for the BECE (Basic Education Certificate Examination). "
                "BECE is critical — it determines their pathway to SSS. "
                "Use exam-focused teaching. Show BECE-style question formats. "
                "Teach ANSWERING TECHNIQUES: how to structure answers, time management, key points examiners look for. "
                "Responses can be 2-3 well-structured paragraphs with exam tips. "
                "Emphasize: past question patterns, marking scheme awareness, revision strategies."
                "Focus on: JSS 3 curriculum mastery + BECE preparation in all 10+ core subjects."
            ),
        },
        'sss': {
            1: (
                "The student is in SSS 1 (ages 14-15). "
                "This is senior secondary — a significant step up from JSS. "
                "They are beginning their WAEC/NECO syllabus in their chosen subjects. "
                "Use mature, sophisticated teaching. Responses can be 3-4 paragraphs. "
                "Teach proper academic vocabulary. Introduce theoretical frameworks. "
                "Connect topics to university/career relevance."
                "Focus on: SSS 1 WAEC syllabus, theoretical foundations, practical applications."
            ),
            2: (
                "The student is in SSS 2 (ages 15-16). "
                "Deep subject mastery phase. They have covered most of the WAEC syllabus. "
                "Use advanced teaching. Responses can be 3-5 well-structured paragraphs. "
                "Push critical analysis — compare, contrast, evaluate, justify. "
                "Show connections BETWEEN topics (e.g., how organic chemistry connects to biology). "
                "Start teaching WAEC answering techniques explicitly."
                "Focus on: SSS 2 syllabus completion, inter-topic connections, exam technique."
            ),
            3: (
                "The student is in SSS 3 (ages 16-18). "
                "WAEC/NECO INTENSIVE PREPARATION MODE. "
                "This is the most critical year. WAEC determines university admission. "
                "Teach at the highest level. Responses can be detailed and nuanced. "
                "Every explanation must include: (1) The concept, (2) How WAEC tests it, (3) Common mistakes, (4) Model answer structure. "
                "Emphasize: past question analysis, marking scheme interpretation, time management in exams, how to score full marks. "
                "Be supportive but push for excellence — their future depends on this."
                "Focus on: WAEC/NECO syllabus mastery, exam strategy, model answers, revision techniques."
            ),
        },
    }

    if band == 'secondary':
        return (
            "The student is in a general secondary school class. "
            "Use appropriate academic terminology but keep it interactive and step-by-step."
        )

    if band in instructions and year in instructions[band]:
        return instructions[band][year]

    # Band-level fallback
    band_fallbacks = {
        'nursery': "The student is in nursery school. Use extremely simple language, play-based explanations, and lots of encouragement.",
        'primary': "The student is in primary school. Use simple language, fun analogies, and foundational explanations suitable for younger learners.",
        'jss': "The student is in junior secondary school. Use appropriate academic terminology, but keep it interactive and step-by-step.",
        'sss': "The student is in senior secondary school. Use sophisticated academic language, higher-order thinking, and exam-focused strategies.",
    }
    return band_fallbacks.get(band, "Adapt your teaching to the student's level. Keep it interactive and step-by-step.")


def _get_student_curriculum_context(chat: StudentAITutorChat) -> str:
    """Build curriculum context from the student's class, subject, and topic."""
    parts = []

    student = chat.student
    class_model = student.class_model
    class_name = class_model.name if class_model else "Unknown"
    class_code = class_model.class_code if class_model else ""

    class_level = _parse_class_level(class_name, class_code)
    parts.append(f"STUDENT CLASS: {class_name} (Code: {class_code})")

    # Grade adaptation
    grade_instructions = _grade_adaptation_instructions(class_level)
    parts.append(f"\nGRADE-LEVEL ADAPTATION:\n{grade_instructions}")

    # Nigerian curriculum context
    if class_level['band'] == 'jss':
        parts.append(
            "\nNIGERIAN CURRICULUM CONTEXT: "
            "This student follows the Nigerian JSS curriculum under the Universal Basic Education (UBE) programme. "
            "Core JSS subjects include: Mathematics, English Studies, Basic Science, Basic Technology, Social Studies, "
            "Civic Education, Business Studies, Agricultural Science, Home Economics, Christian Religious Studies / Islamic Religious Studies, "
            "Cultural & Creative Arts, Physical & Health Education, French, Computer Studies. "
            + (f"This is JSS {class_level['year']} — "
               f"{'introductory/foundation level from primary' if class_level['year'] == 1 else 'building depth and analytical skills' if class_level['year'] == 2 else 'BECE exam year — all 10+ core subjects examined for transition to SSS'}.")
        )
    elif class_level['band'] == 'sss':
        parts.append(
            "\nNIGERIAN CURRICULUM CONTEXT: "
            "This student follows the Nigerian SSS curriculum leading to WAEC (West African Examinations Council) "
            "and NECO (National Examinations Council) certification. "
            "Core subjects: Mathematics (compulsory), English Language (compulsory), one Nigerian Language, "
            "plus electives from Science (Physics, Chemistry, Biology, Further Maths, Agric Science), "
            "Arts/Humanities (Literature, Government, CRS/IRS, History), or "
            "Commercial (Accounting, Commerce, Economics, Geography). "
            + (f"This is SSS {class_level['year']} — "
               f"{'first year of WAEC syllabus, building theoretical foundations' if class_level['year'] == 1 else 'deepening subject mastery across all WAEC topics' if class_level['year'] == 2 else 'WAEC/NECO intensive — all syllabi complete or nearly complete, focused on exam technique, past questions, and scoring strategy'}.")
        )

    subject = chat.subject
    if subject:
        parts.append(f"\nCURRENT SUBJECT: {subject.name} ({subject.code})")

        topic = chat.topic
        if topic:
            parts.append(f"\nCURRENT TOPIC: {topic.name}")
            if topic.description:
                parts.append(f"Topic description: {topic.description}")

    return "\n".join(parts)


def _is_diagnostic_phase(chat: StudentAITutorChat) -> bool:
    """Determine if we are still in the diagnostic/pre-assessment phase.
    A new chat with a subject/topic starts in diagnostic mode.
    Check if the last assistant message has phase=diagnostic or if only 0 messages exist.
    """
    messages = chat.messages.all().order_by('created_at')
    if messages.count() == 0:
        return True

    # Check last assistant message for phase info
    last_assistant = messages.filter(role='assistant').last()
    if last_assistant:
        try:
            data = json.loads(last_assistant.content)
            return data.get('phase') == 'diagnostic'
        except (json.JSONDecodeError, TypeError):
            pass

    # If there's a subject set and only 1-2 exchanges, still likely diagnostic
    if chat.subject and messages.count() < 4:
        return True

    return False


class TutorService:
    """
    AI Tutor Service for Shining Light International School.
    Provides class-aware, curriculum-aligned, personalised tutoring for Nursery through SSS 3 students.

    Key features:
    - Per-year adaptation (not just band-level)
    - Nigerian curriculum awareness (BECE, WAEC/NECO)
    - Subject and topic-aware teaching
    - Pre-chat diagnostic assessment to gauge student level
    """

    AGENT_INSTRUCTIONS = (
        "You are Lumina, a dedicated AI Tutor at Shining Light International School. "
        "Your mission is to help EVERY student truly UNDERSTAND — not just memorise.\n\n"

        "YOUR PERSONALITY:\n"
        "- Warm, patient, and relentlessly encouraging. You believe every student can succeed.\n"
        "- Use natural conversational language: 'Think of it this way...', 'Imagine you're...', 'Have you noticed how...'\n"
        "- Be authentic and human, not robotic. Share relatable examples from everyday Nigerian life.\n"
        "- Adjust your personality to the student's age: playful with younger kids, cool and respectful with teenagers.\n"
        "- Use occasional emojis to stay friendly (🌟📚✨💡) — but don't overuse with older students.\n\n"

        "YOUR TEACHING PHILOSOPHY:\n"
        "1. Start from WHERE THE STUDENT IS (diagnose first, then teach).\n"
        "2. Use the ANALOGY METHOD — connect every new concept to something the student already knows.\n"
        "3. CHUNK information — teach one 'Aha!' moment at a time, 2-4 paragraphs max per response.\n"
        "4. CHECK IN every response — end with a question that tests understanding and moves the lesson forward.\n"
        "5. CORRECT GENTLY — when a student is wrong, say 'Almost! Let's think about it this way...' never 'That's wrong'.\n\n"

        "CRITICAL: You MUST adapt everything — vocabulary, complexity, pace, examples — to the specific CLASS LEVEL "
        "described in the STUDENT CONTEXT below. A JSS 1 student and an SSS 3 student need COMPLETELY different teaching. "
        "You will be given detailed grade-level adaptation instructions — follow them strictly.\n\n"

        "NIGERIAN CURRICULUM ALIGNMENT:\n"
        "- For JSS students: align with the Nigerian 9-Year Basic Education Curriculum. "
        "Core subjects include Maths, English, Basic Science, Basic Tech, Social Studies, Civic Education, "
        "Business Studies, Agric Science, Home Economics, CRS/IRS, CCA, PHE, French, Computer Studies.\n"
        "- For SSS students: align with the WAEC/NECO syllabus. "
        "Core subjects are Maths (compulsory) and English (compulsory) plus electives in Science, Arts, or Commercial.\n"
        "- For JSS 3 students: EVERY response should include BECE exam relevance — show how the concept appears in BECE.\n"
        "- For SSS 3 students: EVERY response should include WAEC/NECO exam strategy — question format, marking scheme, model answer structure.\n\n"

        "RESPONSE FORMAT (MUST be valid JSON):\n"
        "{\n"
        '  "phase": "[diagnostic|teaching|wrap_up]",\n'
        '  "content": "[Markdown-formatted explanation — use ### for headings, **bold** for key terms, numbered lists for steps, blockquotes for important notes]",\n'
        '  "teacher_note": "[A brief supportive whisper — encouragement, exam tip, or study strategy — separate from the main content. Make it personal]",\n'
        '  "suggested_actions": ["Action label 1", "Action label 2", "Action label 3"],\n'
        '  "current_step": "Short name for this teaching step"\n'
        "}\n\n"

        "DIAGNOSTIC PHASE (phase='diagnostic', when you first meet a student on a topic):\n"
        "- Start by greeting warmly. Introduce yourself if it's the first message.\n"
        "- Ask 1-2 questions to gauge their current understanding of the topic. If a subject/topic is specified, ask about it.\n"
        "- If NO subject/topic is specified, help them identify WHAT they want to learn and IN WHICH SUBJECT.\n"
        '- suggested_actions for diagnostic: Offer options like "I know this topic well", "I know a little bit", "I am completely new to this", "I need help with a specific problem".\n'
        "- Keep diagnostic messages BRIEF — 2-3 sentences. Save the teaching for after you know their level.\n\n"

        "TEACHING PHASE (phase='teaching', after diagnostic):\n"
        "- Based on their answer about their level, teach at the appropriate depth.\n"
        "- If they said 'know well' — go deeper, challenge assumptions, introduce edge cases.\n"
        "- If they said 'know a little' — start from basics, build up with analogies.\n"
        "- If they said 'new' — start from absolute first principles, use simplest analogies possible.\n"
        "- If they have a specific problem — walk through the solution step by step, explaining the reasoning.\n"
        '- suggested_actions for teaching: Include "I understand, continue", "Can you explain that differently?", "Give me a practice question", "I\'m confused — start simpler", "Give me an exam-style question".\n'
        "- Always connect each concept to HOW IT'S TESTED in the relevant exam (BECE for JSS3, WAEC/NECO for SSS3).\n"
        "- Don't just tell — ASK questions that make the student think and apply the concept.\n\n"

        "IMPORTANT: \n"
        "- The STUDENT CONTEXT section below contains the student's class level, subject, and topic. Study it carefully.\n"
        "- The GRADE-LEVEL ADAPTATION section tells you EXACTLY how to teach for this student's year. Follow it.\n"
        "- The NIGERIAN CURRICULUM CONTEXT section tells you what curriculum and exams are relevant.\n"
    )

    @staticmethod
    def get_or_create_chat(
        student: Student,
        subject_id: Optional[str] = None,
        topic_id: Optional[int] = None,
        title: str = ""
    ) -> StudentAITutorChat:
        chat = StudentAITutorChat.objects.create(
            student=student,
            subject_id=subject_id,
            topic_id=topic_id,
            title=title or "New Tutoring Session"
        )
        return chat

    @staticmethod
    def get_chat_history(chat: StudentAITutorChat) -> List[Dict[str, str]]:
        messages = chat.messages.all().order_by('created_at')
        history = []
        for m in messages:
            if m.role == 'assistant':
                try:
                    data = json.loads(m.content)
                    history.append({"role": "assistant", "content": data.get("content", "")})
                except (json.JSONDecodeError, TypeError):
                    history.append({"role": m.role, "content": m.content})
            else:
                history.append({"role": m.role, "content": m.content})
        return history

    @staticmethod
    def get_curriculum_context(chat: StudentAITutorChat) -> str:
        """Public accessor for curriculum context — used by both Reply and external callers."""
        return _get_student_curriculum_context(chat)

    @staticmethod
    def reply(chat: StudentAITutorChat, user_message: str) -> Dict[str, Any]:
        """
        Generate a tutor reply with full context awareness:
        - Student's class level (per-year adaptation)
        - Subject and topic context
        - Diagnostic assessment when starting
        - Nigerian curriculum alignment
        """
        # 1. Save user message
        StudentAITutorMessage.objects.create(
            chat=chat, role='user', content=user_message
        )

        # 2. Build message history for the AI
        history = TutorService.get_chat_history(chat)

        # 3. Determine the teaching phase
        is_diagnostic = _is_diagnostic_phase(chat)

        # 4. Build the system prompt with ALL student context
        curriculum_context = _get_student_curriculum_context(chat)

        diagnostic_instruction = (
            "This is the FIRST interaction. Start with a warm greeting and assess the student's "
            "current knowledge level. Be brief — 2-3 sentences. Ask what they know about the topic "
            "and how you can best help them."
        )
        teaching_instruction = (
            "Continue teaching based on what you now know about the student. Build on previous exchanges."
        )
        phase_instruction = diagnostic_instruction if is_diagnostic else teaching_instruction

        system_prompt = (
            f"{TutorService.AGENT_INSTRUCTIONS}\n\n"
            f"==================\n"
            f"STUDENT CONTEXT\n"
            f"==================\n"
            f"{curriculum_context}\n\n"
            f"==================\n"
            f"CURRENT PHASE: {'diagnostic' if is_diagnostic else 'teaching'}\n"
            f"{phase_instruction}\n"
            f"=================="
        )

        # 5. Call OpenAI
        client = get_openai_client()
        messages = [
            {"role": "system", "content": system_prompt},
            *history,
        ]

        response = client.chat.completions.create(
            model=get_default_model(),
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.7,
        )

        raw_reply = response.choices[0].message.content
        try:
            reply_data = json.loads(raw_reply)
        except (json.JSONDecodeError, TypeError):
            reply_data = {
                "phase": "teaching",
                "content": raw_reply or "Let me explain that differently...",
                "teacher_note": "I hope this helps! What do you think?",
                "suggested_actions": ["I understand", "Explain better", "Give me a practice question"],
                "current_step": "Teaching",
            }

        # Ensure required fields
        reply_data.setdefault("phase", "teaching")
        reply_data.setdefault("content", reply_data.get("content", ""))
        reply_data.setdefault("teacher_note", "")
        reply_data.setdefault("suggested_actions", ["I understand", "Explain better"])
        reply_data.setdefault("current_step", "Teaching")

        # 6. Auto-update chat title from the first user message if not set
        if chat.title in ("New Tutoring Session", ""):
            chat.title = user_message[:80]
            chat.save(update_fields=['title'])

        # 7. Save assistant message
        StudentAITutorMessage.objects.create(
            chat=chat,
            role='assistant',
            content=json.dumps(reply_data),
            metadata=reply_data,
        )

        return reply_data
