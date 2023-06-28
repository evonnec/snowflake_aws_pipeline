from snowflake_service import SnowflakeService
import boto3
import time
import json
import pandas as pd
import argparse
import logging

SNOWFLAKE_CREDENTIALS = {
    "user": "candidate",
    "password": "AmplifyData1",
    "account": "PZMAOVJ-AMPLIFY_PUBLIC",
    "database": "PUBLIC",
    "schema": "PUBLIC",
    "warehouse": "PUBLIC",
    "role": "PUBLIC"
}
AWS_STORAGE_BUCKET_NAME = 'amplifydata-evonnecho'
AWS_ACCESS_KEY_ID = 'AKIASC5E62QHDMBCP6FA'
AWS_SECRET_ACCESS_KEY = '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'

parser = argparse.ArgumentParser(
    description='Pull client data from Snowflake and Push to S3'
)
parser.add_argument(
    '--table_name', 
    default='LOCATIONS_595', 
    help='specify table to move', 
    required=False
)
parser.add_argument(
    '--bucket_name', 
    default=AWS_STORAGE_BUCKET_NAME, 
    help='specify s3 bucket to move to', 
    required=False
)

args = parser.parse_args()

def sample_snowflake_df_read(table_name: str) -> None:
    """sample function that reads a snowflake table into a pandas dataframe"""
    with SnowflakeService(**SNOWFLAKE_CREDENTIALS) as ss:
        df = ss.get_df_from_query(f"SELECT * FROM {table_name} LIMIT 5")
    print(df.head())

def sample_snowflake_results_describe(table_name: str) -> None:
    """sample function that describes a snowflake table"""
    with SnowflakeService(**SNOWFLAKE_CREDENTIALS) as ss:
        results = ss.execute_query(f"DESCRIBE TABLE {table_name}")
    print(results.fetchall())

def sample_snowflake_results_read(table_name: str) -> None:
    """sample function that reads a snowflake table into a results object"""
    with SnowflakeService(**SNOWFLAKE_CREDENTIALS) as ss:
        results = ss.execute_query(f"SELECT * FROM {table_name} LIMIT 5")
    for row in results.fetchall():
        print(row)

def sample_s3_results_push(
    table_name: str, 
    source_data: pd.DataFrame
    ) -> None:
    """Takes source_data
    create_file_from_data(source_data) and create parquet
    open session to s3
    push file to s3
    push results.json to s3

    Args:
        table_name (str): _description_
        source_data (pd.DataFrame): _description_
    """
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )
    
    s3 = session.resource('s3')
    bucket = s3.Bucket(args.bucket_name)
    file_path = f"{table_name}"
    try:
        s3.meta.client.put_object(
            Body=create_file_from_data(source_data=source_data),
            Key=file_path, 
            Bucket=bucket, 
            ContentType='parquet'
        )
    except Exception as e:
        raise e
            
def create_file_from_data(source_data: pd.DataFrame) -> None:
    """create parquet file from data

    Args:
        source_data (pd.DataFrame): _description_
    """
    parquet_file = f"{source_data}.parquet"
    source_data.to_parquet(parquet_file, engine = 'pyarrow', compression = 'gzip')
    logging.info('Parquet file named "%s" created', parquet_file)
    
def transform_data(source_data: str) -> pd.DataFrame:
    """
    TODO: Remove any fully blank rows
    TODO: The customer wants to consume data at a monthly level of aggregation, 
    so you should send an aggregated dataset using the existing columns. 
    For all non-numeric columns, leave unaggregated.
    For numeric columns, use SUM aggregation.
    """
    pass 
    
def transfer_data(
    source_table: str, 
    destination_s3_bucket: str) -> int, dict:
    """
    transfer data from source Snowflake table --> pull data
    transform_data
    push result of transform_data to destination S3 bucket
    returns a results.json
    """
    
    try:
        sample_s3_results_push(args.table_name, sample_snowflake_df_read(args.table_name))
        response_code = 200
    except Exception as e:
        raise e
    
    row_count = 0 #count the rows
    time_stamp = time.time() #record timestamp
    results = {
        "file_name": f"{source_table}",
        "row_count": row_count,
        "timestamp": time_stamp
    }

    return response_code, json.dumps(results)
    

if __name__ == '__main__':
    print(f"READING {args.table_name} SQL TABLE INTO PANDAS DATAFRAME\n")
    sample_snowflake_df_read(f"{args.table_name}")

    print(f"\nREADING {args.table_name} SQL TABLE INTO RESULTS OBJECT\n")
    sample_snowflake_results_read(f"{args.table_name}")
    
    print(f"\nDESCRIBE {args.table_name} SQL TABLE\n")
    sample_snowflake_results_describe(f"{args.table_name}")

