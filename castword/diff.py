"""
Word-level diff between original and rewritten text.
"""

import difflib
import re


def word_diff(original: str, rewritten: str) -> list[tuple[str, str]]:
    """
    Compute a word-level diff between two strings.

    Returns a list of (token, tag) pairs where tag is one of:
      "equal"   — unchanged word or whitespace
      "added"   — word present in rewritten but not original
      "removed" — word present in original but not rewritten

    Whitespace between words is included as "equal" tokens so the
    result can be inserted into a GtkTextBuffer verbatim.
    """
    # Tokenise: split on whitespace boundaries, keeping the separators
    orig_tokens = _tokenise(original)
    new_tokens = _tokenise(rewritten)

    matcher = difflib.SequenceMatcher(None, orig_tokens, new_tokens, autojunk=False)
    result: list[tuple[str, str]] = []

    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            for tok in orig_tokens[i1:i2]:
                result.append((tok, "equal"))
        elif op == "insert":
            for tok in new_tokens[j1:j2]:
                result.append((tok, "added"))
        elif op == "delete":
            for tok in orig_tokens[i1:i2]:
                result.append((tok, "removed"))
        elif op == "replace":
            for tok in orig_tokens[i1:i2]:
                result.append((tok, "removed"))
            for tok in new_tokens[j1:j2]:
                result.append((tok, "added"))

    return result


def _tokenise(text: str) -> list[str]:
    """Split text into alternating word / whitespace tokens."""
    return re.split(r"(\s+)", text)
