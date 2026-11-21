import pytest

from benchmark.generate import LAYOUTS
from pdf_table_extractor.detect import RawTable
from pdf_table_extractor.extract import build_table, extract_pdf, stitch
from tests.conftest import MakePdf


def _raw(rows: list[list[str]], page: int = 1, bands: list[tuple[float, float]] | None = None,
         conflicts: list[int] | None = None) -> RawTable:
    bands = bands or [(10.0 * i, 10.0 * i + 8) for i in range(len(rows[0]))]
    return RawTable(page, 100, 500, bands, rows, "whitespace", conflicts or [])


@pytest.mark.parametrize("layout", LAYOUTS)
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_matches_truth(make_pdf: MakePdf, layout: str, seed: int) -> None:
    path, truth = make_pdf(layout, seed)
    got = extract_pdf(path)
    assert len(got) == len(truth)
    for t, g in zip(truth, got, strict=True):
        assert g.header == t.header
        assert g.pages == t.pages
        assert g.rows == t.rows
        assert g.ok == (not t.planted)


def test_header_and_numbers() -> None:
    t = build_table([_raw([["Item", "Amount"], ["Tea", "$1,200.00"], ["Cake", "(3.50)"],
                           ["Total", "1,196.50"]])], "x.pdf")
    assert t.header == ["Item", "Amount"]
    assert t.rows == [["Tea", 1200.0], ["Cake", -3.5], ["Total", 1196.5]]
    assert t.ok and t.total_checked


def test_no_header_when_first_row_has_numbers() -> None:
    t = build_table([_raw([["Tea", "5"], ["Cake", "6"], ["Pie", "7"]])], "x.pdf")
    assert t.header is None
    assert len(t.rows) == 3


def test_total_mismatch_flagged() -> None:
    t = build_table([_raw([["Item", "Qty"], ["a", "1"], ["b", "2"], ["Total", "4"]])], "x.pdf")
    assert not t.ok
    assert t.problems[0].startswith("total: column 'Qty'")


def test_bad_number_flagged_and_total_skipped() -> None:
    rows = [["Item", "Qty"], ["a", "1"], ["b", "2O"], ["c", "3"], ["Total", "6"]]
    t = build_table([_raw(rows)], "x.pdf")
    assert len(t.problems) == 1
    assert "'2O'" in t.problems[0]


def test_column_conflict_flagged() -> None:
    t = build_table([_raw([["A", "B"], ["x", "1"], ["y", "2"]], conflicts=[1])], "x.pdf")
    assert t.problems == ["column count: 1 row(s) had two values in one column"]


def test_stitch_on_repeated_header() -> None:
    a = _raw([["Item", "Qty"], ["a", "1"], ["b", "2"]], page=1)
    b = _raw([["Item", "Qty"], ["c", "3"]], page=2, bands=[(50, 60), (70, 80)])
    groups = stitch([[a], [b]])
    assert len(groups) == 1
    t = build_table(groups[0], "x.pdf")
    assert t.rows == [["a", 1], ["b", 2], ["c", 3]]
    assert t.pages == [1, 2]


def test_stitch_on_aligned_columns() -> None:
    a = _raw([["Item", "Qty"], ["a", "1"]], page=1)
    b = _raw([["c", "3"], ["d", "4"]], page=2)
    assert len(stitch([[a], [b]])) == 1


def test_no_stitch_after_total_or_misaligned() -> None:
    a = _raw([["Item", "Qty"], ["a", "1"], ["Total", "1"]], page=1)
    b = _raw([["c", "3"], ["d", "4"]], page=2)
    assert len(stitch([[a], [b]])) == 2
    c = _raw([["Item", "Qty"], ["a", "1"]], page=1)
    d = _raw([["c", "3"], ["d", "4"]], page=2, bands=[(50, 60), (70, 80)])
    assert len(stitch([[c], [d]])) == 2
    assert len(stitch([[c], [], [d]])) == 2
