"""Row-level validation with quarantine.

Instead of failing the whole load on the first bad row, rows that violate
the pandera contract are set aside into a quarantine frame (kept as text,
with the list of violated checks) and the remaining rows are validated
again to obtain properly typed data. The caller decides whether the share
of quarantined rows is acceptable.

Structural problems (missing or unexpected columns) cannot be attributed
to a row and still raise.
"""

from dataclasses import dataclass

import pandas as pd
import pandera.pandas as pa

ERRORS_COLUMN = "_errors"


class StructuralError(ValueError):
    """The frame does not match the schema at the column level."""


@dataclass(frozen=True)
class ValidationResult:
    valid: pd.DataFrame       # schema-typed rows that passed every check
    quarantine: pd.DataFrame  # failing rows as text + `_errors`

    @property
    def total(self) -> int:
        return len(self.valid) + len(self.quarantine)

    @property
    def invalid_share(self) -> float:
        return len(self.quarantine) / self.total if self.total else 0.0


def _describe_failures(cases: pd.DataFrame) -> pd.Series:
    """One human-readable error string per failing row index."""
    is_row_check = cases["schema_context"].eq("DataFrameSchema")
    column = cases["column"].fillna("?").astype(str)
    value = cases["failure_case"].fillna("<null>").astype(str)
    described = cases.assign(
        message=cases["check"].where(is_row_check, cases["check"] + ": " + column + "=" + value)
    )
    return (
        described.drop_duplicates(subset=["index", "message"])
        .groupby("index")["message"]
        .agg("; ".join)
    )


def validate(df: pd.DataFrame, schema: type[pa.DataFrameModel]) -> ValidationResult:
    """Split `df` into rows accepted by `schema` and rows to quarantine."""
    try:
        return ValidationResult(valid=schema.validate(df, lazy=True), quarantine=_empty_quarantine(df))
    except pa.errors.SchemaErrors as exc:
        cases = exc.failure_cases

    if cases["index"].isna().any():
        structural = cases[cases["index"].isna()]
        raise StructuralError(
            "; ".join(f"{r.check}: {r.column}" for r in structural.itertuples())
        )

    errors = _describe_failures(cases)
    bad_index = errors.index.astype(int)

    quarantine = df.loc[bad_index].astype("string")
    quarantine[ERRORS_COLUMN] = errors.values

    # Only row-level checks remain in the schema, so the survivors cannot
    # fail because of the rows we just removed.
    valid = schema.validate(df.drop(index=bad_index), lazy=True)
    return ValidationResult(valid=valid, quarantine=quarantine.reset_index(drop=True))


def _empty_quarantine(df: pd.DataFrame) -> pd.DataFrame:
    empty = df.iloc[0:0].astype("string")
    empty[ERRORS_COLUMN] = pd.Series(dtype="string")
    return empty
