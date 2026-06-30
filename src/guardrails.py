"""Input/output guardrails for safe tutoring interactions."""

import re

JAILBREAK_PHRASES = [
    "ignore previous instructions",
    "ignore all previous instructions",
    "disregard previous instructions",
    "you are now dan",
    "forget your prompts",
    "forget your instructions",
    "bypass your rules",
    "act as dan",
    "jailbreak",
    "do anything now",
]

UNSAFE_MESSAGE = (
    "Your message was blocked because it appears to attempt bypassing safety guidelines. "
    "Please ask a genuine programming question."
)


def filter_input(user_input: str) -> tuple[bool, str]:
    """
    Check user input for jailbreak attempts.

    Returns:
        (is_safe, message) — message is empty when safe, otherwise explains the block.
    """
    if not user_input or not user_input.strip():
        return False, "Please enter a message."

    normalized = user_input.lower().strip()
    for phrase in JAILBREAK_PHRASES:
        if phrase in normalized:
            return False, UNSAFE_MESSAGE

    return True, ""


def filter_output_for_attempt(output: str, attempt_count: int) -> str:
    """
    Filter tutor output based on attempt count.

    On attempts 0 and 1, remove code solutions (fenced blocks and obvious code lines).
    On attempt 2+, return the original output.
    """
    if attempt_count >= 2:
        return output

    if not output:
        return output

    # Remove fenced code blocks (``` ... ```)
    filtered = re.sub(r"```[\s\S]*?```", "[Code hidden — try solving it yourself first!]", output)

    # Remove inline backtick code that looks like a full solution
    filtered = re.sub(
        r"`(?:def |class |import |for |while |return )[^`]+`",
        "[hint hidden]",
        filtered,
    )

    return filtered.strip()
