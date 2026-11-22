"""Tests for CodeTutor agent behavior."""

from unittest.mock import MagicMock, patch

import pytest

from src.agents import CodeTutorAgents


@pytest.fixture
def mock_rag():
    """Provide a mock RAG system."""
    rag = MagicMock()
    rag.retrieve.return_value = "Functions are defined with the def keyword."
    return rag


@pytest.fixture
def agents(mock_rag):
    """Provide agents with mocked RAG."""
    return CodeTutorAgents(mock_rag)


def test_checker_agent_passes_valid_code(agents):
    """Checker agent should mark valid code as passed."""
    state = {
        "user_code": "def greet():\n    return 'hi'\n",
        "exercise_description": "Write a greet function",
        "attempt_count": 0,
        "test_passed": False,
        "rag_context": "",
        "hint": "",
    }
    result = agents.checker_agent(state)
    assert result["test_passed"] is True
    assert "no syntax errors" in result["hint"].lower()


def test_checker_agent_fails_invalid_code(agents):
    """Checker agent should report syntax errors."""
    state = {
        "user_code": "def broken(\n",
        "exercise_description": "Write a function",
        "attempt_count": 0,
        "test_passed": False,
        "rag_context": "",
        "hint": "",
    }
    result = agents.checker_agent(state)
    assert result["test_passed"] is False
    assert "syntax error" in result["hint"].lower()


@patch.object(CodeTutorAgents, "_call_ollama")
def test_tutor_agent_increments_attempt(mock_ollama, agents, mock_rag):
    """Tutor agent should increment attempt_count and use RAG context."""
    mock_ollama.return_value = "What should your function return?"
    state = {
        "user_code": "def f():\n    pass\n",
        "exercise_description": "Write a function",
        "attempt_count": 0,
        "test_passed": False,
        "rag_context": "",
        "hint": "",
    }
    result = agents.tutor_agent(state)
    assert result["attempt_count"] == 1
    assert result["rag_context"]
    assert result["hint"]
    mock_rag.retrieve.assert_called_once()


@patch("src.agents.check_ollama_status")
@patch("src.agents.ollama_generate")
def test_theory_agent_uses_rag_and_ollama(mock_generate, mock_status, agents, mock_rag):
    """Theory agent should retrieve context and return an answer."""
    from src.ollama_client import OllamaStatus

    mock_status.return_value = OllamaStatus(
        available=True, base_url="http://127.0.0.1:11434", model="test", message="ok"
    )
    mock_generate.return_value = "A function is a reusable block of code."
    answer = agents.theory_agent("What is a function?")
    assert "function" in answer.lower()
    mock_rag.retrieve.assert_called_once_with("What is a function?", top_k=3, source=None)
    mock_generate.assert_called_once()
