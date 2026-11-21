import pytest

from pdf_table_extractor.numbers import clean_cell, parse_number


@pytest.mark.parametrize(
    ("text", "want"),
    [
        ("1,234.50", 1234.5),
        ("$1,234.50", 1234.5),
        ("(1,234.50)", -1234.5),
        ("($12.00)", -12.0),
        ("-7", -7),
        ("−7.25", -7.25),
        ("12", 12),
        ("0", 0),
        ("0.75", 0.75),
        ("£3", 3),
    ],
)
def test_parses(text: str, want: float) -> None:
    got = parse_number(text)
    assert got == want
    assert type(got) is type(want)


@pytest.mark.parametrize(
    "text", ["", "abc", "1,23", "12.5O", "(12", "12)", "007", "2026-01-05", "INV-1234", "--5"]
)
def test_rejects(text: str) -> None:
    assert parse_number(text) is None


def test_clean_cell() -> None:
    assert clean_cell(None) is None
    assert clean_cell("   ") is None
    assert clean_cell(" Office   supplies ") == "Office supplies"
    assert clean_cell("(5.00)") == -5.0
