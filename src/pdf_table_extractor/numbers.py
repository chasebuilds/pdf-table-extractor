"""Turn printed numbers ("$1,234.50", "(12.00)", "-7") into int or float."""

from __future__ import annotations

import re

_NUM = re.compile(
    r"^(?P<open>\()?(?P<sign>[-+])?(?P<cur>[$€£])?\s*(?P<sign2>[-+])?"
    r"(?P<int>\d{1,3}(?:,\d{3})+|\d+)(?P<dec>\.\d+)?(?P<close>\))?$"
)

Cell = str | int | float | None


def parse_number(text: str) -> int | float | None:
    """Return the number in `text`, or None when it is not a plain printed number.

    Accepts thousands separators, a currency sign, a leading minus and parentheses
    for negatives. Codes with a leading zero ("007") stay text.
    """
    s = text.strip().replace("−", "-").replace(" ", "")
    m = _NUM.match(s)
    if not m or bool(m["open"]) != bool(m["close"]):
        return None
    if m["sign"] and m["sign2"]:
        return None
    digits = m["int"].replace(",", "")
    if len(digits) > 1 and digits.startswith("0") and not m["dec"]:
        return None
    negative = bool(m["open"]) or "-" in (m["sign"] or "", m["sign2"] or "")
    value: int | float = float(digits + m["dec"]) if m["dec"] else int(digits)
    return -value if negative else value


def clean_cell(text: str | None) -> Cell:
    """Collapse whitespace; return a number when the text is one, None when empty."""
    if text is None:
        return None
    s = " ".join(text.split())
    if not s:
        return None
    num = parse_number(s)
    return s if num is None else num
