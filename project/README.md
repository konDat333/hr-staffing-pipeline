# HR staffing pipeline

Loads the HR Excel exports from `../data` into DuckDB (`raw` schema), from
where dbt builds the `project_staffing` model.

## Run

```bash
uv run main.py                          # load ../data into warehouse.duckdb
uv run main.py --data-dir <folder>      # load another folder with the same two files
uv run show_db.py                       # tables, row counts, batches
uv run show_db.py raw.employees         # latest batch of a table (--all for history)
uv run show_db.py --sql "select ..."    # ad-hoc query
```

## Loading (Python)

`pipeline/excel.py` reads each export, finds the header row (the exports
carry report metadata above it) and renames columns to snake_case.

`pipeline/schemas.py` holds pandera **row-level** contracts: id formats,
allowed values, ranges, dates, and within-row consistency (an Inactive
employee must have a termination date, and it must be after the hire date).

### Validation strategy: quarantine, not fail-fast

A single bad row should not block a whole load - stale data is usually
worse for analytics than data with a known gap. So:

* rows that pass go to `raw.<table>`, typed;
* rows that fail go to `raw.<table>_quarantine` as text, with an `_errors`
  column naming every violated check;
* if quarantined rows exceed `--max-invalid-share` (default 10%, env
  `MAX_INVALID_SHARE`) in any source, or a source has no valid rows, the run
  aborts and **nothing** is written - that many failures means the source is
  broken, not dirty.

Both sources are validated before anything is written, so a batch is
all-or-nothing.

Only checks that can be decided on one row live in pandera. Relational
rules - unique ids, `reports_to` pointing to an existing employee, one
project code having one name, an assignment's employee existing in HR -
are dbt tests on the staging models. Splitting them this way means
quarantining a row can never cause another row to fail.

**Downstream effect:** a quarantined employee is missing from
`stg_employees`, so their assignments will fail the dbt `relationships`
test. That is intended: quarantine turns a hard pipeline failure into a
visible data-quality signal, it does not hide the problem.

### Raw layer: every load is kept

Each run appends *all* valid rows of every source with one shared
`_loaded_at` timestamp (same for both tables and their quarantines). Raw is
therefore an immutable history of what the HR system exported; dbt staging
selects the latest batch. Changes and deletions between exports are
reflected, and older snapshots stay queryable
(`where _loaded_at = ...`). Re-running on the same files adds an identical
batch - harmless, the latest one wins.

## Fixtures

* `data/*_dirty.xlsx` - one or two row-level errors (< 10%): the load
  succeeds and the rows land in quarantine.
* `data/*_invalid.xlsx` - one error per rule (~25%): trips the circuit
  breaker. They also contain relational errors (duplicate ids, unknown
  manager, two names for one project code) that are left for dbt tests.

Copy a pair into a folder under the original file names and run
`uv run main.py --data-dir <folder>`.
