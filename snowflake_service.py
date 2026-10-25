import os
import re
from string.templatelib import Interpolation, Template
from types import TracebackType
from typing import Any, ReadOnly, Self, TypedDict, Unpack

import pandas as pd
import snowflake.connector
from snowflake.connector import SnowflakeConnection
from snowflake.sqlalchemy import URL
from sqlalchemy import CursorResult, Engine, Row, create_engine, text
from sqlalchemy.engine import Connection

# unquoted Snowflake identifier, optionally qualified as database.schema.object
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*(\.[A-Za-z_][A-Za-z0-9_$]*){0,2}")


class SnowflakeCredentials(TypedDict):
    user: ReadOnly[str]
    password: ReadOnly[str]
    account: ReadOnly[str]
    database: ReadOnly[str]
    schema: ReadOnly[str]
    warehouse: ReadOnly[str]
    role: ReadOnly[str]


class MissingCredentialsError(RuntimeError):
    pass


def credentials_from_env() -> SnowflakeCredentials:
    """reads Snowflake credentials from SNOWFLAKE_* environment variables"""
    missing: list[str] = []

    def require(name: str) -> str:
        value = os.getenv(name, "")
        if not value:
            missing.append(name)
        return value

    credentials: SnowflakeCredentials = {
        "user": require("SNOWFLAKE_USER"),
        "password": require("SNOWFLAKE_PASSWORD"),
        "account": require("SNOWFLAKE_ACCOUNT"),
        "database": require("SNOWFLAKE_DATABASE"),
        "schema": require("SNOWFLAKE_SCHEMA"),
        "warehouse": require("SNOWFLAKE_WAREHOUSE"),
        "role": require("SNOWFLAKE_ROLE"),
    }
    if missing:
        raise MissingCredentialsError(
            f"missing environment variables: {', '.join(missing)}"
        )
    return credentials


def sql(query: Template) -> str:
    """
    renders a t-string query, e.g. t"SELECT * FROM {table_name}"
    identifiers (tables, columns) can't be bound as query parameters, so every
    interpolated value must be a plain Snowflake identifier -- anything else
    is rejected rather than spliced into the SQL
    """
    parts: list[str] = []
    for item in query:
        match item:
            case str() as literal:
                parts.append(literal)
            case Interpolation(value=str() as value) if IDENTIFIER.fullmatch(value):
                parts.append(value)
            case Interpolation(value=value, expression=expression):
                raise ValueError(
                    f"{expression}={value!r} is not a valid Snowflake identifier"
                )
    return "".join(parts)


class SnowflakeService:
    def __init__(self, **credentials: Unpack[SnowflakeCredentials]) -> None:
        self.credentials = credentials
        self.create_connection()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close_connection()

    def create_connection(self) -> None:
        """creates snowflake connection with SQL Alchemy"""
        self.engine = self.get_engine()
        self.connection: Connection = self.engine.connect()

    def close_connection(self) -> None:
        """closes snowflake connection"""
        if self.connection:
            self.connection.close()
        if self.engine:
            self.engine.dispose()

    def get_snowflake_connector_connection(self) -> SnowflakeConnection:
        """get Snowflake connector connection"""
        return snowflake.connector.connect(**self.credentials)

    def get_engine(self) -> Engine:
        """get SQLAlchemy engine"""
        engine = create_engine(self.get_engine_URL())
        return engine

    def get_engine_URL(self) -> str:
        """get SQLAlchemy engine URL"""
        return URL(**self.credentials)

    ##########################################################################
    # execution
    ##########################################################################

    def get_single_response_from_query(self, query: Template) -> Any:
        """
        returns first returned value from first row of query
        TODO: perhaps change to try except to handle blank rows
        """
        results = self.get_first_row_from_query(query)
        if results is None:
            return None
        return results[0]

    def get_first_row_from_query(self, query: Template) -> Row[Any] | None:
        """
        return first row from a query
        """
        results = self.execute_query(query)
        if results is None:
            return None
        return results.fetchone()

    def execute_query(self, query: Template) -> CursorResult[Any]:
        """
        runs query, returning results
        """
        return self.connection.execute(text(sql(query)))

    def get_df_from_query(self, query: Template) -> pd.DataFrame:
        """returns pandas dataframe from results of query"""
        with self.get_snowflake_connector_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql(query))
            df = cur.fetch_pandas_all()
            return df
