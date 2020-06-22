
"""
pyEngine_problem

Developers:
-----------
- Dr. Gaetan K. W. Kenway (GKWK)
- Nicolas Bons (NB)

History
-------
    v. 0.1    - Complete overall of AeroProblem (GKWK, 2014)
    v. 0.2    - Now inherits from AeroProblem (NB, 2017)
"""

# =============================================================================
# Imports
# =============================================================================
import numpy
from baseclasses import AeroProblem

class Error(Exception):
    """
    Format the error message in a box to make it clear this
    was a expliclty raised exception.
    """
    def __init__(self, message):
        msg = '\n+'+'-'*78+'+'+'\n' + '| AeroProblem Error: '
        i = 20
        for word in message.split():
            if len(word) + i + 1 > 78: # Finish line and start new one
                msg += ' '*(78-i)+'|\n| ' + word + ' '
                i = 1 + len(word)+1
            else:
                msg += word + ' '
                i += len(word)+1
        msg += ' '*(78-i) + '|\n' + '+'+'-'*78+'+'+'\n'
        print(msg)
        Exception.__init__(self)

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
        Initial value for ISA temperature variable
"""

    def __init__(self, name, throttle=1.0, ISA=0.0, **kwargs):
        # Initialize AeroProblem
        AeroProblem.__init__(self, name, **kwargs)

        # Set initial throttle or ISA
        self.throttle = throttle
        self.ISA = ISA

        # Update AeroProblem variable sets with possible engine variables
        newVars = ['throttle', 'ISA']
        self.allVarFuncs += newVars
        self.possibleDVs.update(newVars)
        self.possibleFunctions.update(newVars)
