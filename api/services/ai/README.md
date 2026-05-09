# AI Reporting & Chat Service

This service provides automated AI-generated reports and interactive chat capabilities for school administrators.

## Registry Pattern

The system uses a registry pattern to keep page-specific logic decoupled from the general AI service. 

- **Frontend**: Any page can call `<AIPageActions pageType="your-page" />`.
- **Backend**: The `AIReportView` looks up the `pageType` in the `report_handlers` registry.

## Customizing Report Prompts

Existing report handlers are located in `backend/api/services/ai/report_handlers/`.

To tune the output of a report (e.g., changing the tone, adding specific requirements, or adjusting chart suggestions):

1. Open the corresponding handler file (e.g., `dashboard_snapshot.py`).
2. Locate the `build_prompt` method.
3. Modify the prompt string. Look for the `TODO (HUMAN INPUT)` block for guidance.

```python
def build_prompt(self, data: Dict[str, Any], extra_instruction: str = "") -> str:
    # Tune this string to change what the AI focuses on
    return f"""Produce a report based on: {data} ..."""
```

## Adding a New Report Template

1. Create a new file in `backend/api/services/ai/report_handlers/` (e.g., `student_finance.py`).
2. Define a class that inherits from `ReportHandler`.
3. Implement `slug`, `name`, `description`, `page_type`.
4. Implement `fetch_data` to gather necessary Django models/stats.
5. Implement `build_prompt`.
6. Use the `@register_handler` decorator.

```python
from ..report_generator import ReportHandler, register_handler

@register_handler
class MyNewHandler(ReportHandler):
    slug = "finance.arrears"
    name = "Arrears Deep Dive"
    page_type = "finance"
    
    def fetch_data(self, payload):
        return {"stats": ...}
        
    def build_prompt(self, data, extra):
        return "..."
```

## Chat Context

The chat service (`chat_service.py`) automatically receives context based on the `pageType`. You can extend `get_page_context` in `chat_service.py` to provide more specific data to the AI when a user starts a chat from a specific page.
