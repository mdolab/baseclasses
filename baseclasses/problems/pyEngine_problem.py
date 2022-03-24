"""
pyEngine_problem
"""

# =============================================================================
# Imports
# =============================================================================
from .pyAero_problem import AeroProblem


class EngineProblem(AeroProblem):
    """
    The EngineProblem class inherits from the AeroProblem class so that
    aerodynamic solvers (AeroSolver) and engine models (EngineModelSMT) can
    reference the same flight condition without needing to define redundant
    information. The EngineProblem layer simply adds a few possible design
    variables and handles some stuff with derivatives.

    Parameters
    ----------
    name : str
        Name of this Engine problem.

    evalFuncs : iterable object containing strings
        The names of the functions the user wants evaluated for this
        engineProblem.

    throttle : float
        Initial value for throttle variable

    ISA : float
        Initial value for ISA temperature variable"""

    def __init__(self, name, throttle=1.0, ISA=0.0, **kwargs):
        # Initialize AeroProblem
        super().__init__(name, **kwargs)

        # Set initial throttle or ISA
        self.throttle = throttle
        self.ISA = ISA

        # Update AeroProblem variable sets with possible engine variables
        newVars = ["throttle", "ISA"]
        self.allVarFuncs += newVars
        self.possibleDVs.update(newVars)
        self.possibleFunctions.update(newVars)
