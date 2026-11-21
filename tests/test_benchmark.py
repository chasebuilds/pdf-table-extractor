from pathlib import Path

from benchmark.run_benchmark import run, same, summary


def test_same() -> None:
    assert same(1.0, 1.004)
    assert not same(1.0, 1.01)
    assert same("a", "a")
    assert not same("1", 1)


def test_small_run(tmp_path: Path) -> None:
    s = run(5, 3, tmp_path)
    assert s.docs == 5
    assert s.truth_tables == 6
    assert s.cells_right == s.cells
    assert s.stitched == s.multipage == 2
    assert s.false_flags == 0
    assert "| Measure |" in summary(s)
