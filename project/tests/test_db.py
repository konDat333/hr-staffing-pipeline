from datetime import datetime, timedelta, timezone

import duckdb
import pytest

from pipeline.db import connect, count_rows, latest_batch, write_table


@pytest.fixture
def con(tmp_path):
    with connect(tmp_path / "t.duckdb") as c:
        yield c


def test_first_write_creates_table_and_returns_count(con, employees_df):
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)

    assert write_table(con, employees_df, "employees", loaded_at=ts) == 3
    assert count_rows(con, "employees") == 3
    assert con.execute("select distinct _loaded_at from raw.employees").fetchall() == [(ts,)]


def test_second_write_appends_a_new_batch(con, employees_df):
    first = datetime(2026, 1, 1, tzinfo=timezone.utc)
    second = first + timedelta(days=1)

    write_table(con, employees_df, "employees", loaded_at=first)
    write_table(con, employees_df, "employees", loaded_at=second)

    assert count_rows(con, "employees") == 6
    assert latest_batch(con, "employees") == second
    assert con.execute("select count(distinct _loaded_at) from raw.employees").fetchone()[0] == 2


def test_input_frame_is_not_mutated(con, employees_df):
    write_table(con, employees_df, "employees", loaded_at=datetime.now(timezone.utc))

    assert "_loaded_at" not in employees_df.columns


@pytest.mark.parametrize("table", ["raw; drop table x", "with space", "1abc"])
def test_invalid_identifier_is_rejected_before_touching_the_db(con, employees_df, table):
    with pytest.raises(ValueError):
        write_table(con, employees_df, table, loaded_at=datetime.now(timezone.utc))

    assert con.execute("select count(*) from information_schema.tables where table_schema = 'raw'").fetchone()[0] == 0


def test_connect_creates_parent_directory(tmp_path):
    path = tmp_path / "nested" / "dir" / "w.duckdb"

    with connect(path):
        pass

    assert path.exists()
