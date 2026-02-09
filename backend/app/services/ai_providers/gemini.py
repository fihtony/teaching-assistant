"""
Google Gemini provider for essay grading.
"""

from typing import Optional

from .base import BaseAIProvider


class GeminiProvider(BaseAIProvider):
    """Google Gemini provider."""

    DEFAULT_MODEL = "gemini-1.5-pro"

    def __init__(self, api_key: str, model: Optional[str] = None):
        """
        Initialize Gemini provider.

        Args:
            api_key: Google API key
            model: Model name (default: gemini-1.5-pro)
        """
        super().__init__(api_key, model)
        self._model = None

    def _get_model(self):
        """Get or create Gemini model instance."""
        if self._model is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._model = genai.GenerativeModel(self.model or self.DEFAULT_MODEL)
            except ImportError:
                raise ImportError(
                    "google-generativeai is required for Gemini provider. "
                    "Install with: pip install google-generativeai"
                )
        return self._model

    async def grade_essay(
        self,
        essay: str,
        requirements: str,
        student_name: Optional[str] = None,
        student_level: Optional[str] = None,
        recent_activity: Optional[str] = None,
    ) -> str:
        """
        Grade essay using Google Gemini.

        Returns:
            HTML string with corrections and teacher comments
        """
        # Build prompt
        prompt = self._build_prompt(essay, requirements, student_name, student_level, recent_activity)

        model = self._get_model()

        try:
            # Gemini doesn't have native async, use sync in thread pool
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, model.generate_content, prompt)
            return response.text

        except Exception as e:
            raise Exception(f"Gemini request failed: {str(e)}")

    def _build_prompt(
        self,
        essay: str,
        requirements: str,
        student_name: Optional[str] = None,
        student_level: Optional[str] = None,
        recent_activity: Optional[str] = None,
    ) -> str:
        """Build the complete prompt from system template and requirements."""
        # Load base system prompt (same as ZhipuAI)
        system_prompt = self._load_system_prompt()

        # Replace placeholders
        prompt = system_prompt.replace("{student_name}", student_name or "Student")
        prompt = prompt.replace("{student_essay}", essay)
        prompt = prompt.replace("{grading_instructions}", requirements)

        return prompt

    def _load_system_prompt(self) -> str:
        """Load the base system prompt for grading."""
        # Same as ZhipuAI - could be shared
        return """# Essay Grading System - Base Prompt

You are an expert English teacher grading student essays.

## Output Format Requirements

- Use HTML format for all output (NOT Markdown)
- Include the following sections:
  1. **Revised Essay** - with HTML correction tags
  2. **Detailed Corrections** - HTML list with explanations
  3. **Teacher's Comments** - personalized feedback in HTML

## HTML Correction Tags

- **Deleted words/phrases** (student's original): `<del class="error">word</del>`
  - This displays as black text with red strikethrough
- **Added/Modified words/phrases** (teacher's correction): `<span class="correction">word</span>`
  - This displays as red text

**CRITICAL:**
- ALWAYS use HTML tags, never Markdown formatting
- Do NOT use `~~**word**~~` or `**word**` Markdown syntax
- Use `<p>` for paragraphs, `<h2>` for section headers, `<ul><li>` for lists

## Teacher's Comments Format (CRITICAL - FOLLOW EXACTLY)

```html
<h2>Teacher's Comments</h2>
<p>Dear Student [Number],</p>

<h3>What You Did Well</h3>
<ul>
  <li>First specific strength with example from the essay - complete explanation</li>
  <li>Second specific strength with example from the essay - complete explanation</li>
</ul>

<h3>Areas for Improvement</h3>
<ul>
  <li>First specific area with example + better model sentence - complete explanation</li>
  <li>Second specific area with example + better model sentence - complete explanation</li>
</ul>

<p>Encouraging closing sentence</p>
```

---

## Student Essay to Grade

**Student Name:** {student_name}

```
{student_essay}
```

---

## Grading Instructions

{grading_instructions}

---

## Additional Notes

- **CRITICAL:** ALL output must be in English
- **CRITICAL:** Follow the EXACT structure for Teacher's Comments with proper HTML formatting
"""

    async def validate_api_key(self) -> bool:
        """Validate if the Gemini API key is working."""
        try:
            model = self._get_model()
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, model.generate_content, "test")
            return True
        except Exception:
            return False
