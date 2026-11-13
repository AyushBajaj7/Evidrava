"""Read the supported template without calculating or changing the workbook."""
from datetime import date, datetime
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

from openpyxl import load_workbook


def serial(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def load_registry(path):
    path = Path(path)
    blob = path.read_bytes()
    if len(blob) > 20_000_000:
        raise ValueError("Workbook exceeds the 20 MB pilot limit")
    with ZipFile(BytesIO(blob)) as archive:
        if len(archive.infolist()) > 1000 or sum(x.file_size for x in archive.infolist()) > 100_000_000:
            raise ValueError("Workbook exceeds the pilot archive limits")
    contract = json.loads(Path(__file__).with_name("workbook_contract.json").read_text(encoding="utf-8"))
    workbook = load_workbook(BytesIO(blob), data_only=False, keep_links=False)
    diagnostics = []

    def issue(code, sheet, cell, message):
        diagnostics.append(dict(severity="error", code=code, sheet=sheet, cell=cell, message=message))

    missing = set(contract["sheets"]) - set(workbook.sheetnames)
    if missing:
        raise ValueError("Unsupported workbook: missing sheets " + ", ".join(sorted(missing)))
    if str(workbook["Meta"]["C4"].value) != "3.3":
        issue("SCHEMA_VERSION", "Meta", "C4", "Only workbook schema 3.3 is supported")
    for sheet, expected in contract["headers"].items():
        actual = [workbook[sheet].cell(4, i + 1).value for i in range(len(expected))]
        if actual != expected or any(c.value is not None for c in workbook[sheet][4][len(expected):]):
            issue("HEADER_MISMATCH", sheet, "A4", "Header positions differ from the supported v3.3 template")
    for sheet, expected in contract["formulas"].items():
        ws = workbook[sheet]
        if ws.max_row > 50_000 or ws.max_column > 100:
            raise ValueError(f"{sheet} exceeds supported pilot dimensions")
        formulas = {c.coordinate: c.value for row in ws for c in row if c.data_type == "f"}
        digest = sha256(json.dumps(formulas, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        if len(formulas) != expected["count"] or digest != expected["sha256"]:
            issue("FORMULA_CHANGED", sheet, "A1", "Formula fingerprint differs from the accepted v3.3 template; restore or explicitly review this workbook revision")
    tables = {}
    for sheet, layout in contract["tables"].items():
        ws = workbook[sheet]
        if ws.max_row > 50_000 or ws.max_column > 100:
            raise ValueError(f"{sheet} exceeds supported pilot dimensions")
        for col, expected in layout["example"].items():
            if serial(ws[f"{col}5"].value) != expected:
                issue("EXAMPLE_ROW_CHANGED", sheet, f"{col}5", "Row 5 is a reserved example; enter study data from row 6")
        tables[sheet] = []
        for row in range(6, ws.max_row + 1):
            values = {col: ws[f"{col}{row}"].value for col in layout["input_columns"]}
            if not any(value is not None and value != "" for value in values.values()):
                continue
            if row > layout["last_row"]:
                issue("INPUT_OVERFLOW", sheet, f"A{row}", "Populated input lies beyond the template formula range")
            for col, value in values.items():
                if ws[f"{col}{row}"].data_type == "f":
                    issue("FORMULA_IN_INPUT", sheet, f"{col}{row}", "Input must be a literal value, not a formula")
            tables[sheet].append({"row": row, "values": values})
    rules = {f"B{i}": workbook["Rules"][f"B{i}"].value for i in [5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]}
    for coord, value in rules.items():
        if workbook["Rules"][coord].data_type == "f":
            issue("FORMULA_IN_INPUT", "Rules", coord, "Configuration must be a literal value")
    result = {"tables": tables, "rules": rules, "snapshot_date": workbook["Snapshot"]["B3"].value,
              "gate_inputs": {"leak_test": workbook["Gates"]["C29"].value,
                              "baselines": workbook["Gates"]["C30"].value},
              "loader_diagnostics": diagnostics, "workbook_sha256": sha256(blob).hexdigest(),
              "contract_sha256": sha256(Path(__file__).with_name("workbook_contract.json").read_bytes()).hexdigest(),
              "source_name": path.name}
    workbook.close()
    return result
