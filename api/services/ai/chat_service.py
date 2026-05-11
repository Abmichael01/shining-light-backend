"""
AI Chat Assistant Service

Stateless conversational endpoint. The frontend keeps the message history;
each request includes:
    - the page context (so the assistant knows where the user is)
    - the full message history
    - the new user message

Returns the assistant's next reply and any approval actions the UI should render.
"""

import json
import os
from typing import List, Dict, Any
from .openai_client import get_openai_client, get_default_model
from .skills import TOOLS, execute_tool


# ---------------------------------------------------------------------------
# Constants & Context Loading
# ---------------------------------------------------------------------------
MAX_HISTORY_MESSAGES = 30
MAX_MESSAGE_CHARS = 2000

CONTEXT_DIR = os.path.join(os.path.dirname(__file__), "context")

def load_context_json(filename: str) -> Dict[str, Any]:
    path = os.path.join(CONTEXT_DIR, filename)
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)

PAGE_CONTEXT_HINTS = load_context_json("pages.json")
SCHOOL_INFO = load_context_json("school_info.json")

def build_admin_learning_memory(user_type: str) -> str:
    """Small behavior-memory summary from recent admin AI activity."""
    if user_type != 'admin':
        return ""

    try:
        from api.models import AIActionLog, AIMessageDraft

        rejected_reasons = list(
            AIMessageDraft.objects.filter(status='rejected')
            .exclude(rejection_reason='')
            .order_by('-rejected_at')
            .values_list('rejection_reason', flat=True)[:5]
        )
        approved_actions = list(
            AIActionLog.objects.filter(status='approved')
            .order_by('-approved_at')
            .values_list('summary', flat=True)[:5]
        )
    except Exception:
        return ""

    lines = []
    if rejected_reasons:
        lines.append("Recent admin feedback on rejected AI drafts:")
        lines.extend(f"- {reason[:220]}" for reason in rejected_reasons)
    if approved_actions:
        lines.append("Recent AI actions admins approved:")
        lines.extend(f"- {summary[:220]}" for summary in approved_actions if summary)

    if not lines:
        return ""
    return "\nADMIN AI MEMORY:\n" + "\n".join(lines) + "\nUse this as preference guidance, not as guaranteed current facts.\n"

def build_system_prompt(page_type: str = "", user: Any = None) -> str:
    """Compose the full system prompt from static info, page hints, and user identity."""
    info = SCHOOL_INFO
    persona = info.get("ai_persona", {})
    
    user_type = getattr(user, 'user_type', 'unknown') if user else 'unknown'
    user_name = "User"
    if user_type == 'student' and hasattr(user, 'student_profile'):
        user_name = user.student_profile.get_full_name()
    elif user_type in ['admin', 'staff']:
        user_name = user.email.split('@')[0].capitalize()

    base = (
        f"Your name is {persona.get('name', 'Lumina')}. You are the general-purpose intelligent "
        f"assistant for the entire Shining Light International School platform. You have "
        f"knowledge of all administrative modules including academics, finance, and students.\n\n"
        f"School Motto: '{info.get('motto')}'\n"
        f"Divisions: {', '.join(info.get('divisions', []))}\n"
        f"Tone: {persona.get('tone')}\n\n"
        f"USER IDENTITY: You are currently speaking with {user_name} ({user_type}).\n"
    )
    
    if user_type == 'student':
        base += "PRIVACY NOTE: This user is a student. You can only share information about THEIR OWN results, subjects, and schedules. Never disclose data about other students or school finances.\n\n"
    
    page_hint = PAGE_CONTEXT_HINTS.get(page_type, "")
    if page_hint:
        base += (
            f"CURRENT LOCATION: The user is currently viewing the following page: '{page_type}'.\n"
            f"Page Description: {page_hint}\n"
            "Only focus on this specific page if the user asks about 'this page', 'here', "
            "or 'what I am seeing'. Otherwise, remain a general assistant for the whole school.\n\n"
        )

    base += build_admin_learning_memory(user_type)
    
    base += (
        "Guidelines:\n"
        "- Be warm and friendly. Greet the user naturally and show a supportive, helpful attitude.\n"
        "- You are a general expert. Answer any question about school management, even if "
        "it's not related to the current page.\n"
        "- Use the 'CURRENT LOCATION' hint only to add specific context when the user "
        "refers to their immediate screen.\n"
        "- You can query live school data (students, fees, etc.) using available tools.\n"
        "- For emails or SMS, use create_message_draft when an admin asks you to draft or prepare "
        "a message. Never claim a message has been sent; explain that the draft must be reviewed "
        "and approved from Communications > AI Assist.\n"
        "- If an admin clearly asks to change a fee type amount, use update_fee_type_amount to "
        "prepare the change for approval. This does not update the fee immediately. When the tool "
        "returns an approval action, tell the admin to use the approval button below and do not "
        "claim the fee has been updated until it has been approved.\n"
        "- If an admin clearly asks to edit any other school record, use update_record_fields to "
        "prepare the edit for approval. For student name edits, call update_record_fields with "
        "model_name='students', the student/application/admission ID as record_id, and "
        "fields={'full_name': 'Surname Firstname Othernames'}. Never claim a record has been "
        "updated until the approval action succeeds.\n"
        "- Do not directly change data without an approval action. If a requested edit is ambiguous, "
        "ask for the exact record ID or field before preparing the action.\n"
        "- **Formatting**: Always use Markdown for readability. Use bullet points for lists, "
        "bold text for emphasis, and tables for data comparisons. Avoid large blocks of plain text.\n"
        "- Keep replies concise and grounded in the management system data.\n"
        "- Use Nigerian terms naturally (₦, Naira)."
    )
    return base


