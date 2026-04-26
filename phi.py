"""
Name: Nicolas Banatt
CWID: 20014265
"""

class Phi:
    """
    Phi operator implementation
    """

    def __init__(self, S, n, V, F, o, G):
        """
        Creates an instance of a Phi operator
        """
        self.S = S
        self.n = n
        self.V = V
        self.F = F
        self.o = o
        self.G = G
    
    def __repr__(self):
        """
        Override for debug printing purposes
        """
        return f"Phi(S={self.S}, n={self.n}, V={self.V}, F={self.F}, o={self.o}, G='{self.G}')"