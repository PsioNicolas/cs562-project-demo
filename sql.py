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
    # cur.execute("SELECT * FROM sales WHERE quant > 10")
    
    cur.execute(query)

    return cur.fetchall()

    # return tabulate.tabulate([row.values() for row in cur.fetchall()],
    #                          headers=['cust', 'prod', 'avg_quant', 'max_quant'], tablefmt="psql")


def main():
    #print(query())
    query()


if "__main__" == __name__:
    main()
