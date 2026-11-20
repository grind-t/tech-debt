from subprocess import CalledProcessError


def format_search_error(error: BaseException) -> str:
    """Describe search failures, preserving Codex stderr and grouped causes."""
    if isinstance(error, BaseExceptionGroup):
        return "\n\n".join(format_search_error(cause) for cause in error.exceptions)
    if isinstance(error, CalledProcessError):
        message = f"Codex exited with code {error.returncode}."
        detail = error.stderr
        if isinstance(detail, bytes):
            detail = detail.decode("utf-8", errors="replace")
        if detail and detail.strip():
            return f"{message}\n{detail.strip()}"
        return message
    return str(error).strip() or type(error).__name__
