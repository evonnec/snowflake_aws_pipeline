from snowflake_service import SnowflakeService
import boto3
import uuid
import time
import pandas as pd
import argparse
import logging
import pathlib

SNOWFLAKE_CREDENTIALS = {
    "user": "candidate",
    "password": "AmplifyData1",
    "account": "PZMAOVJ-AMPLIFY_PUBLIC",
    "database": "PUBLIC",
    "schema": "PUBLIC",
    "warehouse": "PUBLIC",
    "role": "PUBLIC"
}
"""
TODO: abstract buckets, access key IDs and secret access keys
"""
AWS_STORAGE_BUCKET_NAME = 'amplifydata-evonnecho'
AWS_ACCESS_KEY_ID = 'AKIASC5E62QHDMBCP6FA'
AWS_SECRET_ACCESS_KEY = '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'

parser = argparse.ArgumentParser(
    description='Pull client data from Snowflake, transform output, push to S3'
)
parser.add_argument(
    '--table_name', 
    default='LOCATIONS_595', 
    help='specify the table to retrieve from SnowFlake, make aggregations, push to S3',
    required=False
)
parser.add_argument(
    '--bucket_name', 
    default=AWS_STORAGE_BUCKET_NAME, 
    help='specify the s3 bucket to move to', 
    required=False
)
parser.add_argument(
    '--group_column', 
    default=None, 
    help='references a datetime typed col in order to do a monthly aggregation field', 
    required=True
)
parser.add_argument(
    '--sum_column', 
    default=None, 
    help='references a float int or similiar typed col in order to sum a numeric field \
    by the specified group_column', 
    required=True
)

args = parser.parse_args()

def final_snowflake_df_read_and_filter(
    table_name: str,
    group_col: str,
    sum_col: str
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
    
    with SnowflakeService(**SNOWFLAKE_CREDENTIALS) as ss:
        df_all = ss.get_df_from_query(
            f"SELECT * FROM {table_name}"
        )
        df_all['MONTH'] = pd.DatetimeIndex(df_all[group_col]).month
        df_all['YEAR'] = pd.DatetimeIndex(df_all[group_col]).year
        df_filtered = ss.get_df_from_query(
            f"SELECT sum({sum_col}), MONTH({group_col}) as MONTH, \
                YEAR({group_col}) as YEAR FROM {table_name} \
                GROUP BY MONTH({group_col}), YEAR({group_col})"
        )
        df_join = df_all.merge(df_filtered, \
            on=["MONTH", "YEAR"], how="left" \
        ).drop("MONTH", axis=1 \
        ).drop("YEAR", axis=1 \
        ).drop(sum_col, axis=1 \
        ).dropna(how='all')
        ### TODO: unclear on whether to drop `sum_col` -- check
    print(df_join)
    return df_join

def transfer_data(
    table_name: str, 
    transformed_data: pd.DataFrame
    ) -> dict:
    """Takes result of transformed source data
    create_file_from_data(transformed_data) and create file
    open session to s3, push file to s3
    return results json

    Args:
        table_name (str): name of source table in SnowFlake db
        transformed_data (pd.DataFrame): transformed source data as a DataFrame
    """
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )
    
    s3 = session.resource('s3')
    file_path = f"{table_name}"
    body = create_file_from_data(transformed_source_data=transformed_data)
    s3.meta.client.put_object(
        Body=body,
        Key=file_path, 
        Bucket=args.bucket_name, 
        ContentType='application/json'
    )
    row_count = len(transformed_data)
    time_stamp = body.split(".")[0].split("_")[3]
    results = {
        "file_name": f"{body}",
        "row_count": row_count,
        "timestamp": time_stamp
    }
    print(results)
    return results
            
def create_file_from_data(transformed_source_data: pd.DataFrame) -> str:
    """create a file from pandas DataFrame
    returns: str 
    __description: the string is the path to json file
    Args:
        transformed_source_data (pd.DataFrame): DataFrame of output
    """
    random_name = uuid.uuid4().hex
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    json_file = f"snowflake_data_{random_name}_{timestamp}.json"
    transformed_source_data.to_json(json_file, \
        orient='records', \
        compression='infer', \
        index='true' \
    )
    logging.info('File named "%s" created', json_file)
    contents = pathlib.Path(json_file)
    return str(contents)
    
if __name__ == '__main__':
    print(f"READING {args.table_name} SQL TABLE INTO PANDAS DATAFRAME\n")
    result = final_snowflake_df_read_and_filter(
        table_name=f"{args.table_name}", 
        group_col=f"{args.group_column}", 
        sum_col=f"{args.sum_column}"
    )

    transfer_data(table_name=args.table_name, transformed_data=result)
