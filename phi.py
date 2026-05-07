"""
Team members: Nicolas Banatt CWID(20014265), Aidan Cancelliere CWID(20026351)

Implementation of the phi operator.
"""

class Phi:
    '''Phi operator implementation'''

    def __init__(self, S: list[str], n: int, V: list[str], F: list[str], sigma: list[str], G: str):
        """
        Creates an instance of a Phi expression

        Will automatically spawn two new implicit "sum" and "count" aggregates
        for each "avg" to facilitate computation, unless they already exist.
        Ex. avg_1_quant -> sum_1_quant, count_1_quant
        """
        new_F = []
        for aggr in F:
            # Safeguard for when a user accidentally enters an aggregate twice
            if aggr not in new_F: new_F.append(aggr)

            gv = Phi.__get_aggr_num(aggr)
            attr = Phi.get_aggr_attr(aggr) 

            # If there's an average, add sum and count aggregates to new list
            if Phi.get_aggr_type(aggr) == 'avg':
                suffix = Phi.___create_aggr_suffix(gv, attr)
                sum_aggr = f"sum_{suffix}"
                count_aggr = f"count_{suffix}"
                # Only add them if they do not exist
                if sum_aggr not in new_F: new_F.append(sum_aggr)
                if count_aggr not in new_F: new_F.append(count_aggr)

        self.S = S
        self.n = n
        self.V = V
        self.F = new_F
        self.sigma = sigma
        self.G = G
    
    def __repr__(self):
        '''Override for debug printing purposes'''
        return f"Phi(S={self.S}, n={self.n}, V={self.V}, F={self.F}, sigma={self.sigma}, G='{self.G}')"

    def get_group_var_aggrs(self, i: int) -> list[str]:
        '''Returns list of strings of aggregates corresponding to grouping variable i'''
        aggrs = []
        for aggr in self.F:
            if i == self.__get_aggr_num(aggr):
                aggrs.append(aggr)
        return aggrs
    
    def gv_computes_avg(self, i: int) -> bool:
        """
        Returns True if grouping variable i has an 'avg' aggregate associated with it
        Ex. i = 0, F = [..., 'avg_quant', ...] -> True
            i = 1, F = [..., 'avg_1_quant', ...] -> True
        """
        return any(
            Phi.get_aggr_type(aggr) == 'avg' and Phi.__get_aggr_num(aggr) == i
            for aggr in self.F
        )
    
    @staticmethod
    def get_aggr_type(aggr: str) -> str:
        """
        Returns the aggregate type, either sum, avg, count, or max
        The type is specified at the beginning of the aggregate string
        Ex. 'sum_1_quant' -> 'sum'
        """
        return aggr.split('_', 1)[0]
    
    @staticmethod
    def get_aggr_attr(aggr: str) -> str:
        """
        Returns the attribute associated with an aggregate
        Ex. 'sum_1_quant' -> 'quant'
        """
        return aggr.split('_')[2]
    
    @staticmethod
    def __get_aggr_num(aggr: str) -> int:
        """
        Returns the grouping variable number associated with an aggregate
        Ex. 'sum_1_quant' -> 1
            'avg_quant' -> 0
        """
        # Get digits from raw aggregate string
        digits = "".join(filter(str.isdigit, aggr))
        # Empty string -> 0
        return int(digits) if digits else 0
    
    @staticmethod
    def ___create_aggr_suffix(i: int, attr: str) -> str:
        """
        Returns the suffix / ending of an aggregate string based on the grouping variable i and the attribute
        Ex. i = 0, attr = 'quant' -> 'quant'
            i = 1, attr = 'quant' -> '1_quant'
        """
        return f"{i}_{attr}" if i != 0 else attr