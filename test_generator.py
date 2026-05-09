from generator import main as generator
import _generated

from sql import query as sql

import sys
import tabulate
import importlib

examples = {
    'example_inputs/query1_phi.txt': 'example_inputs/query1_sql.txt',
    'example_inputs/query2_phi.txt': 'example_inputs/query2_sql.txt',
}

def sort_table(table):
    return sorted(table, key=lambda d: sorted(d.items()))

def test_generator():
    # Generate the file
    phi_expr_file = sys.argv[1]
    generator(phi_expr_file)

    # Just changed the file, so reload the module
    importlib.reload(_generated)
    
    # Read corresponding sql query
    query = open(examples[phi_expr_file]).read()

    # Sort tables and convert to strings
    phi_query_result = tabulate.tabulate(sort_table(_generated.query()), headers="keys", tablefmt="psql")
    sql_query_result = tabulate.tabulate(sort_table(sql(query)), headers="keys", tablefmt="psql")

    print("\n\n")

    print(phi_query_result, '\n', sql_query_result)

    # Compare the output of your generated code to the output of the actual SQL query
    # Note: This only works for standard queries, not ESQL queries.
    assert phi_query_result == sql_query_result, "Not equal!"
    print("They are equal!")

def main():
    test_generator()

if __name__ == "__main__":
    main()