# # EXAMPLE 3 - USING PANDAS & PYARROW
# import pandas as pd
# import pyarrow as pa
# import pyarrow.parquet as pq
# import logging

# # SETTING BATCH SIZE
# batch_size = 250

# parquet_schema = pa.schema([('as_of_date', pa.timestamp('ns')),
#                             ('company_code', pa.string()),
#                             ('fc_balance', pa.float32()),
#                             ('fc_currency_code', pa.string()),
#                             ('gl_account_number', pa.string()),
#                             ('gl_account_name', pa.string())
#                            ])

# parquet_file = 'example_pa.parquet'

# total_rows = 0

# logging.info('Writing to file %s in batches...', parquet_file)

# with pq.ParquetWriter(parquet_file, parquet_schema, compression='gzip') as writer:
#     while True:
#         data = db_cursor_pg.fetchmany(batch_size)
#         if not data:
#             break
#         df = pd.DataFrame(data, columns=list(parquet_schema.names))
#         df = df.astype(schema)
        
#         table = pa.Table.from_pandas(df)
#         total_rows += table.num_rows
        
#         writer.write_table(table)

# logging.info('Full parquet file named "%s" has been written to disk \
#               with %s total rows', parquet_file, total_rows)

# to_parquet, engine = 'pyarrow', compression = 'gzip'
