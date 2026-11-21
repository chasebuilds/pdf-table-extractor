# Benchmark

Written by `python -m benchmark.run_benchmark --count 200 --seed 1`. Do not edit by hand.

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

| Measure | Count | Rate |
|---|---:|---:|
| Cells extracted exactly (header + body) | 38,528 / 38,968 | **98.9%** |
| Tables found | 240 / 240 | **100.0%** |
| Headers detected | 240 / 240 | **100.0%** |
| Multi-page tables stitched into one | 79 / 80 | **98.8%** |
| Planted wrong Total rows flagged | 52 / 53 | **98.1%** |
| Planted unparseable numbers flagged | 44 / 44 | **100.0%** |
| Clean tables flagged by mistake | 0 / 143 | **0.0%** |

200 PDFs, 332 pages, 240 tables. Extraction time: 11.9 s total, 36 ms per page.

## By layout

| Layout | Cells | Exact |
|---|---:|---:|
| ruled_single | 2,269 | 100.0% |
| space_single | 2,357 | 100.0% |
| space_multipage | 16,109 | 97.3% |
| ruled_multipage | 15,020 | 100.0% |
| two_tables | 3,213 | 100.0% |

## What this does not show

These PDFs are generated, clean and regular: one font, known gutters, no merged cells, no
scans, no rotated pages, no wrapped text inside a cell. Real statements and reports are
messier, and the numbers above are an upper bound for them. See [LIMITATIONS.md](LIMITATIONS.md).