class ChatService:
    """Service class for AI chat operations."""

    @staticmethod
    def validate_messages(messages: List[Dict[str, str]]) -> None:
        if not isinstance(messages, list) or not messages:
            raise ValueError("messages must be a non-empty list")
        if len(messages) > MAX_HISTORY_MESSAGES:
            raise ValueError(f"Conversation too long (max {MAX_HISTORY_MESSAGES} messages)")
        for m in messages:
            if not isinstance(m, dict):
                raise ValueError("Each message must be an object")
            if m.get('role') not in ('user', 'assistant'):
                raise ValueError("Each message must have role 'user' or 'assistant'")
            content = m.get('content') or ''
            if not isinstance(content, str):
                raise ValueError("Each message content must be a string")
            if len(content) > MAX_MESSAGE_CHARS:
                raise ValueError(f"Message too long (max {MAX_MESSAGE_CHARS} characters)")

    @staticmethod
    def reply(messages: List[Dict[str, str]], page_type: str = "", user: Any = None) -> Dict[str, Any]:
        """Generate the next assistant reply, handling tool calls if needed."""
        ChatService.validate_messages(messages)

        system_prompt = build_system_prompt(page_type, user)
        sanitized_messages = [
            {"role": m["role"], "content": m.get("content") or ""}
            for m in messages
        ]
        openai_messages = [{"role": "system", "content": system_prompt}, *sanitized_messages]
        actions = []

        client = get_openai_client()
        
        # 1. Initial completion with tool calling enabled
        response = client.chat.completions.create(
            model=get_default_model(),
            messages=openai_messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.4,
        )
        
        message = response.choices[0].message
        
        # 2. Check if AI wants to call a tool
        if message.tool_calls:
            openai_messages.append(message)
            
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)
                
                # Execute the skill via dispatcher with user context
                result = execute_tool(func_name, func_args, user=user)
                if isinstance(result, dict) and result.get("requires_approval") and result.get("action"):
                    actions.append(result["action"])
                
                openai_messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": func_name,
                    "content": json.dumps(result, default=str),
                })
            
            # 3. Final completion with tool results
            final_response = client.chat.completions.create(
                model=get_default_model(),
                messages=openai_messages,
            )
            return {
                "reply": final_response.choices[0].message.content or "",
                "actions": actions,
            }
        
        return {"reply": message.content or "", "actions": []}
