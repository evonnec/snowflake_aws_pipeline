## Background

Amplify Data helps its customers distribute their data to external stakeholders. Prior to doing so, it is important to be able to clean and aggregate the data being transferred. We want to build some tooling to allow customers to transfer data between their system and their stakeholders’ systems.

## Goals

Your goal is to write a program that transfers data between a Snowflake database owned by the customer and an S3 bucket owned by their stakeholder. When transferring the data, please apply the following transformations to the source data:

- Remove any fully blank rows
- If there is a date column in the data, aggregate the full dataset to be monthly.  For all non-numeric columns, leave those unaggregated, and you can SUM all numeric columns.

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
3. Run `pip install -r requirements.txt` 
4. Running `python main.py` should read from a sample snowflake table and output the first 5 rows (twice)

### Assumptions

You can assume the credentials will provide the appropriate access (please reach out if you have any issues).

Our processing server has 1GB RAM.

## Deliverables

1. Runnable program written in Python
    1. Feel free to use any external libraries needed to accomplish the task
2. Explain how to run your program 
3. Any other comments you would like to include
4. Live review meeting to discuss the below questions

### Review Meeting

We'll discuss the following questions (plus any other relevant follow-ups):

1. Provide a brief explanation of your architecture and any external libraries used. Would you architect it differently if you had more time?
2. If you had to handle file sizes larger than 1GB, how would you change your program (if at all)? Larger than 1TB?
3. How would you test that your program is working?
4. If you had more time, what other features would you include?
5. What was the most difficult part of this problem? If you were running this assessment, what would you change?

## Evaluation

You will be evaluated based on the following criteria:

1. Correctness – Does the program correctly apply the transformations and transfer the data? 
2. Clarity – Is your code well-organized and easy to read? 
3. Extensibility – Is your solution architected in a manner that makes it easy to collaborate with multiple engineers, and allow them to add and modify features in a consistent, testable way?
4. Communication - Were you able to explain your answers in the review meeting? Did you ask clarifying questions if needed?
