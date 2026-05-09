from generator import main as generator
from _generated import query as _generated

from sql import query as sql

import sys


def test_generator():
    # Generate the file
    phi_expr_file = sys.argv[1]
    generator(phi_expr_file)
    
    query = "select cust, prod, avg(quant), max(quant) from sales where year=2020 group by cust, prod"

    # Compare the output of your generated code to the output of the actual SQL query
    # Note: This only works for standard queries, not ESQL queries.
    assert sorted(_generated(), key=lambda d: sorted(d.items())) == \
           sorted(sql(query), key=lambda d: sorted(d.items()))
