"""
Team members: Nicolas Banatt CWID(20014265), Aidan Cancelliere CWID(20026351)

Generates a _generated.py file that outputs the result of a user's EMF query,
either from a file or from manual keyboard input.

To compute the average, this program will spawn two new "sum" and "count" aggregates
to facilitate computation, unless they already exist.
Ex. avg_1_quant -> sum_1_quant, count_1_quant
"""

import subprocess
import sys
import re

import input_handler as InputHandler
from phi import Phi

DEBUG = False

sales_schema = {
    "cust": "str",
    "prod": "str",
    "day": "int",
    "month": "int",
    "year": "int",
    "state": "str",
    "quant": "int",
    "date": "str"
}

def indent(code: str, level: int = 1, spaces: int = 4) -> str:
    """
    Facilitates code generation by handling indenting of code
    Uses spaces instead of tabs for visual consistency (4 spaces ~= 1 tab)
    Level refers to how many levels of indentation
    """
    prefix = " " * (level * spaces)
    return "\n".join(prefix + line if line.strip() else line for line in code.splitlines())

def mf_struct(i: str, attr: str) -> str:
    """
    Generates python code to access the attribute at the ith element of the mf_struct.
    """
    return f"mf_struct[{i}].{attr}"

def mf_entry_proj(entry: str, attr: str) -> str:
    """
    Generates python code to access an attribute of an entry in the mf_struct.
    """
    return f"{entry}.{attr}"

def row_proj(row_name: str, attr: str) -> str:
    """
    Generates python code to access an attribute of a tuple / row.
    """
    return f"{row_name}['{attr}']"

def generate_code_from_pred_operand(i: int, op: str, row_name: str) -> str:
    """
    Generates python code snippet from a single predicate operand.
    
    Ex. 1.state -> row['state']
        cust    -> mf_struct[i].cust
        'NY'    -> 'NY'
        2020    -> 2020
    """
    op = op.strip()

    # If operand is a string constant, leave it unchanged Ex: 'NY'
    if op.startswith("'") and op.endswith("'"):
        return op

    # If operand is a number, leave it unchanged Ex: 2020
    if op.isdigit():
        return op

    # If operand is a grouping variable attribute (Ex: 1.state), convert it into the current row lookup
    if "." in op:
        gv, attr = op.split(".")
        if gv.isdigit():
            return row_proj(row_name, attr)

    # If operand is a grouping attribute (Ex: cust), compare against the mf_struct entry
    if op in sales_schema:
        return mf_struct("i", op)

    return op

def generate_code_from_pred(i: int, phi: Phi, mf_index_name: str, row_name: str) -> str:
    """
    Generates python code snippet from a grouping variable predicate input by the user.

    Ex. input: "1.product=product and 1.quant > avg_quant"
        output: "row['product'] == mf_struct[i].product and row['quant'] > mf_struct[i].avg_quant"
    """
    # Grouping variable 0 is the "group by" group, not input by user
    if i == 0:
        # Match the current row to the current mf_struct group
        # Ex: row['cust'] == mf_struct[i].cust
        group_match = " and ".join([
            f"{row_proj(row_name, attr)} == {mf_struct(mf_index_name, attr)}"
            for attr in phi.V
        ])
        return group_match

    # Get the condition for this grouping variable
    # sigma[0] is for grouping variable 1
    pred = phi.sigma[i - 1]

    # Fix SQL not-equal operator: SQL <> becomes Python !=
    pred = pred.replace("<>", "!=")

    # Replace SQL = with Python ==
    pred = re.sub(r"(?<![<>=!])=(?!=)", "==", pred)

    # Replace grouping variable references
    # Ex: 1.state -> row['state']
    for attr in sales_schema:
        pred = pred.replace(f"{i}.{attr}", row_proj(row_name, attr))

    # Replace grouping attributes and aggregates with mf_struct references
    # Ex: cust -> mf_struct[i].cust
    for attr in phi.V + phi.F:
        pred = re.sub(rf"\b{attr}\b", mf_struct(mf_index_name, attr), pred)

    return pred

def generate_having_condition(phi: Phi, mf_entry_name: str) -> str:
    """
    Generates python code snippet for "having" condition G

    Ex. sum_1_quant = 2 * sum_2_quant -> entry.sum_1_quant == 2 * entry.sum_2_quant
    """
    pred = phi.G

    # Fix SQL not-equal operator: SQL <> becomes Python !=
    pred = pred.replace("<>", "!=")

    # Replace SQL = with Python ==
    pred = re.sub(r"(?<![<>=!])=(?!=)", "==", pred)

    # Replace select attributes with mf_struct references
    # Ex: cust -> entry.cust
    for attr in phi.S:
        pred = re.sub(rf"\b{attr}\b", mf_entry_proj(mf_entry_name, attr), pred)
    
    return pred

