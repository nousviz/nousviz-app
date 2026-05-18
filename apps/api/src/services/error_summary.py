"""B313 (v0.10.4): pull a clean, operator-actionable headline out of a
Python traceback string.

Background
----------
Plugin sync scripts that raise ``RuntimeError("No GA4 property selected.
Pick one from the dropdown on the Settings tab after connecting with
Google.")`` produce a useful, actionable message. The worker stores the
**tail** of stderr verbatim, which on the surfaces shows up as::

    st recent call last): File "/opt/nousviz/plugins/installed/google-
    analytics/src/google_analytics_sync.py", line 331, in <module>
    GoogleAnalyticsSync().main() ... RuntimeError: No GA4 property
    selected. Pick one from the dropdown on the Settings tab...

That's:

* head-chopped (``Traceback (most recent call last)`` → ``st recent
  call last)``) because the tail truncation discards the leading bytes;
* visually dominated by the traceback chrome the operator can't act on;
* repeating the actual message twice — once raw, once inside the
  traceback — because the SDK formats both into the ``error`` column.

This module extracts the operator-actionable headline (the last
``ExceptionType: message`` line in the traceback) and returns both that
headline and the raw text, so surfaces can show "headline up front,
details on disclosure".

No plugin-author contract change — every existing plugin raising a
plain ``RuntimeError`` (or any standard exception) now surfaces a clean
message in both ``/system/logs`` and the plugin's Settings card.
"""

from __future__ import annotations

import re
from typing import Optional, TypedDict


# Match `FooError: some message` or `foo.bar.BazError: ...`.
# Accepts dotted module paths (custom plugin exceptions), three suffix
# families that cover Python's stdlib + typical user code, and captures
# the message up to the next traceback-frame token or end-of-string.
#
# Why the suffix anchor? Without it, "File:" or "Note:" inside the
# traceback would match. Pinning to ``Error|Exception|Warning|Interrupt``
# keeps the false-positive rate near zero while covering
# RuntimeError, ValueError, KeyError, PermissionError, KeyboardInterrupt,
# DeprecationWarning, and any custom *Error / *Exception class.
_EXC_RE = re.compile(
    r"""
    (?P<type>
        (?:[a-z_][A-Za-z0-9_]*\.)*   # optional lowercase package prefix
                                     # (e.g. ``my_plugin.errors.``)
        [A-Z][A-Za-z0-9_]*           # ClassName body
        (?:Error|Exception|Warning|Interrupt)   # required suffix
    )
    :\s
    (?P<msg>.+?)
    (?=
        (?:\n\s*\n)                  # blank line — next chained traceback
        | (?:\s+Traceback\s)         # explicit chain marker
        | (?:\s+File\s")             # next stack frame (multi-line)
        | \Z                         # end of string
    )
    """,
    re.VERBOSE | re.DOTALL,
)


class ErrorSummary(TypedDict, total=False):
    """Shape returned by :func:`extract_error_summary`.

    ``summary`` is the short, actionable headline (e.g. ``"RuntimeError: No
    GA4 property selected..."``). ``details`` is the raw stderr text the
    surface can render on disclosure. Either may be ``None``.
    """
    summary: Optional[str]
    details: Optional[str]


def extract_error_summary(text: Optional[str]) -> ErrorSummary:
    """Pull the last ``ExceptionType: message`` line out of a traceback.

    Returns a mapping with ``summary`` (clean headline or ``None`` if the
    input doesn't look like a traceback) and ``details`` (the raw input
    for disclosure UIs). The original text is preserved verbatim — this
    helper is read-only.

    Robust to:

    * single-line collapsed tracebacks (the surface or wire format ate
      the newlines)
    * head-chopped tracebacks (``stderr[-500:]`` lost the leading
      ``Traceback (most recent call last):`` prefix)
    * chained tracebacks (``During handling of the above exception...``)
      — the LAST match wins, which is the exception the operator
      ultimately sees
    * dotted custom exception names (``my_plugin.errors.SetupRequired``)

    Anything that doesn't look like a Python traceback is returned with
    ``summary=None`` so the caller can fall back to its previous render
    path.
    """
    if not text or not isinstance(text, str):
        return {"summary": None, "details": text}

    stripped = text.strip()
    if not stripped:
        return {"summary": None, "details": None}

    matches = list(_EXC_RE.finditer(stripped))
    if not matches:
        # No traceback pattern at all. If the text is a short single-line
        # message, treat it as its own summary; otherwise hand the raw
        # text back as details only.
        if len(stripped) <= 200 and "\n" not in stripped:
            return {"summary": stripped, "details": None}
        return {"summary": None, "details": stripped}

    last = matches[-1]
    exc_type = last.group("type")
    raw_msg = last.group("msg").strip()

    # Collapse internal whitespace runs to single spaces — the wire
    # format sometimes preserves indentation from the traceback frame
    # AFTER the message, which we want to discard.
    msg = re.sub(r"\s+", " ", raw_msg).strip()

    # Trim trailing traceback artefacts that survive the boundary
    # lookahead (e.g. the message ends with ``...`` followed by a frame
    # marker that the regex didn't catch in this specific layout).
    msg = re.sub(r"\s*Traceback\s+.*$", "", msg, flags=re.IGNORECASE)
    msg = re.sub(r"\s*File\s+\".*$", "", msg)

    summary = f"{exc_type}: {msg}".strip()
    # Hard cap — surfaces will clip with ellipsis if needed, but a 4kb
    # "summary" defeats the purpose.
    if len(summary) > 400:
        summary = summary[:397] + "..."

    return {"summary": summary, "details": stripped}
