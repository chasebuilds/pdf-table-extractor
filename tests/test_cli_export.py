import csv
from pathlib import Path

import pytest
from openpyxl import load_workbook

from pdf_table_extractor.cli import main
from tests.conftest import MakePdf


def test_extract_to_xlsx_and_csv(make_pdf: MakePdf, tmp_path: Path,
                                 capsys: pytest.CaptureFixture[str]) -> None:
    path, truth = make_pdf("two_tables", 4)
    out = tmp_path / "out.xlsx"
    code = main(["extract", str(path), "-o", str(out), "--csv-dir", str(tmp_path / "csv")])
    assert code == (1 if any(t.planted for t in truth) else 0)
    wb = load_workbook(out)
    assert wb.sheetnames == ["Review", "Table 1", "Table 2"]
    ws = wb["Table 1"]
    assert [c.value for c in ws[1]] == truth[0].header
    assert [c.value for c in ws[2]] == truth[0].rows[0]
    review = [[c.value for c in r] for r in wb["Review"].iter_rows(min_row=2)]
    assert [r[7] for r in review] == ["REVIEW" if t.planted else "OK" for t in truth]
    with (tmp_path / "csv" / f"{path.stem}_table_2.csv").open(encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0] == truth[1].header
    assert len(rows) == len(truth[1].rows) + 1
    assert "table(s)" in capsys.readouterr().out


def test_flagged_table_on_review_sheet(make_pdf: MakePdf, tmp_path: Path) -> None:
    for seed in range(1, 40):
        path, truth = make_pdf("space_single", seed)
        if "wrong_total" in truth[0].planted:
            break
    else:
        pytest.fail("no wrong_total seed found")
    out = tmp_path / "flag.xlsx"
    assert main(["extract", str(path), "-o", str(out)]) == 1
    row = [c.value for c in load_workbook(out)["Review"][2]]
    assert row[7] == "REVIEW"
    assert str(row[8]).startswith("total: column")


def test_folder_input(make_pdf: MakePdf, tmp_path: Path) -> None:
    make_pdf("ruled_single", 1)
    make_pdf("ruled_multipage", 3)
    out = tmp_path / "books"
    main(["extract", str(tmp_path), "-o", str(out)])
    assert sorted(p.name for p in out.iterdir()) == [
        "ruled_multipage_3.xlsx", "ruled_single_1.xlsx"]


def test_missing_input(tmp_path: Path) -> None:
    assert main(["extract", str(tmp_path / "nope.pdf")]) == 2
