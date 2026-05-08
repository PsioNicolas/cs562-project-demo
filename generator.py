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
import re

from input_handler import InputHandler
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
    Converts one operand from a SQL-style condition into Python code.

    Examples:
        1.state -> row['state']
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
            return row_proj("cur_row", attr)

    # If operand is a grouping attribute (Ex: cust), compare against the mf_struct entry
    if op in sales_schema:
        return mf_struct("i", op)

    # Otherwise return it as-is
    return op
    

def generate_code_from_pred(i: int, phi: Phi, mf_index_name: str, row_name: str) -> str:
    """
    Generates python code snippet from a grouping variable predicate input by the user.

    Ex. input: "1.product=product and 1.quant > avg_quant"
        output: "mf_struct[i].product == cur_row['product'] and cur_row['quant'] > mf_struct[i].avg_quant"
    """

    # Match the current row to the current mf_struct group
    # Ex: mf_struct[i].cust == cur_row['cust']
    group_match = " and ".join([
        f"{mf_struct(mf_index_name, attr)} == {row_proj(row_name, attr)}"
        for attr in phi.V
    ])

    # Grouping variable 0 only needs the group match
    if i == 0:
        return group_match

    # Get the condition for this grouping variable
    # sigma[0] is for grouping variable 1
    pred = phi.sigma[i - 1].strip()

    # Convert smart quotes into normal quotes
    pred = pred.replace("‘", "'")
    pred = pred.replace("’", "'")

    # Fix SQL not-equal operator: SQL <> becomes Python !=
    pred = pred.replace("<>", "!=")

    # Replace SQL = with Python ==
    pred = re.sub(r"(?<![<>=!])=(?!=)", "==", pred)

    # Replace grouping variable references
    # Ex: 1.state -> cur_row['state']
    for attr in sales_schema:
        pred = pred.replace(f"{i}.{attr}", row_proj(row_name, attr))

    # Replace grouping attributes with mf_struct references
    # Ex: cust -> mf_struct[i].cust
    for attr in phi.V:
        pred = re.sub(rf"\b{attr}\b", mf_struct(mf_index_name, attr), pred)

    # Final condition must match the group and satisfy the predicate
    return f"{group_match} and {pred}"

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
            # TODO: Refactor this to not check this at the statement level
            return f"if {mf_val} < {row_val}: {mf_val} = {row_val}"
        case _:
            assert False, f"Invalid aggregate type: {aggr_type}"



def generate_avg_code(phi: Phi) -> str:
    """
    Generates code to compute avg aggregates after scans.
    avg_x = sum_x / count_x
    """
    lines = []

    for aggr in phi.F:
        if Phi.get_aggr_type(aggr) == "avg":
            attr = Phi.get_aggr_attr(aggr)

            # avg_quant -> sum_quant, count_quant
            if aggr.count("_") == 1:
                sum_aggr = f"sum_{attr}"
                count_aggr = f"count_{attr}"
            else:
                gv = aggr.split("_")[1]
                sum_aggr = f"sum_{gv}_{attr}"
                count_aggr = f"count_{gv}_{attr}"

            lines.append(f"if entry.{count_aggr} != 0:")
            lines.append(f"    entry.{aggr} = entry.{sum_aggr} / entry.{count_aggr}")

    if not lines:
        return ""

    return "for entry in mf_struct:\n" + indent("\n".join(lines), 1)


def generate_code_to_update_aggrs(i: int, phi: Phi, mf_index_name: str, row_name: str) -> str:
    """
    Generates list of python statements to update each aggregate corresponding to grouping variable i
    """
    updates_statements = []

    aggrs = phi.get_group_var_aggrs(i)
    for aggr in aggrs:
        updates_statements.append(generate_aggr_update_statement(aggr, phi, mf_index_name, row_name))

    return updates_statements

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
    mf_struct_table = [({', '.join([f"entry.{attr}" for attr in phi.S])}) for entry in mf_struct]
    print(tabulate.tabulate(mf_struct_table, headers={phi.S}, tablefmt="psql"))
    """

def generate_body(phi: Phi) -> str:
    """
    Generates program logic within the main function.
    """

    # First scan: build mf_struct with unique grouping attribute values
    populate_mf_struct = """
# Table scan 0: Populate mf_struct with distinct values of grouping attributes
for row in table:
    pos = lookup(row)
    if pos == -1:
        add(row)
"""

    mf_index_name = "i"
    row_name = "cur_row"

    # Generate all grouping variable conditions
    group_var_preds_code = [
        generate_code_from_pred(i, phi, mf_index_name, row_name)
        for i in range(phi.n + 1)
    ]

    # Generate all aggregate update statements
    group_var_update_aggrs_code = [
        generate_code_to_update_aggrs(i, phi, mf_index_name, row_name)
        for i in range(phi.n + 1)
    ]

    emf_algorithm = ""

    # Generate scans for grouping variables 1..n
    start = 0 if phi.n == 0 else 1

    for i in range(start, phi.n + 1):

        # Join update statements into actual executable lines
        update_code = "\n".join(group_var_update_aggrs_code[i])

        emf_algorithm += f"""
# Table scan {i} for grouping variable {i}
for {row_name} in table:
    for {mf_index_name} in range(len(mf_struct)):
        if {group_var_preds_code[i]}:
{indent(update_code, 3)}
"""

    avg_code = generate_avg_code(phi)

    return f"""
for row in cur:
    table.append(row)
{populate_mf_struct}
{emf_algorithm}
{avg_code}
"""

def generate_program(mf_struct: str, helpers: str, body: str) -> str:
    """
    Generates final program code. Inserts important sections into bare minimum skeleton.
    """
    return f"""import os
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
