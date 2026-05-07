"""
Team members: Nicolas Banatt CWID(20014265), Aidan Cancelliere CWID()

Implementation of the phi operator.
"""

class Phi:
    '''Phi operator implementation'''

    def __init__(self, S: list[str], n: int, V: list[str], F: list[str], sigma: list[str], G: str):
        '''Creates an instance of a Phi expression'''
        self.S = S
        self.n = n
        self.V = V
        self.F = F
        self.sigma = sigma
        self.G = G
    
    def __repr__(self):
        '''Override for debug printing purposes'''
        return f"Phi(S={self.S}, n={self.n}, V={self.V}, F={self.F}, sigma={self.sigma}, G='{self.G}')"