from subprocess import CalledProcessError

from tech_debt._stateless_computations.format_search_error import format_search_error


def test_format_search_error_preserves_codex_stderr(subtests):
    cases = {
        "text": ("Model is unavailable.\n", "Model is unavailable."),
        "bytes": (b"Authentication failed.\n", "Authentication failed."),
        "invalid_utf8": (b"Error: \xff", "Error: \ufffd"),
        "missing": (None, ""),
        "empty": ("", ""),
        "whitespace": (" \n", ""),
    }
    for name, (stderr, detail) in cases.items():
        with subtests.test(msg=name):
            error = CalledProcessError(1, ["codex", "exec"], stderr=stderr)

            result = format_search_error(error)

            expected = "Codex exited with code 1."
            if detail:
                expected += f"\n{detail}"
            assert result == expected


def test_format_search_error_flattens_nested_groups():
    error = ExceptionGroup(
        "Search sessions failed",
        [
            CalledProcessError(2, ["codex", "exec"], stderr="Unknown model"),
            ExceptionGroup(
                "Other sessions",
                [ValueError("Invalid response"), OSError("Cannot read response")],
            ),
        ],
    )

    result = format_search_error(error)

    assert result == (
        "Codex exited with code 2.\nUnknown model\n\n"
        "Invalid response\n\nCannot read response"
    )


def test_format_search_error_handles_regular_errors(subtests):
    cases = {
        "message": (RuntimeError("Search failed"), "Search failed"),
        "empty_message": (RuntimeError(), "RuntimeError"),
    }
    for name, (error, expected) in cases.items():
        with subtests.test(msg=name):
            assert format_search_error(error) == expected
