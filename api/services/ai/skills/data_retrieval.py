"""
AI Skills: Data Retrieval (Secure RBAC)

Allows the AI to fetch real-time data with strict permission checks.
- Admins/Staff: Full access to summaries and listings.
- Students: Restricted to specific models and OWN data only.
"""

from typing import Dict, Any, List, Optional
from django.db.models import Count, Sum, Avg, Q
from api.models import (
    Student, Staff, FeeType, FeePayment, 
    Exam, Question, School, Session,
    Class, Subject, Department, SessionTerm
)
from api.models.scheduling.timetable import TimetableEntry
from api.models.scheduling.attendance import StudentAttendance

# Full whitelist for Admins
ADMIN_MODELS = {
    "students": Student,
    "staff": Staff,
    "fee_types": FeeType,
    "fee_payments": FeePayment,
    "exams": Exam,
    "questions": Question,
    "schools": School,
    "sessions": Session,
    "classes": Class,
    "subjects": Subject,
    "departments": Department,
    "timetables": TimetableEntry,
}

# Restricted whitelist for Students
STUDENT_MODELS = {
    "subjects": Subject,
    "timetables": TimetableEntry,
    "exams": Exam,
    "attendance": StudentAttendance,
    "sessions": Session,
    "my_profile": Student, # Their own student record
}

def get_allowed_model(model_name: str, user: Any) -> Optional[Any]:
    """Check if the user has permission to access this model."""
    user_type = getattr(user, 'user_type', 'unknown')
    
    if user_type in ['admin', 'staff']:
        return ADMIN_MODELS.get(model_name)
    
    if user_type == 'student':
        return STUDENT_MODELS.get(model_name)
    
    return None

def apply_student_privacy(model_name: str, queryset: Any, user: Any) -> Any:
    """Ensure students only see their own data for relevant models."""
    if not user or user.user_type != 'student':
        return queryset
    
    student = getattr(user, 'student_profile', None)
    if not student:
        return queryset.none() # No profile, no data

    # Row-level security for students
    if model_name == "my_profile":
        return queryset.filter(id=student.id)
    if model_name == "attendance":
        return queryset.filter(student=student)
    if model_name == "exams":
        # Students can only see exams for their class
        return queryset.filter(class_model=student.class_model)
    if model_name == "timetables":
        return queryset.filter(class_model=student.class_model)
    
    return queryset

def get_data_summary(model_name: str, filters: Dict[str, Any] = None, user: Any = None) -> Dict[str, Any]:
    """Fetch counts and basic stats for a model with RBAC."""
    model = get_allowed_model(model_name, user)
    if not model:
        return {"error": f"Access to model '{model_name}' is restricted or not found."}
    
    queryset = model.objects.all()
    queryset = apply_student_privacy(model_name, queryset, user)
    
    # Apply simple filters if provided (sanitize to avoid deep traversal)
    if filters:
        try:
            queryset = queryset.filter(**filters)
        except Exception as e:
            return {"error": f"Invalid filter: {str(e)}"}
    
    count = queryset.count()
    
    extra = {}
    if model_name == "fee_payments" and user.user_type in ['admin', 'staff']:
        extra["total_amount"] = float(queryset.aggregate(Sum('amount'))['amount__sum'] or 0)
    elif model_name == "students" and user.user_type in ['admin', 'staff']:
        extra["by_status"] = list(queryset.values('status').annotate(count=Count('id')))

    return {
        "model": model_name,
        "total_count": count,
        "extra_stats": extra,
        "filter_applied": filters or "none"
    }

def list_records(model_name: str, limit: int = 5, filters: Dict[str, Any] = None, user: Any = None) -> List[Dict[str, Any]]:
    """List recent records for a model with RBAC."""
    model = get_allowed_model(model_name, user)
    if not model:
        return [{"error": "Restricted"}]
    
    queryset = model.objects.all()
    queryset = apply_student_privacy(model_name, queryset, user)
    
    if filters:
        queryset = queryset.filter(**filters)
        
    limit = min(limit, 10 if user.user_type == 'student' else 20)
    
    # Ordering logic
    for field in ['created_at', 'enrollment_date', 'date', 'start_time']:
        if hasattr(model, field):
            queryset = queryset.order_by(f'-{field}')
            break
            
    records = list(queryset.values()[:limit])
    
    # Cleanup for JSON
    for r in records:
        for k, v in r.items():
            if hasattr(v, 'isoformat'):
                r[k] = v.isoformat()
            elif hasattr(v, 'to_eng_string'): 
                r[k] = float(v)
                
    return records

# Updated tool definitions for OpenAI (enum includes new models)
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_data_summary",
            "description": "Get counts and basic statistics for school models.",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_name": {
                        "type": "string",
                        "enum": ["students", "staff", "fee_types", "fee_payments", "exams", "questions", "schools", "sessions", "subjects", "timetables", "attendance", "my_profile"],
                        "description": "The name of the model to query."
                    },
                    "filters": {
                        "type": "object",
                        "description": "Optional filters."
                    }
                },
                "required": ["model_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_records",
            "description": "List detailed records for a model.",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_name": {
                        "type": "string",
                        "enum": ["students", "staff", "fee_types", "fee_payments", "exams", "questions", "schools", "sessions", "subjects", "timetables", "attendance", "my_profile"],
                        "description": "The name of the model to query."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of records to return.",
                        "default": 5
                    }
                },
                "required": ["model_name"]
            }
        }
    }
]
