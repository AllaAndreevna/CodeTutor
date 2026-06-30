"""Code validation utilities for student submissions."""

import ast


class CodeChecker:
    """Checks student Python code for syntax errors."""

    def check_syntax(self, code: str) -> tuple[bool, str]:
        """
        Compile Python code and report syntax errors.

        Returns:
            (passed, error_message) — error_message is empty when passed is True.
        """
        if not code or not code.strip():
            return False, "No code provided."

        try:
            compile(code, "<student_code>", "exec")
            ast.parse(code)
            return True, ""
        except SyntaxError as exc:
            line = exc.lineno or "?"
            msg = exc.msg or str(exc)
            return False, f"SyntaxError on line {line}: {msg}"
        except Exception as exc:
            return False, f"Error: {exc}"
