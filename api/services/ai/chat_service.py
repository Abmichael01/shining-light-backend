"""
AI Chat Assistant Service

Stateless conversational endpoint. The frontend keeps the message history;
each request includes:
    - the page context (so the assistant knows where the user is)
    - the full message history
    - the new user message

Returns the assistant's next reply as plain text.
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
    
    base += (
        "Guidelines:\n"
        "- You are a general expert. Answer any question about school management, even if "
        "it's not related to the current page.\n"
        "- Use the 'CURRENT LOCATION' hint only to add specific context when the user "
        "refers to their immediate screen.\n"
        "- You can query live school data (students, fees, etc.) using available tools.\n"
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
    def reply(messages: List[Dict[str, str]], page_type: str = "", user: Any = None) -> str:
        """Generate the next assistant reply, handling tool calls if needed."""
        ChatService.validate_messages(messages)

        system_prompt = build_system_prompt(page_type, user)
        openai_messages = [{"role": "system", "content": system_prompt}, *messages]

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
                
                openai_messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": func_name,
                    "content": json.dumps(result),
                })
            
            # 3. Final completion with tool results
            final_response = client.chat.completions.create(
                model=get_default_model(),
                messages=openai_messages,
            )
            return final_response.choices[0].message.content or ""
        
        return message.content or ""
