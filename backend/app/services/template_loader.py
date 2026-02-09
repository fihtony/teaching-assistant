"""
Template loader for grading instruction templates.
Loads and manages pre-defined grading templates from instructions/ directory.
Supports both Markdown (.md) and YAML (.yaml) formats.
"""

import os
import re
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List


class TemplateNotFoundError(Exception):
    """Raised when a template file is not found."""
    pass


class TemplateLoader:
    """Loads and formats grading instruction templates."""

    def __init__(self, instructions_dir: Optional[str] = None):
        """
        Initialize the template loader.

        Args:
            instructions_dir: Path to instructions directory (default: ./instructions/)
        """
        if instructions_dir is None:
            # Default to instructions/ relative to this file
            self.instructions_dir = Path(__file__).parent / "instructions"
        else:
            self.instructions_dir = Path(instructions_dir)

    def list_templates(self) -> List[Dict[str, str]]:
        """
        List all available templates.

        Returns:
            List of dicts with template info (name, description, filename, format)
        """
        templates = []
        if not self.instructions_dir.exists():
            return templates

        # Check for .md files first, then .yaml files
        for md_file in sorted(self.instructions_dir.glob("*.md")):
            try:
                info = self._parse_markdown_header(md_file)
                templates.append({
                    "filename": md_file.stem,
                    "format": "markdown",
                    "name": info.get("name", md_file.stem),
                    "description": info.get("description", ""),
                    "grade_level": info.get("grade_level", ""),
                    "essay_type": info.get("essay_type", ""),
                })
            except Exception:
                continue

        for yaml_file in sorted(self.instructions_dir.glob("*.yaml")):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    templates.append({
                        "filename": yaml_file.stem,
                        "format": "yaml",
                        "name": data.get("name", yaml_file.stem),
                        "description": data.get("description", ""),
                        "grade_level": data.get("grade_level", ""),
                        "essay_type": data.get("essay_type", ""),
                    })
            except Exception:
                continue

        return templates

    def _parse_markdown_header(self, md_file: Path) -> Dict[str, str]:
        """Parse the frontmatter-style header from a Markdown template."""
        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()

        info = {}
        lines = content.split('\n')

        # Parse title (first line starting with #)
        for line in lines:
            if line.strip().startswith('#'):
                info["name"] = line.strip().lstrip('#').strip()
                break

        # Parse metadata fields
        for line in lines:
            if '**Grade Level:**' in line:
                info["grade_level"] = line.split('**Grade Level:**')[1].strip()
            elif '**Essay Type:**' in line:
                info["essay_type"] = line.split('**Essay Type:**')[1].strip()
            elif line.strip().startswith('**Description:**') or '**Description**' in line:
                info["description"] = line.split(':**')[1].strip() if ':**' in line else ""

        return info

    def load_template(self, template_name: str) -> str:
        """
        Load a specific template by name and return its content.

        Args:
            template_name: Name of the template (without extension)

        Returns:
            Template content as a string

        Raises:
            TemplateNotFoundError: If template file doesn't exist
        """
        # Try .md first, then .yaml
        md_path = self.instructions_dir / f"{template_name}.md"
        yaml_path = self.instructions_dir / f"{template_name}.yaml"

        if md_path.exists():
            with open(md_path, "r", encoding="utf-8") as f:
                return f.read()
        elif yaml_path.exists():
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                # Convert YAML to text format
                return self._yaml_to_text(data)
        else:
            available = [t["filename"] for t in self.list_templates()]
            raise TemplateNotFoundError(
                f"Template '{template_name}' not found. "
                f"Available templates: {', '.join(available) if available else 'none'}"
            )

    def _yaml_to_text(self, data: Dict[str, Any]) -> str:
        """Convert YAML template data to text format (for backwards compatibility)."""
        lines = []
        lines.append(f"# {data.get('name', '')}")
        lines.append(f"# {data.get('description', '')}\n")

        for item in data.get("grading_focus", []):
            lines.append(f"\n## {item['area']} (Priority {item['priority']})")
            for detail in item.get("details", []):
                lines.append(f"- {detail}")

        return "\n".join(lines)


def get_available_templates() -> List[str]:
    """
    Get list of available template names.

    Returns:
        List of template names (without extension)
    """
    loader = TemplateLoader()
    return [t["filename"] for t in loader.list_templates()]


def load_template_instructions(template_name: str) -> str:
    """
    Load template content.

    Args:
        template_name: Name of the template

    Returns:
        Template content

    Raises:
        TemplateNotFoundError: If template doesn't exist
    """
    loader = TemplateLoader()
    return loader.load_template(template_name)
