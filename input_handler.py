"""
Team members: Nicolas Banatt CWID(20014265), Aidan Cancelliere CWID()

Handles the input to get the phi operands.
"""

from phi import Phi

class InputHandler:
    """
    Handles user input
    """

    def get_phi_expr(self) -> Phi:
        """
        Gets phi operands from a file or from manual input
        """
        file_name = input("Enter a file path to a phi expression or press enter to input each operand manually: ").strip()
        
        phi: Phi = None
        try:
            # Read from file if one is provided, else read each operand from keyboard
            if file_name:
                phi = self.__read_phi_from_file(file_name)
            else:
                phi = self.__read_phi_from_manual_input()
        except Exception as e:
            print(f"Error: {e}")
            exit()

        return phi
    
    def __read_phi_from_file(self, file_name: str) -> Phi:
        """
        Gets phi operands from a file
        """
        # Starting state to read first input
        state = 0

        # Functions that correspond with reading each operand 
        # state is the index into this list
        read_operand = [
            self.__read_select_attrs,
            self.__read_num_group_vars,
            self.__read_group_attrs,
            self.__read_aggregates,
            self.__read_group_var_preds,
            self.__read_having
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

    def __read_phi_from_manual_input(self) -> Phi:
        """
        Gets phi operands from manual user keyboard input
        """
        print("Use comma separated lists.")
        S = self.__read_select_attrs(input("Select attributes (S): "))
        n = self.__read_num_group_vars(input("Number of grouping variables (n): "))
        V = self.__read_group_attrs(input("Grouping attributes (V): "))
        F = self.__read_aggregates(input("Vector of aggregates (F): "))
        o = self.__read_group_var_preds(input("Grouping variable predicates: (σ): "))
        G = self.__read_having(input("Having condition: "))
        return Phi(S, n, V, F, o, G)
    
    def __read_select_attrs(self, S: str):
        '''Reads a string S of select attributes separated by commas'''
        return self.__parse_comma_separated_list(S)

    def __read_num_group_vars(self, n: str):
        return int(n)

    def __read_group_attrs(self, V: str):
        '''Reads a string V of group by attributes separated by commas'''
        return self.__parse_comma_separated_list(V)

    def __read_aggregates(self, F: str):
        '''Reads a string F of aggregates separated by commas'''
        return self.__parse_comma_separated_list(F)

    def __read_group_var_preds(self, o: str):
        '''Reads a string o of group variable predicates separated by commas'''
        return self.__parse_comma_separated_list(o)
    
    def __read_having(self, G: str):
        '''Reads a string G of a having clause predicate'''
        return G.strip()

    def __parse_comma_separated_list(self, l: str):
        '''Returns a list from a string l of comma separated items'''
        return [attr.strip() for attr in l.split(',')]