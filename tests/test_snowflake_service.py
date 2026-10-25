import pytest

from snowflake_service import sql


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
