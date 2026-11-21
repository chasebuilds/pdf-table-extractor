# Limitations

What this tool does not do, or does badly. Read this before using it on files that matter.

## Input

- **Digital PDFs only.** It reads the text layer. A scanned page has no text layer, so it has no tables. There is no OCR.
- **Rotated pages and right-to-left text** are not handled.
- **Encrypted PDFs** fail with exit code 2.

## Finding tables

- **A whitespace table needs at least three lines** with two or more cells each. A short table (header and one row) is missed. The same rule causes the one benchmark miss: when the last page of a long table holds only the repeated header and the Total row, that part is dropped, so the Total row is lost and the total check never runs.
- **Cells are split on gaps wider than 7 points.** Text with wide letter spacing, or columns closer than that, will be split or merged wrongly.
- **Lines with two or more spaced-out parts next to a table** (for example `Invoice: 123      Date: 2026-01-05` right above it) can be taken as table rows.
- **Ruled tables need full grid lines.** A table with only horizontal rules is read as a whitespace table, which usually works.

## Headers and cells

- **One header row.** A header split over two lines becomes a header plus a first row of text.
- **No merged cells.** A cell spanning two columns joins the columns, and the table is flagged under "column count".
- **No wrapped cells.** Text that wraps inside a cell becomes an extra row.
- **A header made of numbers** (for example years `2024 2025`) is not recognised as a header.

## Stitching

- A table on the next page is joined when the column count matches and the header repeats or the columns line up. **Two separate tables with the same layout on consecutive pages will be joined** unless the first one ends with a Total row.
- Only the first table on a page can continue the last table on the previous page.

## Numbers

- **Formats read:** `1,234.50`, `-1,234.50`, `(1,234.50)`, `$1,234.50`, `($1,234.50)`, `£` and `€`. Not read: European `1.234,50`, trailing minus `1,234.50-`, `CR`/`DR` suffixes, percentages, currency codes like `USD 12`. These stay text, and if most of a column is numbers they are flagged.
- **Codes with a leading zero** (`007`) stay text on purpose.

## Checks

- A pass means the table is internally consistent, not that it is right. A wrong value that still parses and still adds up passes.
- **Total check** looks only at the last row starting with `Total` or `Grand total`, and sums every number above it. Subtotal rows inside the table are added in too, which makes a correct Total look wrong.

## Benchmark

The benchmark files are generated: one font, regular gutters, no merged or wrapped cells, no noise. Real documents are messier, so treat the measured numbers as an upper bound.
