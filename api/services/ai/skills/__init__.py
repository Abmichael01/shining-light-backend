"""
AI Skills Registry

Aggregates all tool definitions and implementation functions for Lumina.
"""

from typing import Any
from . import data_retrieval

# Aggregate all tool definitions for OpenAI
TOOLS = [
    *data_retrieval.TOOLS,
    # Add more skill tools here...
]

# Dispatcher to route tool calls to their implementations
def execute_tool(name: str, args: dict, user: Any = None):
    """Routes a tool call to the correct function with user context."""
    if name == "get_data_summary":
        return data_retrieval.get_data_summary(**args, user=user)
    if name == "list_records":
        return data_retrieval.list_records(**args, user=user)
    if name == "create_message_draft":
        return data_retrieval.create_message_draft(**args, user=user)
    if name == "update_fee_type_amount":
        return data_retrieval.update_fee_type_amount(**args, user=user)
    if name == "update_record_fields":
        return data_retrieval.update_record_fields(**args, user=user)
    
    return {"error": f"Tool '{name}' not found in registry."}
