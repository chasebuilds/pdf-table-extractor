"""Find tables on a page: ruled tables from drawn lines, the rest from text alignment."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

CELL_GAP = 7.0  # a horizontal gap wider than this (points) starts a new cell
ROW_TOL = 2.0  # words whose tops differ by less than this share a row
ROW_BREAK = 20.0  # a vertical jump larger than this ends a whitespace table
MIN_ROWS = 3


@dataclass
class RawTable:
    """A table as found on one page, before header detection and stitching."""

    page: int
    top: float
    bottom: float
    bands: list[tuple[float, float]]  # (x0, x1) of each column
    rows: list[list[str]]
    kind: str  # "ruled" or "whitespace"
    conflicts: list[int] = field(default_factory=list)  # rows where two cells hit one column

    @property
    def ncols(self) -> int:
        return len(self.bands)


def _ruled(page: Any, page_no: int) -> list[RawTable]:
    out: list[RawTable] = []
    for t in page.find_tables({"vertical_strategy": "lines", "horizontal_strategy": "lines"}):
        rows = [[c or "" for c in r] for r in t.extract()]
        if len(rows) < 2 or max(len(r) for r in rows) < 2:
            continue
        first = next(r for r in t.rows if all(c is not None for c in r.cells))
        bands = [(c[0], c[2]) for c in first.cells]
        width = len(bands)
        rows = [(r + [""] * width)[:width] for r in rows]
        out.append(RawTable(page_no, t.bbox[1], t.bbox[3], bands, rows, "ruled"))
    return out


def _lines(words: list[dict[str, Any]]) -> list[tuple[float, list[tuple[float, float, str]]]]:
    """Group words into text lines, then words into cells by horizontal gap."""
    lines: list[tuple[float, list[dict[str, Any]]]] = []
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if lines and abs(w["top"] - lines[-1][0]) < ROW_TOL:
            lines[-1][1].append(w)
        else:
            lines.append((w["top"], [w]))
    result = []
    for top, ws in lines:
        cells: list[tuple[float, float, str]] = []
        for w in sorted(ws, key=lambda w: w["x0"]):
            if cells and w["x0"] - cells[-1][1] <= CELL_GAP:
                x0, _, text = cells[-1]
                cells[-1] = (x0, w["x1"], text + " " + w["text"])
            else:
                cells.append((w["x0"], w["x1"], w["text"]))
        result.append((top, cells))
    return result


def _bands(block: list[tuple[float, list[tuple[float, float, str]]]]) -> list[tuple[float, float]]:
    spans = sorted((x0, x1) for _, cells in block for x0, x1, _ in cells)
    bands: list[tuple[float, float]] = []
    for x0, x1 in spans:
        if bands and x0 <= bands[-1][1] + 1:
            bands[-1] = (bands[-1][0], max(bands[-1][1], x1))
        else:
            bands.append((x0, x1))
    return bands


def _whitespace(words: list[dict[str, Any]], page_no: int) -> list[RawTable]:
    lines = _lines(words)
    blocks: list[list[tuple[float, list[tuple[float, float, str]]]]] = []
    current: list[tuple[float, list[tuple[float, float, str]]]] = []
    for top, cells in lines:
        joins = current and top - current[-1][0] <= ROW_BREAK
        if len(cells) >= 2 and (joins or not current):
            current.append((top, cells))
            continue
        if len(current) >= MIN_ROWS:
            blocks.append(current)
        current = [(top, cells)] if len(cells) >= 2 else []
    if len(current) >= MIN_ROWS:
        blocks.append(current)

    out = []
    for block in blocks:
        bands = _bands(block)
        if len(bands) < 2:
            continue
        rows, conflicts = [], []
        for i, (_, cells) in enumerate(block):
            row = [""] * len(bands)
            for x0, x1, text in cells:
                j = next(k for k, (b0, b1) in enumerate(bands) if x0 >= b0 - 1 and x1 <= b1 + 1)
                if row[j]:
                    conflicts.append(i)
                    row[j] += " " + text
                else:
                    row[j] = text
            rows.append(row)
        out.append(
            RawTable(page_no, block[0][0], block[-1][0] + 10, bands, rows, "whitespace", conflicts)
        )
    return out


def find_tables(page: Any, page_no: int) -> list[RawTable]:
    """Every table on a pdfplumber page, top to bottom."""
    ruled = _ruled(page, page_no)

    def outside(w: dict[str, Any]) -> bool:
        return not any(t.top - 2 <= w["top"] <= t.bottom + 2 for t in ruled)

    words = [w for w in page.extract_words() if outside(w)]
    return sorted(ruled + _whitespace(words, page_no), key=lambda t: t.top)
