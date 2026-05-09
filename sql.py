"""
Team members: Nicolas Banatt CWID(20014265), Aidan Cancelliere CWID(20026351)

Runs a regular sql query.
"""

import os
import psycopg2
import psycopg2.extras
import tabulate
from dotenv import load_dotenv


def query(query):
    """
    Used for testing standard queries in SQL.
    """
    load_dotenv()

    user = os.getenv('USER')
    password = os.getenv('PASSWORD')
    dbname = os.getenv('DBNAME')

    conn = psycopg2.connect("dbname="+dbname+" user="+user+" password="+password,
                            cursor_factory=psycopg2.extras.DictCursor)
    cur = conn.cursor()

    cur.execute(query)

    output = cur.fetchall()
    print("Normal SQL:")
    print(tabulate.tabulate(output, headers="keys", tablefmt="psql"))

    return output


def main():
    query()


if "__main__" == __name__:
    main()
