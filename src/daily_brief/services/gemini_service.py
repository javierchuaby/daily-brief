"""Gemini AI service implementation with Structured Outputs."""

import json
from datetime import datetime, timedelta
from typing import Any, Dict
from pydantic import BaseModel, Field
from google import genai
from daily_brief.interfaces import AIService

class BriefItem(BaseModel):
    source: str = Field(description="Source of the item (e.g., Canvas, Coursemology, or specific course code)")
    title: str = Field(description="Title of the assignment, announcement, or quiz")
    date_str: str = Field(description="Formatted date string (e.g., 'Due: 2026-09-19' or 'Posted: 2026-09-18')")
    action_item: str = Field(description="A concise 1-sentence summary of the item's content. If it's an assignment, state the key requirement. If it's an announcement, summarize its main message.")

class DailyBriefSchema(BaseModel):
    urgent: list[BriefItem] = Field(description="Urgent items due Today or Tomorrow")
    important: list[BriefItem] = Field(description="Important items due this week (excluding Today/Tomorrow)")
    recent_updates: list[BriefItem] = Field(description="Recent updates and announcements")
    later_deadlines: list[BriefItem] = Field(description="Deadlines strictly after this week")

class GeminiAIService(AIService):
    """AI service using Gemini API and Structured Outputs."""

    def __init__(self, model: str = "gemini-3.1-flash-lite"):
        self.model = model
        self.client = genai.Client() # Picks up GEMINI_API_KEY from environment

    def synthesize(self, data: Dict[str, Any], current_date_str: str) -> str:
        # Calculate dates for reasoning context
        try:
            current_date = datetime.strptime(current_date_str, "%Y-%m-%d").date()
        except ValueError:
            current_date = datetime.now().date()
            
        tomorrow = current_date + timedelta(days=1)
        # Calculate days until Sunday (end of week). If today is Sunday (6), days_until = 0.
        days_until_sunday = 6 - current_date.weekday()
        end_of_week = current_date + timedelta(days=days_until_sunday)
        
        prompt = (
            f"You are a helpful student assistant. Generate a structured daily brief based on the provided data.\n"
            f"Temporal Context:\n"
            f"- Today: {current_date}\n"
            f"- Tomorrow: {tomorrow}\n"
            f"- End of Week (Sunday): {end_of_week}\n\n"
            f"Categorize items according to the schema:\n"
            f"- urgent: due Today or Tomorrow.\n"
            f"- important: due after tomorrow but before or on the End of Week.\n"
            f"- recent_updates: general announcements.\n"
            f"- later_deadlines: due strictly after the End of Week.\n\n"
            f"CRITICAL RULES:\n"
            f"1. ONLY items from the 'assignments', 'quizzes', or 'assessments' JSON arrays belong in urgent, important, or later_deadlines.\n"
            f"2. Items from the 'announcements' JSON array MUST go into recent_updates, EVEN IF the announcement message mentions a deadline. (True assignments are tracked in their own arrays, so do not duplicate them from announcements).\n\n"
            f"Raw Data:\n{json.dumps(data, default=str)}"
        )

        import time
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                interaction = self.client.interactions.create(
                    model=self.model,
                    input=prompt,
                    response_format={
                        "type": "text",
                        "mime_type": "application/json",
                        "schema": DailyBriefSchema.model_json_schema()
                    }
                )
                structured_data = DailyBriefSchema.model_validate_json(interaction.output_text)
                return self._render_markdown(structured_data)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Gemini AI synthesis failed: {e}")
                time.sleep(2 ** attempt)

    def _render_markdown(self, data: DailyBriefSchema) -> str:
        lines = []
        
        def add_items(items: list[BriefItem], default_msg: str = "- None"):
            if not items:
                lines.append(default_msg)
            for item in items:
                if item.action_item:
                    lines.append(f"- [{item.source}] **{item.title}** ({item.date_str}): {item.action_item}")
                else:
                    lines.append(f"- [{item.source}] **{item.title}** ({item.date_str})")

        lines.append("## 🚨 URGENT (Today/Tomorrow)")
        add_items(data.urgent)
        lines.append("")
        
        lines.append("## 📌 IMPORTANT (This Week)")
        add_items(data.important)
        lines.append("")
        
        lines.append("## 📢 INFO (For Awareness)")
        lines.append("### Recent Updates & Announcements")
        add_items(data.recent_updates)
        lines.append("")
        
        lines.append("### Later Deadlines")
        add_items(data.later_deadlines)
        
        return "\n".join(lines)
