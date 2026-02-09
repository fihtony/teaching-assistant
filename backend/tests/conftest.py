"""
Test configuration and fixtures
"""

import pytest
import os
import tempfile
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="session")
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        yield f.name
    os.unlink(f.name)


@pytest.fixture(scope="session")
def temp_dirs():
    """Create temporary directories for testing."""
    import tempfile

    base_dir = tempfile.mkdtemp()
    dirs = {
        "uploads": os.path.join(base_dir, "uploads"),
        "graded": os.path.join(base_dir, "graded"),
        "cache": os.path.join(base_dir, "cache"),
        "logs": os.path.join(base_dir, "logs"),
    }

    for d in dirs.values():
        os.makedirs(d, exist_ok=True)

    yield dirs

    # Cleanup
    import shutil

    shutil.rmtree(base_dir)


@pytest.fixture
def mock_ai_response():
    """Mock AI response for grading."""
    return {
        "total_score": 85,
        "sections": [
            {
                "type": "mcq",
                "score": 90,
                "max_score": 100,
                "feedback": "Good understanding of the material.",
                "details": [],
            },
            {
                "type": "essay",
                "score": 80,
                "max_score": 100,
                "feedback": "Well-structured essay with minor grammatical errors.",
                "details": [
                    {
                        "issue": "grammar",
                        "location": "paragraph 2",
                        "suggestion": "Check verb tense",
                    }
                ],
            },
        ],
        "overall_feedback": "Solid performance overall. Focus on improving essay structure.",
        "encouragement": "Keep up the great work!",
        "annotations": [
            {"start": 10, "end": 20, "type": "correct", "color": "green"},
            {
                "start": 50,
                "end": 60,
                "type": "error",
                "color": "red",
                "comment": "Spelling error",
            },
        ],
    }


@pytest.fixture
def sample_assignment_text():
    """Sample assignment text for testing."""
    return """
    Name: John Smith
    Date: October 15, 2024
    
    Part A: Multiple Choice (Circle the correct answer)
    
    1. The capital of France is:
       a) London  b) Paris  c) Berlin  d) Madrid
       Answer: b
    
    2. Which planet is closest to the Sun?
       a) Venus  b) Earth  c) Mercury  d) Mars
       Answer: c
    
    Part B: True or False
    
    1. The Earth is flat. (False)
    2. Water boils at 100°C at sea level. (True)
    
    Part C: Short Answer
    
    1. Describe the water cycle in 2-3 sentences.
    
    The water cycle is the continuous movement of water within Earth. 
    Water evaporates from oceans, forms clouds, and falls as rain or snow.
    This cycle repeats endlessly.
    
    Part D: Essay
    
    Write a paragraph about your favorite book.
    
    My favorite book is "Harry Potter and the Sorcerer's Stone" by J.K. Rowling.
    This magical story follows Harry, an orphan who discovers he is a wizard.
    The book teaches valuable lessons about friendship, courage, and standing up
    for what is right. I love how the author creates a detailed magical world
    that feels both fantastical and real. The characters are memorable and
    their development throughout the series is excellent.
    """


@pytest.fixture
def sample_template():
    """Sample grading template for testing."""
    return {
        "id": "test-template-1",
        "name": "Standard English Test",
        "description": "Template for standard English assessments",
        "question_types": [
            {"type": "mcq", "name": "Multiple Choice", "weight": 20, "enabled": True},
            {"type": "true_false", "name": "True/False", "weight": 10, "enabled": True},
            {
                "type": "short_answer",
                "name": "Short Answer",
                "weight": 30,
                "enabled": True,
            },
            {"type": "essay", "name": "Essay", "weight": 40, "enabled": True},
        ],
        "encouragement_words": [
            "Bravo!",
            "Excellent!",
            "Perfect!",
            "Outstanding!",
            "Well done!",
        ],
        "is_default": False,
    }
