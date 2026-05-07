"""
Team members: Nicolas Banatt CWID(20014265), Aidan Cancelliere CWID(20026351)

Handles the input to get the phi operands.

The operands should be structured as follows:

# SELECT ATTRIBUTE(S):
#   Regular attributes should be their name in the schema (Ex. cust)
#   Aggregates should be structured like <agg>_[<gv>_]<attr>
#       agg: Name of the aggregate (Ex. sum, count, max)
#       gv: Grouping variable associated with the aggregate (Ex. 1, 2, 3...)
#           For normal aggregates / grouping variable 0, leave out the number (Ex. avg_quant)
#       attr: Name of the attribute (Ex. quant)
#   Each attribute should be separated by a comma.
cust, sum_1_quant, sum_2_quant, sum_3_quant

# NUMBER OF GROUPING VARIABLES(n):
#   Integer from [0, inf)
3

# GROUPING ATTRIBUTES(V):
#   Names of attributes from the table separated by commas
cust

# F-VECT([F]):
#   List of aggregates associated with each grouping variable / group.
#   Refer to SELECT ATTRIBUTE(S) to know how to format each one.
avg_quant, max_1_quant

# SELECT CONDITION-VECT([σ]):
#   Ordered list of predicates associated with each grouping variable.
#   When accessing a row value, use <gv>.<attr> (Ex. 1.quant)
#   When specifying aggregates, use the names from the F-VECT
1.quant > avg_quant, 2.quant < max_1_quant, 3.state='CT'

# HAVING_CONDITION(G):
#   Condition for filtering final table.
#   Regular SQL condition, but using aggregate names from F-VECT
sum_1_quant > 2 * sum_2_quant or avg_1_quant > avg_3_quant

For V, F, σ, or G, you can type NONE if they are not part of the expression.
"""

from phi import Phi

class InputHandler:
    """
    Handles user input
    """

    @staticmethod
    def get_phi_expr() -> Phi:
        """
        Gets phi operands from a file or from manual input
        """
        file_name = input("Enter a file path to a phi expression or press enter to input each operand manually: ").strip()
        
        phi: Phi = None
        try:
            # Read from file if one is provided, else read each operand from keyboard
            if file_name:
                phi = InputHandler.__read_phi_from_file(file_name)
            else:
                phi = InputHandler.__read_phi_from_manual_input()
        except Exception as e:
            print(f"Error: {e}")
            exit()

        return phi
    
    @staticmethod
    def __read_phi_from_file(file_name: str) -> Phi:
        """
        Gets phi operands from a file
        """
        # Starting state to read first input
        state = 0

        # Functions that correspond with reading each operand 
        # state is the index into this list
        read_operand = [
            InputHandler.__read_select_attrs,
            InputHandler.__read_num_group_vars,
            InputHandler.__read_group_attrs,
            InputHandler.__read_aggregates,
            InputHandler.__read_group_var_preds,
            InputHandler.__read_having
        ]

        operands = []
        with open(file_name) as f:
            for line in f:
                # Remove leading and trailing whitespace
                line = line.strip()

                # Comments start with '#'
                if line == "" or line[0] == '#':
                    continue

                # Read next operand
                operands.append(read_operand[state](line))

                # Enter new state to process next input
                state += 1
        
        # Unpack list to initialize Phi class
        return Phi(*operands)

    @staticmethod
    def __read_phi_from_manual_input() -> Phi:
        """
        Gets phi operands from manual user keyboard input
        """
        print("Use comma separated lists.")
        S = InputHandler.__read_select_attrs(input("Select attributes (S): "))
        n = InputHandler.__read_num_group_vars(input("Number of grouping variables (n): "))
        V = InputHandler.__read_group_attrs(input("Grouping attributes (V): "))
        F = InputHandler.__read_aggregates(input("Vector of aggregates (F): "))
        sigma = InputHandler.__read_group_var_preds(input("Grouping variable predicates: (σ): "))
        G = InputHandler.__read_having(input("Having condition: "))
        return Phi(S, n, V, F, sigma, G)
    
    @staticmethod
    def __read_select_attrs(S: str):
        '''Reads a string S of select attributes separated by commas'''
        return InputHandler.__parse_comma_separated_list(S)

    @staticmethod
    def __read_num_group_vars(n: str):
        return int(n)

    @staticmethod
    def __read_group_attrs(V: str):
        '''Reads a string V of group by attributes separated by commas'''
        return InputHandler.__parse_comma_separated_list(V)

    @staticmethod
    def __read_aggregates(F: str):
        '''Reads a string F of aggregates separated by commas'''
        return InputHandler.__parse_comma_separated_list(F)

    @staticmethod
    def __read_group_var_preds(sigma: str):
        '''Reads a string sigma of group variable predicates separated by commas'''
        return InputHandler.__parse_comma_separated_list(sigma)
    
    @staticmethod
    def __read_having(G: str):
        '''Reads a string G of a having clause predicate'''
        return G.strip()

    @staticmethod
    def __parse_comma_separated_list(l: str):
        '''Returns a list from a string l of comma separated items'''
        return [attr.strip() for attr in l.split(',')]