from collections.abc import Callable
from pathlib import Path

import pytest

from benchmark.generate import TruthTable, make_doc

MakePdf = Callable[[str, int], tuple[Path, list[TruthTable]]]


@pytest.fixture
def make_pdf(tmp_path: Path) -> MakePdf:
    def _make(layout: str, seed: int = 1) -> tuple[Path, list[TruthTable]]:
        path = tmp_path / f"{layout}_{seed}.pdf"
        return path, make_doc(path, layout, seed)

    return _make
