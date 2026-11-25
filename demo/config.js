window.DEMO = {
  repo: "pdf-table-extractor",
  title: "pdf-table-extractor",
  tagline: "Drop in a PDF with tables. Get every table as its own sheet, with tables that span pages joined, and a review list of tables whose Total row does not match the column sum.",
  pkg: "pdf_table_extractor",
  packages: ["openpyxl", "pdfminer.six", "pillow"],
  pip_nodeps: ["pdfplumber"],
  inputs: [
    { id: "pdf", label: "PDF with tables", accept: ".pdf", sample: "samples/doc_002_space_multipage.pdf" },
  ],
  options: [],
  sampleNote: 'The sample is <a href="samples/doc_002_space_multipage.pdf">doc_002_space_multipage.pdf</a>: a synthetic two-page table with no ruling lines and a Total row that is planted to be wrong, so it goes to review. Another sample, <a href="samples/doc_004_two_tables.pdf">doc_004_two_tables.pdf</a>, has two tables on one page.<br>pdfplumber runs here without pypdfium2 (it has no WebAssembly build and is only used to render page images, which this tool does not need).',
  python: `
from pathlib import Path
from pdf_table_extractor.cli import main as cli_main

def run(paths, opts):
    src = paths["pdf"][0]
    out = "/work/" + Path(src).stem + "-tables.xlsx"
    code, log = run_cli(cli_main, ["extract", src, "-o", out])  # exit 1 means a table was flagged
    if code not in (0, 1) or not Path(out).exists():
        return {"ok": False, "log": log, "sheets": [], "download": None}
    sheets = sheets_from_xlsx(out)
    sheets.sort(key=lambda s: s["name"] == "Review")
    return {"ok": True, "log": log, "sheets": sheets, "download": out}
`,
};