def generate_mf_struct_def(phi: Phi) -> str:
    """
    Generates python code to define the mf_struct.
    """
    # Constructing the mf_struct fields (V + F)
    struct_fields = ""
    for attr in phi.V:
        struct_fields += f"{attr}: {sales_schema[attr]}\n"
    for agg in phi.F:
        struct_fields += f"{agg}: int\n"

    # Code to define the mf_struct
    return f"""
@dataclass(slots=True)
class MfStruct:
{indent(struct_fields)}

mf_struct = []
    """.strip()

def generate_aggr_update_statement(aggr: str, phi: Phi, mf_index_name: str, row_name: str) -> str:
    """
    Generates a statement that updates an aggregate in the mf_struct
    """
    aggr_type = Phi.get_aggr_type(aggr)
    aggr_attr = Phi.get_aggr_attr(aggr)

    mf_val = mf_struct(mf_index_name, aggr)
    row_val = row_proj(row_name, aggr_attr)

    match aggr_type:
        case "sum":
            return f"{mf_val} += {row_val}"
        case "avg":
            # Do nothing. Calculated from sum and count at the end of a scan
            return ""
        case "count":
            return f"{mf_val} += 1"
        case "max":
            return f"if {mf_val} < {row_val}: {mf_val} = {row_val}"
        case _:
            assert False, f"Invalid aggregate type: {aggr_type}"

def generate_code_to_update_aggrs(i: int, phi: Phi, mf_index_name: str, row_name: str) -> str:
    """
    Generates python code to update each aggregate corresponding to grouping variable i
    """
    code = []

    aggrs = phi.get_group_var_aggrs(i)
    for aggr in aggrs:
        statement = generate_aggr_update_statement(aggr, phi, mf_index_name, row_name)
        if statement: code.append(statement)
    code = '\n'.join(code)

    return code.strip()

def generate_helpers(phi: Phi) -> str:
    """
    Generates python helper functions for the generated program.
    """
    # Lookup condition to check if row is in the mf_struct group
    row_is_part_of_group = " and ".join([f"{mf_struct('i', attr)} == {row_proj('cur_row', attr)}" for attr in phi.V])

    # For output to convert mf_struct to table output
    mf_struct_dict = ",\n".join([f"'{attr}': {mf_entry_proj('entry', attr)}" for attr in phi.S])

    return f""" 
def lookup(cur_row):
    '''Search for all indices in the mf_struct that match the current group'''
    for i in range(len(mf_struct)):
        if {row_is_part_of_group}:
            return i
    return -1

def add(cur_row):
    '''Adds a new entry in mf_struct corresponding to a newly found group by attribute value'''
    mf_struct.append(MfStruct({", ".join(
        [f"{attr}={row_proj('cur_row', attr)}" for attr in phi.V] +
        [f"{aggr}={-1 if Phi.get_aggr_type(aggr) == 'max' else 0}" for aggr in phi.F]
    )}))

def output():
    '''Returns only the select attributes of mf_struct'''
    mf_struct_table = [{{
{indent(mf_struct_dict, 2)}
    }} for entry in mf_struct]
    return mf_struct_table

def print_output(table):
    '''Prints final table to stdout'''
    print(tabulate.tabulate(table, headers="keys", tablefmt="psql"))
    """.strip()

def generate_emf_table_scan(i: int, mf_index_name: str, row_name: str, pred_code: str, update_aggr_code: str) -> str:
    """
    Generates python code to perform one scan of the table to compute aggregates for grouping variable i
    """
    return f"""
# Table scan for grouping variable {i}
for {row_name} in table:
    for {mf_index_name} in range(len(mf_struct)):
        if {pred_code}:
{indent(update_aggr_code, 3)}
    """.strip()

