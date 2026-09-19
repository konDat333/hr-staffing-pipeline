# HR staffing pipeline

Loads the HR Excel exports from `../data` into DuckDB and builds the
`project_staffing` model with dbt.

```
data/*.xlsx  --main.py-->  raw.*  --dbt-->  staging -> intermediate -> marts.project_staffing
             (pandera)     (DuckDB)         (views)    (ephemeral)     (table)
```

## Run with Docker

From the repository root:

```bash
docker compose up --build
```

This builds one image (Python 3.14 + uv + dbt-duckdb), loads the Excel files
and runs `dbt build` (models + tests). The container exits when done; a
non-zero exit code means the load was rejected or a dbt test failed.

* `./data` is mounted read-only - replace the files there to load other data.
* `./project/warehouse/warehouse.duckdb` is written to the host, so loads
  accumulate between runs and the file can be inspected locally.

Pass loader options after the service name:

```bash
docker compose run --rm pipeline --max-invalid-share 0.5
```

Inspect the result without leaving Docker:

```bash
docker compose run --rm --entrypoint "uv run show_db.py" pipeline marts.project_staffing
```

## Run locally with uv

```bash
cd project
./run_pipeline.sh                       # = uv run main.py && (cd dbt && uv run dbt build)
uv run main.py --data-dir <folder>      # load another folder with the same two files
uv run show_db.py                       # tables, row counts, batches
uv run show_db.py marts.project_staffing
uv run show_db.py raw.employees --all   # every batch
uv run show_db.py --sql "select ..."    # ad-hoc query
```

dbt commands run from `project/dbt` (`uv run dbt build`, `uv run dbt test`,
`uv run dbt docs generate`); `profiles.yml` lives there and points at the
same DuckDB file via `DUCKDB_PATH`.

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

## Transformation (dbt)

| layer | models | materialisation | what happens |
|---|---|---|---|
| staging | `stg_employees`, `stg_assignments` | view | latest raw batch, renames, casts, value normalisation (`status`/roles lower-cased, `Y/Yes/N/No` -> `is_billable`) |
| intermediate | `int_project_assignments`, `int_project_leads` | ephemeral | assignments joined to employees (`is_active`, `employee_name`); active leads ranked per project |
| marts | `project_staffing` | table | one row per project: lead, active team size, active weekly hours |

Business rules and how the sample data exercises them:

* **Only active employees** count towards `team_size` / `total_weekly_hours`.
* **Projects with no active team stay in the output** (PROJ-2024-006: lead
  and contributor both inactive -> 0 / 0).
* **Project lead** = active employee assigned with role `lead`. Two active
  leads (PROJ-2024-004): the billable one is preferred, then more weekly
  hours, then the earliest assignment; `active_lead_count` shows there were
  two. No active lead (PROJ-2024-006, -007): null.
* **Email** (PII) is not selected beyond raw; duplicates are tested on the
  source among active employees.

Tests (`dbt build` runs them in dependency order; an `error` stops
downstream models, a `warn` does not):

| test | severity | why |
|---|---|---|
| `unique` / `not_null` on keys, `accepted_values` on categorical codes | error | basic integrity of every layer |
| `relationships` assignments -> employees, manager -> employees | error | catches assignments to unknown or quarantined people |
| one assignment per employee and project; one name per project code | error | double-counted people / split projects |
| mart hours reconcile with active assignment hours | error | detects join fan-out or dropped rows |
| `team_size = 0` iff `total_weekly_hours = 0` | error | internal consistency of the mart |
| project without an active lead; more than one active lead | warn | real in the sample data, reported not hidden |
| assignment above 40 h/week; employee above 40 h/week in total | warn | plausible but worth a look |

## Fixtures

* `data/*_dirty.xlsx` - one or two row-level errors (< 10%): the load
  succeeds and the rows land in quarantine.
* `data/*_invalid.xlsx` - one error per rule (~25%): trips the circuit
  breaker. They also contain relational errors (duplicate ids, unknown
  manager, two names for one project code) that are left for dbt tests.

Copy a pair into a folder under the original file names and run
`uv run main.py --data-dir <folder>`.
