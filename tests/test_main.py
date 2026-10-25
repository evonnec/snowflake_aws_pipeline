import json
from collections.abc import Iterator
from pathlib import Path
from string.templatelib import Template
from types import TracebackType
from typing import Self, Unpack

import boto3
import pandas as pd
import pytest
from moto import mock_aws

import main
from snowflake_service import SnowflakeCredentials, sql

BUCKET = "test-bucket"
CREDENTIALS: SnowflakeCredentials = {
    "user": "user",
    "password": "password",
    "account": "account",
    "database": "database",
    "schema": "schema",
    "warehouse": "warehouse",
    "role": "role",
}


class FakeSnowflakeService:
    """stands in for SnowflakeService; renders queries through the real sql()"""

    queries: list[str] = []

    def __init__(self, **credentials: Unpack[SnowflakeCredentials]) -> None:
        pass

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        pass

    def get_df_from_query(self, query: Template) -> pd.DataFrame:
        rendered = sql(query)
        self.queries.append(rendered)
        if "GROUP BY" in rendered:
            return pd.DataFrame(
                {"SUM(AREA_KM2)": [3.0, 10.0], "MONTH": [1, 2], "YEAR": [2023, 2023]}
            )
        return pd.DataFrame(
            {
                "NAME": ["a", "b", "c", None],
                "DOB": pd.to_datetime(
                    ["2023-01-05", "2023-01-20", "2023-02-01", "NaT"]
                ),
                "AREA_KM2": [1.0, 2.0, 10.0, None],
            }
        )


@pytest.fixture
def fake_snowflake(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    FakeSnowflakeService.queries = []
    monkeypatch.setattr(main, "SnowflakeService", FakeSnowflakeService)
    return FakeSnowflakeService.queries


@pytest.fixture
def snowflake_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in CREDENTIALS.items():
        monkeypatch.setenv(f"SNOWFLAKE_{key.upper()}", str(value))


@pytest.fixture
def s3_bucket(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    with mock_aws():
        boto3.client("s3").create_bucket(Bucket=BUCKET)
        yield BUCKET


def test_parser_requires_group_and_sum_columns() -> None:
    with pytest.raises(SystemExit):
        main.build_parser().parse_args(["--table_name", "LOCATIONS_595"])


def test_parser_defaults() -> None:
    args = main.build_parser().parse_args(
        ["--group_column", "DOB", "--sum_column", "AREA_KM2"]
    )
    assert args.table_name == "LOCATIONS_595"


def test_read_and_filter_adds_monthly_sum(fake_snowflake: list[str]) -> None:
    df = main.snowflake_df_read_and_filter(
        "LOCATIONS_595", "DOB", "AREA_KM2", CREDENTIALS
    )

    assert fake_snowflake[0] == "SELECT * FROM LOCATIONS_595"
    assert "GROUP BY MONTH(DOB), YEAR(DOB)" in fake_snowflake[1]
    # helper join columns are dropped, the fully blank row is removed
    assert list(df.columns) == ["NAME", "DOB", "AREA_KM2", "SUM(AREA_KM2)"]
    assert df["NAME"].tolist() == ["a", "b", "c"]
    assert df["SUM(AREA_KM2)"].tolist() == [3.0, 3.0, 10.0]


def test_read_and_filter_rejects_sql_injection(fake_snowflake: list[str]) -> None:
    with pytest.raises(ValueError, match="not a valid Snowflake identifier"):
        main.snowflake_df_read_and_filter(
            "T; DROP TABLE T", "DOB", "AREA_KM2", CREDENTIALS
        )
    assert fake_snowflake == []


def test_create_file_from_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    df = pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})

    contents = main.create_file_from_data(df)

    assert json.loads(contents) == [{"A": 1, "B": "x"}, {"A": 2, "B": "y"}]
    # serialized in memory; nothing is left behind on disk
    assert list(tmp_path.iterdir()) == []


def test_transfer_data_uploads_json(s3_bucket: str) -> None:
    df = pd.DataFrame({"A": [1, 2, 3]})

    result = main.transfer_data("LOCATIONS_595", s3_bucket, df)

    assert result["row_count"] == 3
    assert result["file_name"].startswith("LOCATIONS_595_")
    obj = boto3.client("s3").get_object(Bucket=s3_bucket, Key=result["file_name"])
    assert obj["ContentType"] == "application/json"
    assert json.loads(obj["Body"].read()) == [{"A": 1}, {"A": 2}, {"A": 3}]


@pytest.mark.usefixtures("snowflake_env")
def test_main_end_to_end(fake_snowflake: list[str], s3_bucket: str) -> None:
    result = main.main(
        [
            "--table_name",
            "LOCATIONS_595",
            "--group_column",
            "DOB",
            "--sum_column",
            "AREA_KM2",
            "--bucket_name",
            s3_bucket,
        ]
    )

    assert result["row_count"] == 3
    keys = [
        o["Key"]
        for o in boto3.client("s3").list_objects_v2(Bucket=s3_bucket)["Contents"]
    ]
    assert keys == [result["file_name"]]


def test_main_requires_bucket(
    monkeypatch: pytest.MonkeyPatch, fake_snowflake: list[str]
) -> None:
    monkeypatch.setattr(main, "AWS_STORAGE_BUCKET_NAME", None)
    with pytest.raises(SystemExit):
        main.main(["--group_column", "DOB", "--sum_column", "AREA_KM2"])
    # fails fast, before reading from Snowflake
    assert fake_snowflake == []


def test_main_requires_snowflake_credentials(
    monkeypatch: pytest.MonkeyPatch, fake_snowflake: list[str]
) -> None:
    for key in CREDENTIALS:
        monkeypatch.delenv(f"SNOWFLAKE_{key.upper()}", raising=False)
    with pytest.raises(SystemExit):
        main.main(
            [
                "--group_column",
                "DOB",
                "--sum_column",
                "AREA_KM2",
                "--bucket_name",
                BUCKET,
            ]
        )
    assert fake_snowflake == []
