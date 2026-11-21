"""Score extraction against the known truth of generated PDFs and write BENCHMARK.md.

    python -m benchmark.run_benchmark --count 200 --seed 1
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from benchmark.generate import LAYOUTS, TruthTable, generate
from pdf_table_extractor.extract import Table, extract_pdf

ROOT = Path(__file__).resolve().parent.parent


def same(a: Any, b: Any) -> bool:
    if isinstance(a, int | float) and isinstance(b, int | float):
        return abs(a - b) < 0.005
    return bool(a == b)


@dataclass
class Score:
    docs: int = 0
    pages: int = 0
    seconds: float = 0.0
    truth_tables: int = 0
    found_tables: int = 0
    docs_exact_count: int = 0
    cells: int = 0
    cells_right: int = 0
    headers_right: int = 0
    multipage: int = 0
    stitched: int = 0
    planted: Counter[str] = field(default_factory=Counter)
    caught: Counter[str] = field(default_factory=Counter)
    clean: int = 0
    false_flags: int = 0
    by_layout: dict[str, list[int]] = field(default_factory=dict)  # cells, right


def score_doc(s: Score, layout: str, truth: list[TruthTable], got: list[Table]) -> None:
    s.truth_tables += len(truth)
    s.found_tables += len(got)
    s.docs_exact_count += len(truth) == len(got)
    lay = s.by_layout.setdefault(layout, [0, 0])
    for i, t in enumerate(truth):
        g = got[i] if i < len(got) else None
        cells = [*t.header, *(v for r in t.rows for v in r)]
        right = 0
        if g is not None:
            g_cells = [*(g.header or []), *(v for r in g.rows for v in r)]
            if len(g.rows) == len(t.rows) and (g.header or []) == t.header:
                right = sum(same(a, b) for a, b in zip(cells, g_cells, strict=True))
            s.headers_right += g.header == t.header
        s.cells += len(cells)
        s.cells_right += right
        lay[0] += len(cells)
        lay[1] += right
        if len(t.pages) > 1:
            s.multipage += 1
            s.stitched += g is not None and g.pages == t.pages and len(g.rows) == len(t.rows)
        if t.planted:
            for p in t.planted:
                s.planted[p] += 1
                tag = "total:" if p == "wrong_total" else "numbers:"
                s.caught[p] += g is not None and any(x.startswith(tag) for x in g.problems)
        else:
            s.clean += 1
            s.false_flags += g is not None and not g.ok


def run(count: int, seed: int, data: Path) -> Score:
    s = Score()
    for path in generate(data, count, seed):
        meta = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        truth = [TruthTable(**t) for t in meta["tables"]]
        t0 = time.perf_counter()
        got = extract_pdf(path)
        s.seconds += time.perf_counter() - t0
        s.docs += 1
        s.pages += max(p for t in truth for p in t.pages)
        score_doc(s, meta["layout"], truth, got)
    return s


def pct(a: int, b: int) -> str:
    return f"{100 * a / b:.1f}%" if b else "n/a"


def summary(s: Score) -> str:
    rows = [
        ("Cells extracted exactly (header + body)", f"{s.cells_right:,} / {s.cells:,}",
         pct(s.cells_right, s.cells)),
        ("Tables found", f"{s.found_tables} / {s.truth_tables}",
         pct(min(s.found_tables, s.truth_tables), s.truth_tables)),
        ("Headers detected", f"{s.headers_right} / {s.truth_tables}",
         pct(s.headers_right, s.truth_tables)),
        ("Multi-page tables stitched into one", f"{s.stitched} / {s.multipage}",
         pct(s.stitched, s.multipage)),
        ("Planted wrong Total rows flagged", f"{s.caught['wrong_total']} / "
         f"{s.planted['wrong_total']}", pct(s.caught["wrong_total"], s.planted["wrong_total"])),
        ("Planted unparseable numbers flagged", f"{s.caught['bad_number']} / "
         f"{s.planted['bad_number']}", pct(s.caught["bad_number"], s.planted["bad_number"])),
        ("Clean tables flagged by mistake", f"{s.false_flags} / {s.clean}",
         pct(s.false_flags, s.clean)),
    ]
    lines = ["| Measure | Count | Rate |", "|---|---:|---:|"]
    lines += [f"| {a} | {b} | **{c}** |" for a, b, c in rows]
    lines.append("")
    lines.append(f"{s.docs} PDFs, {s.pages} pages, {s.truth_tables} tables. Extraction time: "
                 f"{s.seconds:.1f} s total, {1000 * s.seconds / s.pages:.0f} ms per page.")
    return "\n".join(lines)


def write(s: Score, count: int, seed: int) -> None:
    by_layout = ["| Layout | Cells | Exact |", "|---|---:|---:|"]
    for lay in LAYOUTS:
        cells, right = s.by_layout.get(lay, [0, 0])
        by_layout.append(f"| {lay} | {cells:,} | {pct(right, cells)} |")
    body = f"""# Benchmark

Written by `python -m benchmark.run_benchmark --count {count} --seed {seed}`. Do not edit by hand.

## Method

`benchmark/generate.py` draws PDFs with reportlab from a seed, so the content of every
cell is known. Five layouts rotate: a ruled table, a whitespace-aligned table under a
paragraph of prose, a whitespace table across pages with the header repeated, a ruled table
across pages with no repeated header, and two tables on one page. Money columns use one of
three styles per file: `1,234.50` with a minus sign, `(1,234.50)` for negatives, or
`$1,234.50`. About 30% of tables with a Total row get a total changed by 10 to 500. About
a quarter of the rest get one number with a letter `O` in place of a digit.

Each PDF is run through `extract_pdf`, and tables are matched to the truth in reading order.
A cell counts as exact when the text matches, or the number matches to the cent. When a
table's row count or header is wrong, all of its cells count as wrong.

## Result

{summary(s)}

## By layout

{chr(10).join(by_layout)}

## What this does not show

These PDFs are generated, clean and regular: one font, known gutters, no merged cells, no
scans, no rotated pages, no wrapped text inside a cell. Real statements and reports are
messier, and the numbers above are an upper bound for them. See [LIMITATIONS.md](LIMITATIONS.md).
"""
    (ROOT / "BENCHMARK.md").write_text(body, encoding="utf-8")
    readme = ROOT / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        block = f"<!-- benchmark:start -->\n{summary(s)}\n<!-- benchmark:end -->"
        text = re.sub(r"<!-- benchmark:start -->.*<!-- benchmark:end -->", lambda _: block,
                      text, flags=re.S)
        readme.write_text(text, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--data", type=Path, default=ROOT / "benchmark" / "data")
    a = ap.parse_args()
    s = run(a.count, a.seed, a.data)
    write(s, a.count, a.seed)
    print(summary(s))


if __name__ == "__main__":
    main()
