"""
HTML Generator for AI Grading System
Generates single HTML file with red-ink annotations for student essays.
"""

from typing import Tuple


class HTMLGenerator:
    """Generate graded essay as HTML with red-ink corrections."""

    def generate(
        self,
        essay: str,
        corrections: str,
        comments: str,
        output_path: str,
        student_name: str = "Student"
    ) -> str:
        """
        Generate complete HTML file with embedded styles.

        Args:
            essay: Student essay with HTML correction tags
            corrections: Detailed corrections section (HTML)
            comments: Teacher's comments section (HTML)
            output_path: Where to save the HTML file
            student_name: Optional student name for title

        Returns:
            Path to generated HTML file
        """
        html_content = self._build_html(essay, corrections, comments, student_name)
        self._save_html(html_content, output_path)
        return output_path

    def _build_html(
        self,
        essay: str,
        corrections: str,
        comments: str,
        student_name: str = "Student"
    ) -> str:
        """Build complete HTML document with embedded CSS."""
        css = self._get_css_styles()
        title = f"Graded Essay - {student_name}"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
{css}
    </style>
</head>
<body>
    <h1>Revised Essay</h1>
    {self._wrap_in_paragraphs(essay)}

    {corrections}

    {comments}
</body>
</html>"""

    def _wrap_in_paragraphs(self, content: str) -> str:
        """
        Wrap essay content in paragraph tags if not already wrapped.
        Handle mixed content (some with tags, some without).
        """
        lines = content.split('\n')
        wrapped_lines = []
        current_paragraph = []

        for line in lines:
            line = line.strip()

            # Skip empty lines
            if not line:
                if current_paragraph:
                    wrapped_lines.append(f"<p>{' '.join(current_paragraph)}</p>")
                    current_paragraph = []
                continue

            # Already has HTML tags - keep as is
            if line.startswith('<') and any(tag in line for tag in ['<h1>', '<h2>', '<h3>', '<p>', '<ul>', '<li>']):
                if current_paragraph:
                    wrapped_lines.append(f"<p>{' '.join(current_paragraph)}</p>")
                    current_paragraph = []
                wrapped_lines.append(line)
            else:
                current_paragraph.append(line)

        # Don't forget the last paragraph
        if current_paragraph:
            wrapped_lines.append(f"<p>{' '.join(current_paragraph)}</p>")

        return '\n'.join(wrapped_lines)

    def _get_css_styles(self) -> str:
        """Return CSS styles for red-ink grading."""
        return """/* Base styles */
body {
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 16px;
    line-height: 1.8;
    color: #000;
    max-width: 800px;
    margin: 40px auto;
    padding: 20px;
    background: #fff;
}

/* Red strikethrough - black text, red line */
.error {
    text-decoration: line-through;
    text-decoration-color: #e74c3c;
    text-decoration-thickness: 2px;
    color: #000;
}

/* Red correction text */
.correction {
    color: #e74c3c;
    font-weight: 500;
}

/* Headers */
h1 {
    font-size: 24px;
    margin-bottom: 20px;
    color: #000;
    border-bottom: 2px solid #e74c3c;
    padding-bottom: 10px;
}

h2 {
    font-size: 20px;
    margin-top: 30px;
    margin-bottom: 15px;
    color: #000;
}

h3 {
    font-size: 18px;
    margin-top: 20px;
    margin-bottom: 10px;
    color: #000;
}

/* Paragraphs */
p {
    margin-bottom: 15px;
    text-align: justify;
}

/* Lists */
ul {
    margin-left: 25px;
    margin-bottom: 15px;
}

li {
    margin-bottom: 10px;
}

/* Strong text */
strong {
    font-weight: 600;
}
"""

    def _save_html(self, content: str, path: str):
        """Save HTML content to file."""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)


def parse_ai_response(result: str) -> Tuple[str, str, str]:
    """
    Parse AI response into three HTML sections.

    Args:
        result: Raw AI response containing HTML

    Returns:
        Tuple of (essay_html, corrections_html, comments_html)
    """
    # Split by h2 headers
    sections = result.split('<h2>')

    essay_html = ""
    corrections_html = ""
    comments_html = ""

    for i, section in enumerate(sections):
        section_lower = section.lower()

        # First section - contains essay (before any h2)
        if i == 0:
            essay_html = extract_essay_content(section)

        # Corrections section
        elif 'correction' in section_lower or 'detailed' in section_lower:
            corrections_html = f"<h2>{section}"

        # Teacher comments section
        elif 'teacher' in section_lower and 'comment' in section_lower:
            comments_html = f"<h2>{section}"

    return essay_html, corrections_html, comments_html


def extract_essay_content(section: str) -> str:
    """
    Extract essay content from the first section.
    Returns content after h1 tag, excluding the header itself.
    """
    lines = section.split('\n')
    content = []
    skip_h1 = True

    for line in lines:
        line = line.strip()

        # Skip the h1 header line
        if skip_h1:
            if '<h1>' in line or '<h1 ' in line:
                continue
            if not line:
                continue
            skip_h1 = False

        # Stop at next section header
        if line.startswith('<h2>') or line.startswith('<h2 '):
            break

        # Collect essay content
        if line:
            content.append(line)

    return '\n'.join(content)
