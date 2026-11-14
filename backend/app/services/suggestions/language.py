"""Text helpers for deciding whether a question really mentions a column."""

import re

_WORD = re.compile(r"[a-z0-9]+")
_SIMILARITY_LIMIT = 0.7
_MAX_FILLER_WORDS = 2  # a question that only adds this many words is a rewording


def words(text: str) -> frozenset[str]:
    """Lowercase word set with a naive plural strip (`orders` -> `order`)."""
    return frozenset(w[:-1] if len(w) > 3 and w.endswith("s") else w for w in _WORD.findall(text.lower()))


def humanize(name: str) -> str:
    """`order_date` -> `order date`."""
    return name.replace("_", " ").strip().lower()


def mentions(question: str, column: str) -> bool:
    """True when every word of the column name appears in the question."""
    needed = words(humanize(column))
    return bool(needed) and needed <= words(question)


def similar(a: str, b: str) -> bool:
    """Near-duplicate test: high word overlap, or one question is the other plus filler."""
    left, right = words(a), words(b)
    if not left or not right:
        return False
    shorter, longer = sorted((left, right), key=len)
    if shorter <= longer and len(longer - shorter) <= _MAX_FILLER_WORDS:
        return True
    return len(left & right) / len(left | right) >= _SIMILARITY_LIMIT
