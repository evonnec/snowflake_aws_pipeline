import pytest

from snowflake_service import MissingCredentialsError, credentials_from_env, sql

CREDENTIAL_ENV_VARS = [
    "SNOWFLAKE_USER",
    "SNOWFLAKE_PASSWORD",
    "SNOWFLAKE_ACCOUNT",
    "SNOWFLAKE_DATABASE",
    "SNOWFLAKE_SCHEMA",
    "SNOWFLAKE_WAREHOUSE",
    "SNOWFLAKE_ROLE",
]


@pytest.mark.parametrize(
    "identifier",
    ["LOCATIONS_595", "o_orderdate", "_PRIVATE", "COL$1", "PUBLIC.PUBLIC.ORDERS_100K"],
)
def test_sql_renders_valid_identifiers(identifier: str) -> None:
    assert sql(t"SELECT * FROM {identifier}") == f"SELECT * FROM {identifier}"


def test_sql_renders_multiple_interpolations() -> None:
    table, sum_col, group_col = "ORDERS_100K", "O_TOTALPRICE", "O_ORDERDATE"
    query = sql(
        t"SELECT sum({sum_col}), MONTH({group_col}) FROM {table} "
        t"GROUP BY MONTH({group_col})"
    )
    assert query == (
        "SELECT sum(O_TOTALPRICE), MONTH(O_ORDERDATE) FROM ORDERS_100K "
        "GROUP BY MONTH(O_ORDERDATE)"
    )


def test_sql_without_interpolations() -> None:
    assert sql(t"SELECT 1") == "SELECT 1"


@pytest.mark.parametrize(
    "value",
    [
        "X; DROP TABLE Y",
        "LOCATIONS_595 --",
        "a b",
        "1ABC",
        '"QUOTED"',
        "",
        "A.B.C.D",
        5,
        None,
    ],
)
def test_sql_rejects_non_identifiers(value: object) -> None:
    with pytest.raises(ValueError, match="not a valid Snowflake identifier"):
        sql(t"SELECT * FROM {value}")


def test_credentials_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in CREDENTIAL_ENV_VARS:
        monkeypatch.setenv(name, name.lower())

    credentials = credentials_from_env()

    assert credentials["user"] == "snowflake_user"
    assert credentials["password"] == "snowflake_password"
    assert credentials["role"] == "snowflake_role"


def test_credentials_from_env_lists_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in CREDENTIAL_ENV_VARS:
        monkeypatch.setenv(name, name.lower())
    monkeypatch.delenv("SNOWFLAKE_PASSWORD")
    monkeypatch.setenv("SNOWFLAKE_ROLE", "")  # empty counts as missing

    with pytest.raises(MissingCredentialsError) as excinfo:
        credentials_from_env()

    assert str(excinfo.value) == (
        "missing environment variables: SNOWFLAKE_PASSWORD, SNOWFLAKE_ROLE"
    )
