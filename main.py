import argparse
import logging
import os
import time
import uuid
from collections.abc import Sequence
from typing import ReadOnly, TypedDict

import boto3
import pandas as pd

from snowflake_service import (
    MissingCredentialsError,
    SnowflakeCredentials,
    SnowflakeService,
    credentials_from_env,
)


class TransferResult(TypedDict):
    file_name: ReadOnly[str]
    row_count: ReadOnly[int]
    timestamp: ReadOnly[str]


"""
TODO: abstract buckets, access key IDs and secret access keys
"""
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")


def snowflake_df_read_and_filter(
    table_name: str, group_col: str, sum_col: str, credentials: SnowflakeCredentials
) -> pd.DataFrame:
    """
    function that reads a Snowflake table with group_col,
    sum_col params into a pandas DataFrame
    - removes any fully blank rows
    - write data to be consumed at a monthly level of aggregation,
    i.e. send an aggregated dataset using the existing columns.
    For all non-numeric columns, leave unaggregated.
    For numeric columns, use SUM aggregation.
    """

    with SnowflakeService(**credentials) as ss:
        df_all = ss.get_df_from_query(t"SELECT * FROM {table_name}")
        df_filtered = ss.get_df_from_query(
            t"SELECT sum({sum_col}), MONTH({group_col}) as MONTH, "
            t"YEAR({group_col}) as YEAR FROM {table_name} "
            t"GROUP BY MONTH({group_col}), YEAR({group_col})"
        )
    df_all["MONTH"] = pd.DatetimeIndex(df_all[group_col]).month
    df_all["YEAR"] = pd.DatetimeIndex(df_all[group_col]).year
    df_join = (
        df_all.merge(df_filtered, on=["MONTH", "YEAR"], how="left")
        .drop("MONTH", axis=1)
        .drop("YEAR", axis=1)
        # .drop(sum_col, axis=1)
        .dropna(how="all")
    )
    ### TODO: unclear on whether to drop `sum_col` -- check
    print(df_join)
    return df_join


def transfer_data(
    table_name: str, storage_bucket: str, data: pd.DataFrame
) -> TransferResult:
    """Takes result of transformed source data
    create_file_from_data(transformed_data) and create file
    open session to s3, push file to s3
    return results json

    Args:
        table_name (str): name of source table in SnowFlake db
        storage_bucket (str): name of S3 bucket to write data file to
        transformed_data (pd.DataFrame): transformed source data as a DataFrame
    """
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )

    s3 = session.resource("s3")

    random_name = uuid.uuid7().hex
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"{table_name}_{random_name}_{timestamp}.json"
    body = create_file_from_data(transformed_source_data=data)

    result = s3.meta.client.put_object(
        Body=body, Key=filename, Bucket=storage_bucket, ContentType="application/json"
    )  # ideally, we'd like to detect what type of file was uploaded, or send
    # that metadata with the bytes datatype that was sent from create_file_from_data function
    # content_type = media_response.headers["Content-Type"]
    # extension = mimetypes.guess_extension(content_type)

    metadata_resp = result.get("ResponseMetadata", {})
    if metadata_resp.get("HTTPStatusCode") == 200:
        logging.info('File "%s" is transferred', filename)
    else:
        logging.info('Failed to transfer file "%s"', filename)

    row_count = len(data)
    results: TransferResult = {
        "file_name": filename,
        "row_count": row_count,
        "timestamp": timestamp,
    }
    logging.info('Results are "%s"', results)
    return results


def create_file_from_data(transformed_source_data: pd.DataFrame) -> bytes:
    """serialize a pandas DataFrame to JSON records in memory, ready to upload
    returns: bytes
    Args:
        transformed_source_data (pd.DataFrame): DataFrame of output
    """
    # ideally we'd like to parameterize the filetype (e.g. parquet)
    # and serialize accordingly here in this function.
    return transformed_source_data.to_json(orient="records").encode()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pull client data from Snowflake, transform output, push to S3"
    )
    parser.add_argument(
        "--table_name",
        default="LOCATIONS_595",
        help="specify the table to retrieve from SnowFlake, make aggregations, push to S3",
        required=False,
    )
    parser.add_argument(
        "--bucket_name",
        default=AWS_STORAGE_BUCKET_NAME,
        help="specify the s3 bucket to move to",
        required=False,
    )
    parser.add_argument(
        "--group_column",
        default=None,
        help="references a datetime typed col in order to do a monthly aggregation field",
        required=True,
    )
    parser.add_argument(
        "--sum_column",
        default=None,
        help="references a float int or similiar typed col in order to sum a numeric field \
        by the specified group_column",
        required=True,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> TransferResult:
    logging.basicConfig(level=logging.INFO)
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.bucket_name is None:
        parser.error("--bucket_name or AWS_STORAGE_BUCKET_NAME is required")
    try:
        credentials = credentials_from_env()
    except MissingCredentialsError as e:
        parser.error(str(e))

    logging.info("READING %s SQL TABLE INTO PANDAS DATAFRAME", args.table_name)
    result = snowflake_df_read_and_filter(
        table_name=args.table_name,
        group_col=args.group_column,
        sum_col=args.sum_column,
        credentials=credentials,
    )

    logging.info("TRANSFERRING PANDAS DATAFRAME FROM %s TO S3", args.table_name)
    results = transfer_data(
        table_name=args.table_name, data=result, storage_bucket=args.bucket_name
    )

    logging.info("PROCESSING COMPLETED")
    return results


if __name__ == "__main__":
    main()
