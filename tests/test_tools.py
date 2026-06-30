"""Tests for core tool functionality (RAG and code checker)."""

import tempfile
from pathlib import Path

import pytest

from src.code_checker import CodeChecker
from src.rag import RAGSystem


@pytest.fixture
def temp_rag_dirs():
    """Create temporary directories for RAG testing."""
    with tempfile.TemporaryDirectory() as tmp:
        docs_dir = Path(tmp) / "course_docs"
        chroma_dir = Path(tmp) / "chroma_db"
        docs_dir.mkdir()
        chroma_dir.mkdir()
        (docs_dir / "functions.txt").write_text(
            "Python functions use the def keyword to define reusable blocks of code. "
            "Functions can take parameters and return values using the return statement.",
            encoding="utf-8",
        )
        yield docs_dir, chroma_dir


@pytest.fixture
def rag_system(temp_rag_dirs):
    """RAG instance using ephemeral Chroma (avoids Windows file locks)."""
    docs_dir, chroma_dir = temp_rag_dirs
    rag = RAGSystem(course_docs_dir=docs_dir, chroma_db_dir=chroma_dir, ephemeral=True)
    yield rag
    rag.close()


def test_code_checker_valid_syntax():
    """Valid Python code should pass syntax check."""
    checker = CodeChecker()
    code = "def add(a, b):\n    return a + b\n"
    passed, error = checker.check_syntax(code)
    assert passed is True
    assert error == ""


def test_code_checker_invalid_syntax():
    """Invalid Python code should fail with an error message."""
    checker = CodeChecker()
    code = "def broken(\n    return 1\n"
    passed, error = checker.check_syntax(code)
    assert passed is False
    assert "SyntaxError" in error


def test_rag_retrieve_returns_relevant_context(rag_system):
    """RAG system should retrieve context related to the query."""
    rag = rag_system

    context = rag.retrieve("What is a Python function?", top_k=1)
    assert context
    assert "def" in context.lower() or "function" in context.lower()

    scored = rag.retrieve_with_scores("Python return statement", top_k=1)
    assert len(scored) >= 1
    text, score = scored[0]
    assert text
    assert isinstance(score, float)
