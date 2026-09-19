# Single image for the whole pipeline: Python loader + dbt on DuckDB.
# DuckDB runs in-process, so no database service is needed.

FROM python:3.14-slim

# uv from its official image, pinned
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    DBT_SEND_ANONYMOUS_USAGE_STATS=0 \
    DBT_PROFILES_DIR=/app/project/dbt \
    DUCKDB_PATH=/app/project/warehouse/warehouse.duckdb

WORKDIR /app/project

# Dependencies first so this layer is cached while the code changes
COPY project/pyproject.toml project/uv.lock ./
RUN uv sync --locked --no-dev

# Application code and the default source data (data/ is usually
# bind-mounted over at run time, see docker-compose.yml)
COPY project/ /app/project/
COPY data/ /app/data/

RUN chmod +x run_pipeline.sh

ENTRYPOINT ["./run_pipeline.sh"]
