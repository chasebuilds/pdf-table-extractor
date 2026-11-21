"""From raw page tables to clean, checked tables: header, stitching, numbers, checks."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber

from .detect import RawTable, find_tables
from .numbers import Cell, clean_cell, parse_number

ALIGN_TOL = 3.0
NUMERIC_SHARE = 0.6
_TOTAL = re.compile(r"^(grand\s+)?total\b", re.IGNORECASE)


@dataclass
class Table:
    """One finished table: optional header, cleaned rows, and the result of its checks."""

    source: str
    pages: list[int]
    kind: str
    header: list[str] | None
    rows: list[list[Cell]]
    problems: list[str] = field(default_factory=list)
    total_checked: bool = False

    @property
    def ok(self) -> bool:
        return not self.problems

    @property
    def ncols(self) -> int:
        return len(self.rows[0]) if self.rows else len(self.header or [])


def _norm(row: list[str]) -> list[str]:
    return [" ".join(c.split()) for c in row]


def _aligned(a: RawTable, b: RawTable) -> bool:
    return a.ncols == b.ncols and all(
        abs(x0 - y0) <= ALIGN_TOL or abs(x1 - y1) <= ALIGN_TOL
        for (x0, x1), (y0, y1) in zip(a.bands, b.bands, strict=True)
    )


def _is_total(row: list[str]) -> bool:
    first = next((c for c in row if c.strip()), "")
    return bool(_TOTAL.match(first.strip()))


def stitch(pages: list[list[RawTable]]) -> list[list[RawTable]]:
    """Group page tables into logical tables.

    The first table on a page continues the last table on the previous page when the
    column count matches, the earlier part has no Total row, and either its header row
    repeats or its columns line up.
    """
    groups: list[list[RawTable]] = []
    for p, tables in enumerate(pages):
        for i, t in enumerate(tables):
            prev = groups[-1] if groups else None
            continues = (
                prev is not None
                and i == 0
                and p > 0
                and bool(pages[p - 1])
                and prev[-1] is pages[p - 1][-1]
                and prev[-1].ncols == t.ncols
                and not _is_total(prev[-1].rows[-1])
                and (_norm(t.rows[0]) == _norm(prev[0].rows[0]) or _aligned(prev[-1], t))
            )
            if continues and prev is not None:
                prev.append(t)
            else:
                groups.append([t])
    return groups


def _looks_like_header(row: list[str], rest: list[list[str]]) -> bool:
    filled = [c for c in row if c.strip()]
    if len(filled) < 2 or any(parse_number(c) is not None for c in filled):
        return False
    return any(parse_number(c) is not None for r in rest for c in r if c.strip())


def build_table(parts: list[RawTable], source: str) -> Table:
    """Merge the parts, find the header, clean cells and run the checks."""
    first = parts[0].rows
    header = _norm(first[0]) if _looks_like_header(first[0], first[1:]) else None
    raw: list[list[str]] = []
    conflicts = 0
    for k, part in enumerate(parts):
        rows = part.rows
        if header is not None and (k == 0 or _norm(rows[0]) == header):
            rows = rows[1:]
        raw.extend(rows)
        conflicts += len(part.conflicts)
    table = Table(
        source,
        sorted({p.page for p in parts}),
        parts[0].kind,
        header,
        [[clean_cell(c) for c in r] for r in raw],
    )
    if conflicts:
        table.problems.append(f"column count: {conflicts} row(s) had two values in one column")
    _check(table, raw)
    return table


def _check(table: Table, raw: list[list[str]]) -> None:
    total_idx = max((i for i, r in enumerate(raw) if _is_total(r)), default=None)
    data = [r for i, r in enumerate(table.rows) if i != total_idx]
    names = table.header or [f"Column {j + 1}" for j in range(table.ncols)]
    bad_cols: set[int] = set()
    for j in range(table.ncols):
        values = [r[j] for r in data if r[j] is not None]
        nums = [v for v in values if isinstance(v, int | float)]
        if not values or len(nums) / len(values) < NUMERIC_SHARE or len(nums) == len(values):
            continue
        bad = [v for v in values if not isinstance(v, int | float)]
        bad_cols.add(j)
        shown = ", ".join(repr(v) for v in bad[:3])
        table.problems.append(
            f"numbers: column '{names[j]}' has {len(bad)} value(s) that do not parse: {shown}"
        )
    if total_idx is None:
        return
    table.total_checked = True
    total_row = table.rows[total_idx]
    body = table.rows[:total_idx]
    for j, total in enumerate(total_row):
        if not isinstance(total, int | float) or j in bad_cols:
            continue
        col = [float(v) for r in body if isinstance(v := r[j], int | float)]
        if not col:
            continue
        s = sum(col)
        if abs(s - total) > 0.005 + 1e-9 * abs(s):
            table.problems.append(
                f"total: column '{names[j]}' Total row says {total:,.2f}, column sums to {s:,.2f}"
            )


def extract_pdf(path: str | Path) -> list[Table]:
    """Every table in a PDF, stitched across pages and checked."""
    path = Path(path)
    with pdfplumber.open(path) as pdf:
        pages = [find_tables(page, n + 1) for n, page in enumerate(pdf.pages)]
    return [build_table(g, path.name) for g in stitch(pages)]
