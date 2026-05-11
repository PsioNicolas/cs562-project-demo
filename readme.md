# CS562 Final Project

## Important Notes

There seems to be a bug sometimes where if you run the generator on a new file it'll print the output of the previously generated file. I'm guessing this will be a common problem since that part of the code was already given to us.

There are more detailed explanations inside `generator.py`, `input_handler.py`, `phi.py`, `sql.py` and `test_generator.py` about how to create your own tests and Phi expressions. 

Tested on python version 3.10.11. I recommend creating a .venv using this python version, since psycopg2 can break in newer versions.

In the example_inputs folder, there are five examples of Phi queries with corresponding regular SQL queries. 
Ex. example_inputs/query1_phi.txt should output the same table as example_inputs/query1_sql.txt (when sorted)

IMPORTANT: query1_phi.txt (phi_expr_file) is one of the possible inputs to the generator. It creates output_files/_generated_query1.py.

## Instructions

Create a .env file in the format of .env.example. Fill in the environment variables so that the program can access your PostgreSQL database running locally. 

Install dependencies:
`pip install -r requirements.txt`

Run the program (with a file, or input the file after running, or press enter to enter Phi manually):
`python generator.py [phi_expr_file]`

Run the generated file (after first running the generator to generate the file):
`python _generated.py`

Or, run one of the already generated files:
`python output_files/_generated_query<i>.py`

Run the test harness (with a file to test one Phi/SQL pair, or test all of them at once by just running it)
`python test_generator.py [phi_expr_file]`

## Test Harness Notes
Running the test harness runs the generator on each `query<i>_phi.txt` file and compares it to the output of its corresponding `query<i>_sql.txt`. For each pair, it outputs the output of the generated code, then the SQL code, then sorts both tables and prints them both again, so for each pair it prints exactly four tables to stdout and then tells you if the output tables are equivalent.