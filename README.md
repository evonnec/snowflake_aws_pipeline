## Background

Amplify Data helps its customers distribute their data to external stakeholders. Prior to doing so, it is important to be able to clean and aggregate the data being transferred. We want to build some tooling to allow customers to transfer data between their system and their stakeholders’ systems.

## Goals

Your goal is to write a program that transfers data between a Snowflake database owned by the customer and an S3 bucket owned by their stakeholder. When transferring the data, please apply the following transformations to the source data:

- Remove any fully blank rows
- The customer wants to consume data at a monthly level of aggregation, so you should send an aggregated dataset using the existing columns. For all non-numeric columns, leave unaggregated, for numeric columns, use SUM aggregation.

### Outputs

To make this easier to use in an API endpoint, you should have a main function `transfer_data(source_table, destination_s3_bucket)` that takes the source Snowflake table and the destination S3 bucket and returns a results JSON in the following format:

```json
{
  "file_name": str,
  "row_count": int,
  "timestamp": str
}
```

### Inputs

The Snowflake database credentials are contained in `main.py`, along with some starter code for pulling data from Snowflake.  There are 3 sample tables available on the PUBLIC database:

- LOCATIONS_595
- ORDERS_100K
- MOVIE_RATINGS_27M

Your destination S3 bucket and access credentials are provided in `main.py`.

### Setup

To get started, follow these steps:

1. Clone this git repo to a folder on your local computer and navigate to it
2. Create a virtual environment in that folder  
  ```python3 -m venv amplifydata```  
  ```source amplifydata/bin/activate```  
3. Run `pip install -r requirements.txt`  
  Added pyproject.toml to project, and added relevant libraries for type checking.  
  In order to skip libraries without type check libraries, ignore and override in pyproject.toml  
  ```pip install -e .```  
4. Running `python main.py` should read from a sample snowflake table and output the first 5 rows (twice)  

### Assumptions

You can assume the credentials will provide the appropriate access (please reach out if you have any issues).

Our processing server has 1GB RAM.

## Deliverables

1. Runnable program written in Python
    1. Feel free to use any external libraries needed to accomplish the task
        - installing and using mypy to find bugs  
        ```python3 -m mypy . --exclude amplifydata``` should return `Success: no issues found in source files`  
        - installing and using ruff to find formatting suggestions  
        ```ruff --fix main.py```  
2. Explain how to run your program   
    2. For each of the tables, we ought to pass in the date column in which to group by month, and the column to sum.  
    We could potentially have pulled out the schemas of the tables for datetime col's and int/float/etc col's in order to do the group by and sum, but some tables had more than one col.  
    Specifying explicitly, we know what we have.  
  ```python3 main.py --table_name 'LOCATIONS_595' --sum_column 'AREA_KM2' --group_column 'DOB'```  
  ```python3 main.py --table_name 'ORDERS_100K' --sum_column 'O_TOTALPRICE' --group_column 'O_ORDERDATE'```  
  ```python3 main.py --table_name 'MOVIE_RATINGS_27M' --sum_column 'RATING' --group_column 'TIMESTAMP'```  
    Format Options:  
    - we can choose to stream io bytes or write to a file format  
    - file formats that would work are .parquet or .json  
    - we chose .json for now, and specify the `orient` parameter to give an orientation to determine how we'd like to see the output.  
    for now, we've used `records` so we can pretty print the results  
3. Any other comments you would like to include  
    - we pull from the database twice to do the transform. ideally this would be one pull per time the program runs. and give it the filter before it returns all the results.  
    - pull the secrets using secrets manager or similar, not have them in the code.  
    - abstraction of more of the hard-coded elements
    - unfortunately there are no tests or exception handling for the moment  
    - notes in code to see  
4. Live review meeting to discuss the below questions

### Review Meeting

We'll discuss the following questions (plus any other relevant follow-ups):

1. Provide a brief explanation of your architecture and any external libraries used. Would you architect it differently if you had more time?
    - brief architecture is that the program takes in a table, and a group by column (i.e. datetime) and a sum column (i.e. some numeric field) and sums the numeric field grouped by the month and year.
    - it transforms it as required (no fully null rows), and pushes the result in the form of a dataframe.
    - we use pandas dataframe for this example
    - holding in memory can be expensive as is writing to disk. we can make additional considerations if the data is too much for the resources it has and take a look at numpy or Spark.
    - If I had more time, I'd probably clean it up more, further modularize the code, add tests for each item, and handle exceptions clearly.
2. If you had to handle file sizes larger than 1GB, how would you change your program (if at all)? Larger than 1TB?
    - Yes, as I stated before, we might have to move away from a dataframe and move to a native data structure in python object instead.
3. How would you test that your program is working?
    - I would write tests in a test suite using pytest, then have CI run those tests each time code is pushed.
4. If you had more time, what other features would you include?
    - the items I wrote above
5. What was the most difficult part of this problem? If you were running this assessment, what would you change?
    - getting used to libraries I haven't worked with that much. If I were running this assessment, I'd perhaps make the transform more clear as to exact expected output with a sample input example so it's clear what's expected. I would also maybe ask for different data type outputs to be handled and provide them based on what a client expects. also provide any specifics with respect to filename.

create document here
## Evaluation

You will be evaluated based on the following criteria:

1. Correctness – Does the program correctly apply the transformations and transfer the data? 
2. Clarity – Is your code well-organized and easy to read? 
3. Extensibility – Is your solution architected in a manner that makes it easy to collaborate with multiple engineers, and allow them to add and modify features in a consistent, testable way?
4. Communication - Were you able to explain your answers in the review meeting? Did you ask clarifying questions if needed?