def generate_calculate_avgs(i: int, phi: Phi, mf_index_name: str) -> str:
    """
    Generates python code to update averages in the entire mf_struct corresponding to grouping variable i
    """
    # Get all 'avg' attributes in the row to update
    avgs = phi.get_group_var_avgs(i)

    avg_updates = []
    # Update avgs in a row according to previously calculated sum and count
    for avg in avgs:
        sum = mf_struct(mf_index_name, Phi.change_aggr_type(avg, 'sum'))
        count = mf_struct(mf_index_name, Phi.change_aggr_type(avg, 'count'))
        # TODO: Don't need to calculate this every time
        avg_updates.append(f"{mf_struct(mf_index_name, avg)} = {sum} / {count}")
    avg_updates = '\n'.join(avg_updates)

    return f"""
# Compute averages for grouping variable {i} at end of scan
for {mf_index_name} in range(len(mf_struct)):
{indent(avg_updates)}
    """.strip()

def generate_body(phi: Phi) -> str:
    """
    Generates program logic within the main function.
    """
    # Code for first table scan to populate mf_struct
    populate_mf_struct = """
# Table scan 0: Populate mf_struct with distinct values of grouping attributes
for row in table:
    pos = lookup(row)
    if pos == -1:
        add(row)
    """.strip()

    mf_index_name = "i"
    row_name = "cur_row"
    group_vars = range(phi.n + 1)

    # List of python code condition snippets for each grouping variable (including grouping variable 0)
    group_var_preds_code = [
        generate_code_from_pred(i, phi, mf_index_name, row_name) 
        for i in group_vars
    ]
    # List of python code snippets to update aggregates corresponding to each grouping variable
    group_var_update_aggrs_code = [
        generate_code_to_update_aggrs(i, phi, mf_index_name, row_name) 
        for i in group_vars
    ]

    emf_algorithm = []
    for i in group_vars:
        # Don't scan table if there are no aggregates to compute for this grouping variable
        if not phi.get_group_var_aggrs(i): continue
        # At the end of a table scan, compute all necessary averages for this grouping variable
        table_scan = generate_emf_table_scan(
            i, mf_index_name, row_name, group_var_preds_code[i], group_var_update_aggrs_code[i]
        )
        compute_avgs = generate_calculate_avgs(i, phi, mf_index_name) if phi.gv_computes_avg(i) else ""

        # Scan over table to update aggregates for this grouping variable
        emf_algorithm.append(f"""
{table_scan}
{compute_avgs}
        """.strip())
    # Join all scans
    emf_algorithm = '\n\n\n'.join(emf_algorithm)

    # Having condition
    having = f"""
# Having condition
mf_struct[:] = list(filter(
    lambda entry: {generate_having_condition(phi, 'entry')}, 
    mf_struct
))
""".strip() if phi.G else ""

    return f"""
{populate_mf_struct}

{emf_algorithm}

{having}
    """.strip()

def generate_program(mf_struct: str, helpers: str, body: str) -> str:
    """
    Generates final program code. Inserts important sections into bare minimum skeleton.
    """
    return f"""
import os
import psycopg2
import psycopg2.extras
import tabulate
from dotenv import load_dotenv
from dataclasses import dataclass

# DO NOT EDIT THIS FILE, IT IS GENERATED BY generator.py

{mf_struct}

{helpers}

def query():
    load_dotenv()

    user = os.getenv('USER')
    password = os.getenv('PASSWORD')
    dbname = os.getenv('DBNAME')

    conn = psycopg2.connect("dbname="+dbname+" user="+user+" password="+password,
                            cursor_factory=psycopg2.extras.DictCursor)
    cur = conn.cursor()
    cur.execute("SELECT * FROM sales")
    
    table = cur.fetchall()

{indent(body)}

    return output()

def main():
    table = query()
    print_output(table)
    
if "__main__" == __name__:
    main()
    """.strip()

def file_name() -> str:
    '''Returns name of if there is a command line argument'''
    return sys.argv[1] if len(sys.argv) >= 2 else ""

def main(file_name):
    """
    This is the generator code. It should take in the MF structure and generate the code
    needed to run the query. That generated code should be saved to a 
    file (e.g. _generated.py) and then run.
    """
    phi: Phi = InputHandler.get_phi_expr(file_name)
    if DEBUG: print(phi)
    
    mf_struct = generate_mf_struct_def(phi)                # mf_struct definition
    helpers = generate_helpers(phi)                        # Database helper functions
    body = generate_body(phi)                              # Program logic
    program = generate_program(mf_struct, helpers, body)   # Whole program

    # Collapse multiple newlines to a maximum of three
    # program = re.sub(r"\n{4,}", "\n\n\n", program)

    # Write the generated code to a file
    open("_generated.py", "w").write(program)
    # Execute the generated code using the same python.exe running this script
    subprocess.run([sys.executable, "_generated.py"])


if "__main__" == __name__:
    main(file_name())
