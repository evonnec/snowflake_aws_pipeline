from snowflake_service import SnowflakeService

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
AWS_SECRET_ACCESS_KEY = 'FTbEZqie2ZuOBB6jG9CF52Q0jevp+ZSRfDldFaTA'

def sample_snowflake_df_read():
    """sample function that reads a snowflake table into a pandas dataframe"""
    with SnowflakeService(**SNOWFLAKE_CREDENTIALS) as ss:
        df = ss.get_df_from_query("SELECT * FROM LOCATIONS_595 LIMIT 5")
    print(df.head())


def sample_snowflake_results_read():
    """sample function that reads a snowflake table into a results object"""
    with SnowflakeService(**SNOWFLAKE_CREDENTIALS) as ss:
        results = ss.execute_query("SELECT * FROM LOCATIONS_595 LIMIT 5")
    for row in results.fetchall():
        print(row)

def transfer_data(source_table, destination_s3_bucket):
    """transfer data from source Snowflake table to destination S3 bucket"""
    pass

if __name__ == '__main__':
    print("READING SQL TABLE INTO PANDAS DATAFRAME\n")
    sample_snowflake_df_read()

    print("\nREADING SQL TABLE INTO RESULTS OBJECT\n")
    sample_snowflake_results_read()

