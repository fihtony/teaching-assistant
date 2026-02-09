"""
ZhipuAI GLM provider for essay grading.
"""

import asyncio
import httpx
from typing import Optional

from .base import BaseAIProvider


class ZhipuAIProvider(BaseAIProvider):
    """ZhipuAI GLM provider."""

    BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
    DEFAULT_MODEL = "glm-4.7"

    def __init__(self, api_key: str, model: Optional[str] = None):
        """
        Initialize ZhipuAI provider.

        Args:
            api_key: ZhipuAI API key
            model: Model name (default: glm-4.7)
        """
        super().__init__(api_key, model)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def grade_essay(
        self,
        essay: str,
        requirements: str,
        student_name: Optional[str] = None,
        student_level: Optional[str] = None,
        recent_activity: Optional[str] = None,
    ) -> str:
        """
        Grade essay using ZhipuAI GLM.

        Returns:
            HTML string with corrections and teacher comments
        """
        # Build prompt with system template
        prompt = self._build_prompt(essay, requirements, student_name, student_level, recent_activity)

        model = self.model or self.DEFAULT_MODEL

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        }

        client = await self._get_client()

        try:
            response = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

            data = response.json()
            return data["choices"][0]["message"]["content"]

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # Rate limit - wait and retry once
                await asyncio.sleep(5)
                response = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                raise Exception(f"ZhipuAI API error: {e.response.status_code} - {e.response.text}")

        except Exception as e:
            raise Exception(f"ZhipuAI request failed: {str(e)}")

    def _build_prompt(
        self,
        essay: str,
        requirements: str,
        student_name: Optional[str] = None,
        student_level: Optional[str] = None,
        recent_activity: Optional[str] = None,
    ) -> str:
        """Build the complete prompt from system template and requirements."""
        # Load base system prompt
        system_prompt = self._load_system_prompt()

        # Replace placeholders
        prompt = system_prompt.replace("{student_name}", student_name or "Student")
        prompt = prompt.replace("{student_essay}", essay)
        prompt = prompt.replace("{grading_instructions}", requirements)

        return prompt

    def _load_system_prompt(self) -> str:
        """Load the base system prompt for grading."""
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

**Example:**
```html
Many people have <del class="error">an answer about</del><span class="correction">different opinions on</span> the most important...
```

**CRITICAL:**
- ALWAYS use HTML tags, never Markdown formatting
- Do NOT use `~~**word**~~` or `**word**` Markdown syntax
- Use `<p>` for paragraphs, `<h2>` for section headers, `<ul><li>` for lists

## Teacher's Comments Format (CRITICAL - FOLLOW EXACTLY)

The Teacher's Comments section MUST follow this EXACT structure with proper HTML formatting:

```html
<h2>Teacher's Comments</h2>
<p>Dear Student [Number],</p>
<p>[Optional: 1 warm greeting sentence based on context]</p>

<h3>What You Did Well</h3>
<ul>
  <li>First specific strength with example from the essay - complete explanation</li>
  <li>Second specific strength with example from the essay - complete explanation</li>
  <li>Third specific strength with example if applicable - complete explanation</li>
</ul>

<h3>Areas for Improvement</h3>
<ul>
  <li>First specific area with example + better model sentence - complete explanation</li>
  <li>Second specific area with example + better model sentence - complete explanation</li>
  <li>Third specific area with example if applicable - complete explanation</li>
</ul>

<p>Encouraging closing sentence</p>
```

**CRITICAL FORMATTING RULES:**
1. Use HTML `<ul>` and `<li>` for bullet lists
2. Each bullet point must be in a separate `<li>` tag
3. Use `<h2>` for "Teacher's Comments" header
4. Use `<h3>` for "What You Did Well" and "Areas for Improvement" headers
5. Use `<p>` tags for paragraphs

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

- Follow the grading instructions above for detailed criteria
- Use the exact HTML correction tags specified
- **CRITICAL:** ALL output must be in English (essay, corrections, comments)
- **CRITICAL:** Follow the EXACT structure for Teacher's Comments with proper HTML formatting
"""

    async def validate_api_key(self) -> bool:
        """Validate if the ZhipuAI API key is working."""
        try:
            client = await self._get_client()
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model or self.DEFAULT_MODEL,
                "messages": [{"role": "user", "content": "test"}],
            }

            response = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            )

            return response.status_code == 200

        except Exception:
            return False
