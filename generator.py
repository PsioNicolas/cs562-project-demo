"""
Team members: Nicolas Banatt CWID(20014265), Aidan Cancelliere CWID(20026351)

Generates a _generated.py file that outputs the result of a user's EMF query,
either from a file or from manual keyboard input.

To compute the average, this program will spawn two new "sum" and "count" aggregates
to facilitate computation, unless they already exist.
Ex. avg_1_quant -> sum_1_quant, count_1_quant
"""

# TODO: Handle "NONE" input cases

import subprocess
import sys

import input_handler as InputHandler
from phi import Phi

DEBUG = True

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

def generate_code_from_pred_operand(i: int, op: str) -> str:
    """
    Generates python code snippet from a single predicate operand.

    Ex. "1.state" -> "row['state']"
        "avg_2_quant -> 
    """
    pass

def generate_code_from_pred(i: int, phi: Phi, mf_index_name: str, row_name: str) -> str:
    """
    Generates python code snippet from a grouping variable predicate input by the user.

    Ex. input: "1.product=product and 1.quant > avg_quant" -> 
        output: "row['product'] == mf_struct[pos].product and row['quant'] > mf_struct[pos].avg_quant"
    """
    # Grouping variable 0
    if i == 0:
        return f"{" and ".join([f"{mf_entry_proj(mf_index_name, attr)} == {row_proj(row_name, attr)}" for attr in phi.V])}"
    return ""

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
    """

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
    code = ""

    aggrs = phi.get_group_var_aggrs(i)
    for aggr in aggrs:
        code += (generate_aggr_update_statement(aggr, phi, mf_index_name, row_name)) + '\n'

    return code

def generate_helpers(phi: Phi) -> str:
    """
    Generates python helper functions for the generated program.
    """
    return f"""
def lookup(cur_row):
    '''Search for all indices in the mf_struct that match the current group'''
    for i in range(len(mf_struct)):
        if {" and ".join([f"{mf_struct('i', attr)} == {row_proj('cur_row', attr)}" for attr in phi.V])}:
            return i
    return -1

def add(cur_row):
    '''Adds a new entry in mf_struct corresponding to a newly found group by attribute value'''
    mf_struct.append(MfStruct({", ".join(
        [f"{attr}={row_proj('cur_row', attr)}" for attr in phi.V] +
        [f"{aggr}={-1 if Phi.get_aggr_type(aggr) == 'max' else 0}" for aggr in phi.F]
    )}))

def output():
    '''Prints only the select attributes of mf_struct to stdout'''
    mf_struct_table = [({', '.join([mf_entry_proj("entry", attr) for attr in phi.S])}) for entry in mf_struct]
    print(tabulate.tabulate(mf_struct_table, headers={phi.S}, tablefmt="psql"))
    """

def generate_emf_table_scan(i: int, mf_index_name: str, row_name: str, pred_code: str, update_aggr_code: str) -> str:
    """
    Generates python code to perform one scan of the table to compute aggregates for grouping variable i
    """
    return f"""
# Table scan {i+1} for grouping variable {i}
for {row_name} in table:
    for {mf_index_name} in range(len(mf_struct)):
        if {pred_code}:
{indent(update_aggr_code, 3)}
    """

def generate_calculate_avgs(i: int, mf_index_name: str) -> str:
    """
    Generates python code to update averages in a single row corresponding to grouping variable i
    """
    return f"""
# Compute averages for grouping variable {i} at end of scan
for {mf_index_name} in range(len(mf_struct)):

    """

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
    """

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
        # At the end of a table scan, compute all necessary averages for this grouping variable
        table_scan = generate_emf_table_scan(
            i, mf_index_name, row_name, group_var_preds_code[i], group_var_update_aggrs_code[i]
        )
        compute_avgs = generate_calculate_avgs(i, mf_index_name) if phi.gv_computes_avg(i) else ""

        # Scan over table to update aggregates for this grouping variable
        emf_algorithm.append(f"""
{table_scan}
{compute_avgs}
        """)
    # Join all scans
    emf_algorithm = '\n'.join(emf_algorithm)

    return f"""
for row in cur:
    table.append(row)
{populate_mf_struct}
{emf_algorithm}
    """

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
    
    table = []
    for row in cur:
        table.append(row)

{indent(body)}
    
    return tabulate.tabulate(table,
                        headers="keys", tablefmt="psql")

def main():
    query()
    output()
    
if "__main__" == __name__:
    main()
    """

def main():
    """
    This is the generator code. It should take in the MF structure and generate the code
    needed to run the query. That generated code should be saved to a 
    file (e.g. _generated.py) and then run.
    """

    phi: Phi = InputHandler.get_phi_expr()
    if DEBUG: print(phi)
    
    mf_struct = generate_mf_struct_def(phi)                # mf_struct definition
    helpers = generate_helpers(phi)                        # Database helper functions
    body = generate_body(phi)                              # Program logic
    program = generate_program(mf_struct, helpers, body)   # Whole program

    # Write the generated code to a file
    open("_generated.py", "w").write(program)
    # Execute the generated code using the same python.exe running this script
    subprocess.run([sys.executable, "_generated.py"])


if "__main__" == __name__:
    main()
