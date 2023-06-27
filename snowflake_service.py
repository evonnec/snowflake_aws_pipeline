from typing import Any

from sqlalchemy import create_engine
from snowflake.sqlalchemy import URL
import snowflake.connector
import pandas as pd
from sqlalchemy.engine import CursorResult, Row


class SnowflakeService:

    def __init__(self, user, password, account, database, schema, warehouse, role):
        self.user = user
        self.password = password
        self.account = account
        self.database = database
        self.schema = schema
        self.warehouse = warehouse
        self.role = role
        self.create_connection()

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.close_connection()

    def create_connection(self):
        """creates snowflake connection with SQL Alchemy"""
        self.engine = self.get_engine()
        self.connection = self.engine.connect()

    def close_connection(self):
        """closes snowflake connection"""
        if self.connection:
            self.connection.close()
        if self.engine:
            self.engine.dispose()

    def get_snowflake_connector_connection(self):
        """get Snowflake connector connection"""
        return snowflake.connector.connect(
            account=self.account,
            user=self.user,
            password=self.password,
            database=self.database,
            schema=self.schema,
            warehouse=self.warehouse,
            role=self.role
        )

    def get_engine(self):
        """get SQLAlchemy engine"""
        engine = create_engine(self.get_engine_URL())
        return engine

    def get_engine_URL(self):
        """get SQLAlchemy engine URL"""
        return URL(
                account=self.account,
                user=self.user,
                password=self.password,
                database=self.database,
                schema=self.schema,
                warehouse=self.warehouse,
                role=self.role,
            )

##########################################################################
# execution
##########################################################################

    def get_single_response_from_query(self, query: str) -> Any:
        """returns first returned value from first row of query"""
        results = self.get_first_row_from_query(query)
        if results is None:
            return None
        return results[0]

    def get_first_row_from_query(self, query: str) -> Row | None:
        """return first row from a query"""
        results = self.execute_query(query)
        if results is None:
            return None
        return results.fetchone()

    def execute_query(self, query: str) -> CursorResult:
        """
        runs query, returning results
        """
        return self.connection.execute(query)

    def get_df_from_query(self, query: str) -> pd.DataFrame:
        """returns pandas dataframe from results of query"""
        with self.get_snowflake_connector_connection() as conn:
            cur = conn.cursor()
            cur.execute(query)
            df = cur.fetch_pandas_all()
            return df
