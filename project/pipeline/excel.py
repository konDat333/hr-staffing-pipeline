"""Reading HR-system Excel exports into normalised pandas DataFrames.

Both source files share the same layout: a few report-metadata rows
(title, generation date, blank line) followed by the real header row and
the data. The header row position is not hardcoded - it is detected by
looking for the row that contains all expected source columns.
"""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


class ExcelLayoutError(ValueError):
    """Raised when a source file does not have the expected structure."""


@dataclass(frozen=True)
class ExcelSource:
    """Describes one Excel export: where it lives and how its columns map.

    `columns` maps the header text as it appears in the file to the
    snake_case name used downstream. Every key must be present in the file.
    """

    path: Path
    columns: dict[str, str]
    sheet_name: str | int = 0
    max_header_scan_rows: int = 20

    @property
    def source_columns(self) -> list[str]:
        return list(self.columns)


def _find_header_row(raw: pd.DataFrame, expected: list[str], scan_rows: int) -> int:
    """Return the 0-based index of the first row containing all `expected` values."""
    expected_set = set(expected)
    for idx, row in raw.head(scan_rows).iterrows():
        cells = {str(v).strip() for v in row.dropna()}
        if expected_set <= cells:
            return int(idx)
    raise ExcelLayoutError(
        f"Header row with columns {expected} not found in first {scan_rows} rows"
    )


def read_excel_source(source: ExcelSource) -> pd.DataFrame:
    """Read one export, locate its header, keep and rename the expected columns."""
    if not source.path.is_file():
        raise FileNotFoundError(source.path)

    raw = pd.read_excel(source.path, sheet_name=source.sheet_name, header=None)
    header_idx = _find_header_row(raw, source.source_columns, source.max_header_scan_rows)

    df = pd.read_excel(source.path, sheet_name=source.sheet_name, header=header_idx)
    df.columns = [str(c).strip() for c in df.columns]

    df = df[source.source_columns].rename(columns=source.columns)
    # Drop fully empty rows (e.g. trailing footer whitespace in exports)
    df = df.dropna(how="all").reset_index(drop=True)

    # Normalise string cells: strip surrounding whitespace, blank -> NA
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].str.strip().replace("", pd.NA)

    return df
