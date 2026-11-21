"""pdftables extract IN [-o OUT] [--csv-dir DIR]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .export import write_csvs, write_xlsx
from .extract import Table, extract_pdf


def _inputs(src: Path) -> list[Path]:
    if src.is_dir():
        return sorted(p for p in src.iterdir() if p.suffix.lower() == ".pdf")
    return [src]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pdftables", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("extract", help="extract tables from a PDF or a folder of PDFs")
    ex.add_argument("input", type=Path, help="a PDF file or a folder of PDFs")
    ex.add_argument("-o", "--out", type=Path,
                    help="workbook path (folder input: folder for one workbook per PDF)")
    ex.add_argument("--csv-dir", type=Path, help="also write one CSV per table here")
    args = ap.parse_args(argv)

    files = _inputs(args.input)
    if not files or not all(f.is_file() for f in files):
        print(f"error: no PDF found at {args.input}", file=sys.stderr)
        return 2
    folder_mode = args.input.is_dir()
    flagged = 0
    for f in files:
        try:
            tables: list[Table] = extract_pdf(f)
        except Exception as e:  # pdfminer raises many types for broken files
            print(f"error: {f}: {e}", file=sys.stderr)
            return 2
        if folder_mode:
            out = (args.out or Path("pdftables-out")) / f"{f.stem}.xlsx"
        else:
            out = args.out or f.with_suffix(".xlsx")
        write_xlsx(tables, out)
        if args.csv_dir:
            write_csvs(tables, args.csv_dir, f.stem)
        for n, t in enumerate(tables, 1):
            status = "OK    " if t.ok else "REVIEW"
            pages = ",".join(map(str, t.pages))
            print(f"{status} {f.name} table {n}: {len(t.rows)} rows x {t.ncols} cols, "
                  f"page {pages}")
            for p in t.problems:
                print(f"         {p}")
        bad = sum(not t.ok for t in tables)
        flagged += bad
        print(f"{f.name}: {len(tables)} table(s), {bad} flagged -> {out}")
    return 1 if flagged else 0


if __name__ == "__main__":
    raise SystemExit(main())
