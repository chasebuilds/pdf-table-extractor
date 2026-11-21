"""Write tables to one Excel workbook (a sheet per table plus Review) or to CSV files."""

from __future__ import annotations

import csv
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from .extract import Table

REVIEW_COLUMNS = ["Table", "Sheet", "Source", "Pages", "Rows", "Columns", "Header", "Status",
                  "Reasons"]
_FLAG = PatternFill("solid", fgColor="FFF2CC")


def _pages(t: Table) -> str:
    return str(t.pages[0]) if len(t.pages) == 1 else f"{t.pages[0]}-{t.pages[-1]}"


def write_xlsx(tables: list[Table], path: str | Path) -> None:
    wb = Workbook()
    review = wb.active
    review.title = "Review"
    review.append(REVIEW_COLUMNS)
    for c in review[1]:
        c.font = Font(bold=True)
    for n, t in enumerate(tables, 1):
        name = f"Table {n}"
        review.append([n, name, t.source, _pages(t), len(t.rows), t.ncols,
                       "yes" if t.header else "no", "OK" if t.ok else "REVIEW",
                       "; ".join(t.problems)])
        if not t.ok:
            for c in review[review.max_row]:
                c.fill = _FLAG
        ws = wb.create_sheet(name)
        if t.header:
            ws.append(t.header)
            for c in ws[1]:
                c.font = Font(bold=True)
            ws.freeze_panes = "A2"
        for row in t.rows:
            ws.append(row)
        for col in ws.iter_cols(min_row=2 if t.header else 1):
            for c in col:
                if isinstance(c.value, float):
                    c.number_format = "#,##0.00"
    review.column_dimensions["I"].width = 80
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def write_csvs(tables: list[Table], folder: str | Path, stem: str) -> list[Path]:
    out_dir = Path(folder)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for n, t in enumerate(tables, 1):
        p = out_dir / f"{stem}_table_{n}.csv"
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if t.header:
                w.writerow(t.header)
            w.writerows(["" if v is None else v for v in r] for r in t.rows)
        paths.append(p)
    return paths
