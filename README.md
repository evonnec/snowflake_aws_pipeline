# Snowflake to S3 transfer

A command-line pipeline that reads a table from Snowflake, adds a monthly total for one numeric column, and uploads the result to an S3 bucket as JSON. It is built for handing a customer's data to an external stakeholder in an aggregated, cleaned form.

## What it does

For a given table, a date column and a numeric column, the pipeline:

1. Reads the whole table from Snowflake into a pandas DataFrame.
2. Asks Snowflake for `SUM(<sum column>)` grouped by the month and year of the date column.
3. Joins that monthly total onto every row of its month, as a new `SUM(<sum column>)` column. All original columns are kept unaggregated.
4. Drops fully blank rows.
5. Serializes the result to JSON records in memory and uploads it to S3 as `<TABLE>_<uuid>_<YYYYmmdd-HHMMSS>.json`.
6. Returns, and logs, a result summary:

```json
{
  "file_name": "ORDERS_100K_0193f3c2…_20230629-150002.json",
  "row_count": 8911,
  "timestamp": "20230629-150002"
}
```

### Example output

`snowflake_data_81ad294cbb7842a491dec9670a6bd192_20230629-150002.json` is a real upload from a run with `--table_name ORDERS_100K --group_column O_ORDERDATE --sum_column O_TOTALPRICE`. An earlier version named uploads `snowflake_data_…`, and the current code uses the table name. It has one record per source row (8,911 rows, January–August 1998), each carrying its month's total in `SUM(O_TOTALPRICE)`. Timestamps (`O_ORDERDATE`, `CREATED_AT`) are epoch milliseconds, the pandas default for `to_json`.

## Setup

1. Install [uv](https://docs.astral.sh/uv/) (for example `brew install uv`). The project targets Python 3.14, pinned in `.python-version`, and uv downloads it if needed.
2. Run `uv sync` to create `.venv` from the locked dependencies in `uv.lock`, including the dev tools.
3. Copy `.env.example` to `.env` and fill in the Snowflake (`SNOWFLAKE_*`) and AWS values. `.env` is gitignored, so it never gets committed.

All credentials come from environment variables, and none live in the code. The Snowflake user needs read access to the source table, and the AWS keys need `s3:PutObject` on the destination bucket.

## Usage

```sh
uv run --env-file .env main.py --table_name ORDERS_100K --group_column O_ORDERDATE --sum_column O_TOTALPRICE
```

| Option | Required | Description |
| --- | --- | --- |
| `--group_column` | yes | Date or timestamp column whose month and year define the groups |
| `--sum_column` | yes | Numeric column to total per month |
| `--table_name` | no | Source table, optionally qualified as `database.schema.table` (default `LOCATIONS_595`) |
| `--bucket_name` | no | Destination S3 bucket (default: `AWS_STORAGE_BUCKET_NAME`) |

Variables exported in your shell work as well. `--env-file` is just a convenience.

### Sample tables

The `PUBLIC` schema used during development has three tables. Their columns and a few example rows are in `sample_schemas.txt`.

| Table | `--group_column` | `--sum_column` |
| --- | --- | --- |
| `LOCATIONS_595` | `DOB` | `AREA_KM2` |
| `ORDERS_100K` | `O_ORDERDATE` | `O_TOTALPRICE` |
| `MOVIE_RATINGS_27M` | `TIMESTAMP` | `RATING` |

## How it works

| File | Role |
| --- | --- |
| `main.py` | CLI (`argparse`), the read-and-aggregate step (`snowflake_df_read_and_filter`), JSON serialization, and the S3 upload (`transfer_data`), which returns the result summary |
| `snowflake_service.py` | Reads credentials from the environment, manages the Snowflake connection, and renders queries safely |
| `tests/` | pytest suite, with a fake Snowflake service and [moto](https://github.com/getmoto/moto) for S3 |
| `write_to_parquet.py` | A commented-out sketch of batched Parquet writing with pyarrow. It is not used by the pipeline. |

Design choices:

- **Columns are chosen explicitly.** The tables have several numeric and date columns. For example, `ORDERS_100K` has float key columns (`O_ORDERKEY`, `O_CUSTKEY`, `O_SHIPPRIORITY`) and two timestamps (`O_ORDERDATE`, `CREATED_AT`). Summing an order key is meaningless, so the caller names the date and sum columns rather than having the pipeline guess from the schema.
- **Queries are written as t-strings (Python 3.14 template strings).** Table and column names can't be bound as SQL parameters, so `snowflake_service.sql()` accepts only values that are plain Snowflake identifiers, and rejects anything else before it reaches the query. That blocks SQL injection through the command-line options.
- **The upload goes from memory.** The DataFrame is serialized to JSON bytes and sent with `put_object`, with no temporary file on disk. Records orientation keeps the output easy to read with `jq` or `json_pp`.
- **Credentials come from the environment,** and the pipeline exits with a clear error naming any missing variables.

## Development

These are the same checks CI runs (`.github/workflows/ci.yml`) on every pull request and push to `main`:

| Stage | Command |
| --- | --- |
| Test | `uv run pytest` |
| Lint | `uv run ruff check .` |
| Type check | `uv run mypy` (strict mode) |
| Format | `uv run ruff format --check .` (drop `--check` to apply) |

The tests need no credentials or network access. Renovate keeps dependencies and GitHub Actions up to date.

## Limitations and next steps

- **Two reads per run.** The table is read once in full and once for the monthly totals. The aggregation could happen in a single query, using a window function, or in pandas from the one read.
- **Everything is held in memory.** The full table, the result and the JSON bytes all sit in RAM, which suits tables that fit comfortably in memory, and the original target server had 1 GB. For larger data:
  - **Beyond memory (more than about 1 GB):** read in batches, or one month at a time, and write each batch to Parquet partitioned by year and month (`write_to_parquet.py` sketches the batched writer). Compute the totals per partition, and upload the files to S3 with multipart uploads.
  - **Terabyte scale:** let Snowflake do the work, with `COPY INTO @stage` to unload the aggregated result straight to S3 as partitioned Parquet, or move the transform to Spark.
- **JSON is the only output format.** Parquet would be smaller and typed. The format could become an option, with the S3 content type set to match.
- **The `SUM(...)` column is added alongside the original sum column.** Whether stakeholders want the per-row value, the monthly total, or both is still an open question (there's a `TODO` in `main.py`).
- **Upload failures are only logged.** `transfer_data` logs a non-200 response from S3, but still returns a result, and `snowflake_df_read_and_filter` prints the joined DataFrame to stdout. Both should be tightened before production use.

## License

GPL-3.0, see `LICENSE`.
