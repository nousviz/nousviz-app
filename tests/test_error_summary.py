"""B313 (v0.10.4): tests for extract_error_summary().

Covers:
- John's actual prod stderr (collapsed-to-one-line, head-chopped)
- Multi-line tracebacks (the normal case)
- Chained tracebacks ('During handling of the above exception')
- Plain non-traceback messages
- Edge cases (empty, None, garbage)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def test_johns_actual_collapsed_stderr():
    """The exact text the user pasted from /system/logs. Single-line,
    head-chopped 'Traceback' → 'st recent call last)', traceback frames
    inlined with no newlines. The summary must still be clean."""
    from apps.api.src.services.error_summary import extract_error_summary

    raw = (
        "st recent call last): File \"/opt/nousviz/plugins/installed/"
        "google-analytics/src/google_analytics_sync.py\", line 331, in "
        "<module> GoogleAnalyticsSync().main() File \"/opt/nousviz/sdk/"
        "nousviz_sdk/sync.py\", line 282, in main self.run(since=since) "
        "File \"/opt/nousviz/plugins/installed/google-analytics/src/"
        "google_analytics_sync.py\", line 111, in run raise RuntimeError"
        "( RuntimeError: No GA4 property selected. Pick one from the "
        "dropdown on the Settings tab after connecting with Google."
    )
    result = extract_error_summary(raw)
    assert result["summary"] == (
        "RuntimeError: No GA4 property selected. Pick one from the "
        "dropdown on the Settings tab after connecting with Google."
    )
    assert result["details"] == raw.strip()


def test_normal_multiline_traceback():
    """Standard Python traceback with newlines preserved."""
    from apps.api.src.services.error_summary import extract_error_summary

    raw = (
        "Traceback (most recent call last):\n"
        '  File "/opt/nousviz/sdk/nousviz_sdk/sync.py", line 282, in main\n'
        "    self.run(since=since)\n"
        '  File "/opt/nousviz/plugins/installed/x/src/sync.py", line 50, in run\n'
        "    raise ValueError(\"bad config\")\n"
        "ValueError: bad config"
    )
    result = extract_error_summary(raw)
    assert result["summary"] == "ValueError: bad config"
    assert result["details"] is not None


def test_chained_traceback_picks_innermost():
    """`During handling of the above exception, another exception
    occurred` — the LAST exception is the one the operator sees."""
    from apps.api.src.services.error_summary import extract_error_summary

    raw = (
        "Traceback (most recent call last):\n"
        '  File "x.py", line 1, in <module>\n'
        '    raise KeyError("first")\n'
        "KeyError: 'first'\n"
        "\n"
        "During handling of the above exception, another exception occurred:\n"
        "\n"
        "Traceback (most recent call last):\n"
        '  File "x.py", line 3, in <module>\n'
        '    raise RuntimeError("actual issue user should see")\n'
        "RuntimeError: actual issue user should see"
    )
    result = extract_error_summary(raw)
    assert result["summary"] == "RuntimeError: actual issue user should see"


def test_plain_short_message_passes_through():
    """A short, non-traceback string is its own summary."""
    from apps.api.src.services.error_summary import extract_error_summary

    result = extract_error_summary("Connection refused.")
    assert result["summary"] == "Connection refused."
    assert result["details"] is None


def test_empty_and_none_inputs():
    from apps.api.src.services.error_summary import extract_error_summary

    assert extract_error_summary(None) == {"summary": None, "details": None}
    assert extract_error_summary("") == {"summary": None, "details": ""}
    assert extract_error_summary("   ") == {"summary": None, "details": None}


def test_garbage_long_text_with_no_traceback():
    """A long string with no exception pattern keeps details, no summary."""
    from apps.api.src.services.error_summary import extract_error_summary

    raw = "log line 1\nlog line 2\n" * 50
    result = extract_error_summary(raw)
    assert result["summary"] is None
    assert result["details"] is not None
    assert "log line 1" in result["details"]


def test_custom_dotted_exception_class():
    """Plugin-defined exception with dotted path is recognised."""
    from apps.api.src.services.error_summary import extract_error_summary

    raw = (
        "Traceback (most recent call last):\n"
        '  File "x.py", line 1, in <module>\n'
        "my_plugin.errors.SetupRequiredError: user must do X"
    )
    result = extract_error_summary(raw)
    assert result["summary"] == "my_plugin.errors.SetupRequiredError: user must do X"


def test_keyboard_interrupt_is_recognised():
    from apps.api.src.services.error_summary import extract_error_summary

    raw = "Traceback (most recent call last):\n  ...\nKeyboardInterrupt: user cancelled"
    result = extract_error_summary(raw)
    assert result["summary"] == "KeyboardInterrupt: user cancelled"


def test_summary_is_capped_at_400_chars():
    """A pathologically long exception message gets clipped with an
    ellipsis so it can't blow up the surface."""
    from apps.api.src.services.error_summary import extract_error_summary

    long_msg = "x" * 1000
    raw = f"RuntimeError: {long_msg}"
    result = extract_error_summary(raw)
    assert len(result["summary"]) == 400
    assert result["summary"].endswith("...")
    # Details preserves the original.
    assert result["details"] == raw.strip()


def test_internal_whitespace_collapsed():
    """A message containing weird whitespace runs (newlines, tabs) gets
    normalised to single spaces in the summary. Details retains original."""
    from apps.api.src.services.error_summary import extract_error_summary

    raw = "ValueError: line one\n\tline two\n  line three"
    result = extract_error_summary(raw)
    # Note: only the first part of the message after the lookahead boundary
    # is captured if a traceback marker follows. With no traceback follow,
    # everything is the message and gets collapsed.
    assert "line one" in result["summary"]
    # No literal newlines or tabs in the summary.
    assert "\n" not in result["summary"]
    assert "\t" not in result["summary"]


def test_head_chopped_traceback_still_works():
    """Tail-truncated stderr that lost 'Traceback (most recent call last)'
    — common when stderr[-500:] eats the prefix."""
    from apps.api.src.services.error_summary import extract_error_summary

    raw = (
        '_call_last): File "x.py", line 5, in foo\n'
        '    raise PermissionError("denied")\n'
        "PermissionError: denied"
    )
    result = extract_error_summary(raw)
    assert result["summary"] == "PermissionError: denied"
