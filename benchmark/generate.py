"""Seeded synthetic PDFs with known tables, for tests and the benchmark.

Five layouts: a ruled table, a whitespace table under prose, a whitespace table across
pages with the header repeated, a ruled table across pages with no repeated header, and
two tables on one page. Some tables get a planted problem: a Total row that does not
match the column, or a number with a letter in it. The truth goes to `<name>.json`.

    python -m benchmark.generate --out samples --count 5 --seed 7
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen.canvas import Canvas

TOP, BOTTOM, LEFT, ROW_H = 740.0, 60.0, 50.0, 14.0
LAYOUTS = ["ruled_single", "space_single", "space_multipage", "ruled_multipage", "two_tables"]
WORDS = ["office", "supplies", "freight", "consulting", "hosting", "travel", "licence",
         "repairs", "catering", "training", "printing", "postage", "cleaning", "insurance",
         "utilities", "marketing"]
PROSE = ("This statement lists the activity for the period. Amounts are shown in US dollars "
         "and negative values are credits. Contact the accounts team with any questions.")


@dataclass
class Col:
    name: str
    kind: str  # text, code, date, int, money
    width: float


@dataclass
class TruthTable:
    header: list[str]
    rows: list[list[Any]]
    pages: list[int] = field(default_factory=list)
    planted: list[str] = field(default_factory=list)


def _money(v: float, style: str) -> str:
    s = f"{abs(v):,.2f}"
    if style == "dollar":
        s = "$" + s
    if v >= 0:
        return s
    return f"({s})" if style in ("paren", "dollar") else "-" + s


def _make_rows(rng: random.Random, cols: list[Col], n: int, style: str,
               total: bool) -> tuple[list[list[Any]], list[list[str]]]:
    """Values and their printed text, with an optional Total row."""
    values: list[list[Any]] = []
    for i in range(n):
        row: list[Any] = []
        for c in cols:
            if c.kind == "text":
                row.append(" ".join(rng.sample(WORDS, rng.randint(1, 2))).capitalize())
            elif c.kind == "code":
                row.append(f"INV-{rng.randint(1000, 9999)}")
            elif c.kind == "date":
                row.append(f"2026-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}")
            elif c.kind == "int":
                row.append(rng.randint(1, 400))
            else:
                v = round(rng.uniform(5, 25000), 2)
                row.append(-v if rng.random() < 0.1 and i else v)
        values.append(row)
    if total:
        trow: list[Any] = []
        for j, c in enumerate(cols):
            if j == 0:
                trow.append("Total")
            elif c.kind == "money":
                trow.append(round(sum(r[j] for r in values), 2))
            elif c.kind == "int":
                trow.append(sum(r[j] for r in values))
            else:
                trow.append(None)
        values.append(trow)
    printed = [[_fmt(v, c, style) for v, c in zip(r, cols, strict=True)] for r in values]
    return values, printed


def _fmt(v: Any, c: Col, style: str) -> str:
    if v is None:
        return ""
    if c.kind == "money" and isinstance(v, float | int):
        return _money(float(v), style)
    if c.kind == "int" and isinstance(v, int):
        return f"{v:,}"
    return str(v)


class Writer:
    def __init__(self, path: Path) -> None:
        self.c = Canvas(str(path), pagesize=letter)
        self.page = 1
        self.y = TOP

    def new_page(self) -> None:
        self.c.setFont("Helvetica", 8)
        self.c.drawString(LEFT, 30, f"Page {self.page}")
        self.c.showPage()
        self.page += 1
        self.y = TOP

    def text(self, s: str, size: float = 9, bold: bool = False, gap: float = 6) -> None:
        self.c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        self.c.drawString(LEFT, self.y - size, s)
        self.y -= size + gap

    def prose(self, s: str) -> None:
        words, line = s.split(), ""
        for w in words:
            if len(line) + len(w) > 95:
                self.text(line, gap=3)
                line = ""
            line = (line + " " + w).strip()
        self.text(line, gap=3)
        self.y -= 12

    def _row(self, cols: list[Col], cells: list[str], bold: bool) -> None:
        self.c.setFont("Helvetica-Bold" if bold else "Helvetica", 9)
        x, base = LEFT, self.y - 10
        for c, s in zip(cols, cells, strict=True):
            if c.kind in ("int", "money"):
                self.c.drawRightString(x + c.width - 8, base, s)
            else:
                self.c.drawString(x + 4, base, s)
            x += c.width
        self.y -= ROW_H

    def table(self, cols: list[Col], printed: list[list[str]], ruled: bool,
              repeat_header: bool, title: str) -> list[int]:
        header = [c.name for c in cols]
        xs = [LEFT]
        for c in cols:
            xs.append(xs[-1] + c.width)
        pages = [self.page]
        ys = [self.y]
        self._row(cols, header, True)
        ys.append(self.y)
        for cells in printed:
            if self.y - ROW_H < BOTTOM:
                if ruled:
                    self.c.grid(xs, ys)
                self.new_page()
                pages.append(self.page)
                self.text(f"{title} (continued)", size=11, bold=True, gap=14)
                ys = [self.y]
                if repeat_header:
                    self._row(cols, header, True)
                    ys.append(self.y)
            self._row(cols, cells, cells[0] == "Total")
            ys.append(self.y)
        if ruled:
            self.c.grid(xs, ys)
        self.y -= 24
        return pages

    def save(self) -> None:
        self.c.setFont("Helvetica", 8)
        self.c.drawString(LEFT, 30, f"Page {self.page}")
        self.c.save()


def _columns(rng: random.Random) -> list[Col]:
    options = [
        [Col("Description", "text", 170), Col("Qty", "int", 60), Col("Unit price", "money", 90),
         Col("Amount", "money", 100)],
        [Col("Date", "date", 80), Col("Invoice", "code", 80), Col("Description", "text", 160),
         Col("Debit", "money", 90), Col("Credit", "money", 90)],
        [Col("Item", "text", 180), Col("Units", "int", 70), Col("Revenue", "money", 110)],
    ]
    return rng.choice(options)


def _plant(rng: random.Random, t: TruthTable, cols: list[Col], printed: list[list[str]],
           has_total: bool) -> None:
    money = [j for j, c in enumerate(cols) if c.kind == "money"]
    if has_total and rng.random() < 0.3:
        j = rng.choice(money)
        delta = round(rng.uniform(10, 500), 2) * rng.choice([-1, 1])
        t.rows[-1][j] = round(t.rows[-1][j] + delta, 2)
        style = "paren" if "(" in "".join(r[j] for r in printed) else "plain"
        if any(r[j].startswith("$") or r[j].startswith("($") for r in printed):
            style = "dollar"
        printed[-1][j] = _money(t.rows[-1][j], style)
        t.planted.append("wrong_total")
    elif rng.random() < 0.25:
        i = rng.randrange(len(t.rows) - (2 if has_total else 1))
        j = rng.choice(money)
        s = printed[i][j]
        k = max(n for n, ch in enumerate(s) if ch.isdigit())
        printed[i][j] = s[:k] + "O" + s[k + 1:]
        t.rows[i][j] = printed[i][j]
        t.planted.append("bad_number")


def make_doc(path: Path, layout: str, seed: int) -> list[TruthTable]:
    rng = random.Random(seed)
    style = rng.choice(["plain", "paren", "dollar"])
    w = Writer(path)
    w.text("Account statement", size=14, bold=True, gap=10)
    specs: list[tuple[int, bool, bool, bool]] = {  # rows, ruled, repeat header, total
        "ruled_single": [(rng.randint(6, 18), True, False, True)],
        "space_single": [(rng.randint(6, 18), False, False, True)],
        "space_multipage": [(rng.randint(60, 120), False, True, True)],
        "ruled_multipage": [(rng.randint(60, 120), True, False, True)],
        "two_tables": [(rng.randint(5, 12), False, False, True),
                       (rng.randint(5, 12), False, False, False)],
    }[layout]
    if layout != "ruled_single":
        w.prose(PROSE)
    out = []
    for n, (nrows, ruled, repeat, total) in enumerate(specs):
        cols = _columns(rng)
        values, printed = _make_rows(rng, cols, nrows, style, total)
        t = TruthTable([c.name for c in cols], values)
        _plant(rng, t, cols, printed, total)
        title = f"Schedule {n + 1}"
        w.text(title, size=11, bold=True, gap=10)
        t.pages = w.table(cols, printed, ruled, repeat, title)
        out.append(t)
    w.save()
    path.with_suffix(".json").write_text(
        json.dumps({"layout": layout, "seed": seed, "tables": [t.__dict__ for t in out]},
                   indent=1), encoding="utf-8")
    return out


def generate(out: Path, count: int, seed: int) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(count):
        layout = LAYOUTS[i % len(LAYOUTS)]
        p = out / f"doc_{i:03d}_{layout}.pdf"
        make_doc(p, layout, seed * 10_000 + i)
        paths.append(p)
    return paths


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("benchmark/data"))
    ap.add_argument("--count", type=int, default=100)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    print(f"wrote {len(generate(a.out, a.count, a.seed))} PDFs to {a.out}")


if __name__ == "__main__":
    main()
