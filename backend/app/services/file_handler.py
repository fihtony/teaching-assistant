"""
File handling for reading essays and requirements.
Supports .txt, .docx, and .pdf formats.
"""

import os
from pathlib import Path
from typing import List, Tuple, Optional


def read_requirements_file(requirements_path: str) -> str:
    """
    Read the grading requirements from a file.

    Args:
        requirements_path: Path to requirements.txt file

    Returns:
        Requirements text content

    Raises:
        FileNotFoundError: If requirements file doesn't exist
    """
    path = Path(requirements_path)
    if not path.exists():
        raise FileNotFoundError(f"Requirements file not found: {requirements_path}")

    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def scan_student_essays(
    input_dir: str,
    pattern: Optional[str] = None
) -> List[Tuple[str, str, str]]:
    """
    Scan for student essay files in the input directory.

    Args:
        input_dir: Directory containing student essays
        pattern: Optional glob pattern (default: scans .txt, .docx, .pdf)

    Returns:
        List of tuples: (file_path, file_type, student_name)
    """
    path = Path(input_dir)
    if not path.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    # Default patterns: scan .txt, .docx, .pdf files starting with "student"
    if pattern is None:
        patterns = ["student*.txt", "student*.docx", "student*.pdf"]
    else:
        patterns = [pattern]

    results = []
    seen_files = set()

    for pat in patterns:
        files = list(path.glob(pat))
        for file_path in sorted(files):
            # Skip already seen files (when using multiple patterns)
            if file_path.name in seen_files:
                continue
            seen_files.add(file_path.name)

            # Get file type
            file_type = file_path.suffix.lstrip('.').lower()

            # Extract student name from filename
            stem = file_path.stem
            if stem.startswith("student"):
                number = stem.replace("student", "")
                student_name = f"Student {number}" if number else "Student"
            else:
                student_name = stem

            results.append((str(file_path), file_type, student_name))

    if not results:
        raise FileNotFoundError(f"No student essays found in: {input_dir}")

    return results


def read_essay(file_path: str) -> str:
    """
    Read a student essay from file.

    Supports .txt, .docx, and .pdf formats.

    Args:
        file_path: Path to the essay file

    Returns:
        Essay text content

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is not supported
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Essay file not found: {file_path}")

    ext = path.suffix.lower()

    # Text files - read directly
    if ext == '.txt':
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    # Word and PDF files - use document processor
    elif ext in ['.docx', '.pdf']:
        from document_processor import extract_document_text
        return extract_document_text(file_path)

    else:
        raise ValueError(f"Unsupported file format: {ext}")


def validate_paths(input_dir: str, requirements_path: Optional[str] = None) -> None:
    """
    Validate that input paths exist before processing.

    Args:
        input_dir: Directory containing student essays
        requirements_path: Optional path to requirements file

    Raises:
        FileNotFoundError: If any path doesn't exist
    """
    if not Path(input_dir).exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    if requirements_path and not Path(requirements_path).exists():
        raise FileNotFoundError(f"Requirements file not found: {requirements_path}")


def get_output_path(input_file: str, output_dir: Optional[str] = None) -> str:
    """
    Generate output path for graded file.

    Args:
        input_file: Path to input file
        output_dir: Optional output directory (default: same as input)

    Returns:
        Path for output file
    """
    input_path = Path(input_file)

    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        return str(out_path / f"{input_path.stem}_graded{input_path.suffix}")
    else:
        return str(input_path.parent / f"{input_path.stem}_graded{input_path.suffix}")
