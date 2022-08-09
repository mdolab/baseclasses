"""
pyAeroStruct_problem
"""
# ======================================================================
# Imports
# ======================================================================
from .pyAero_problem import AeroProblem
from .pyStruct_problem import StructProblem
from ..utils import Error


class AeroStructProblem:
    """
    The main purpose of this class is to represent all relevant
    information for a coupled aero-structural analysis. To this end,
    it maintains a reference to an AaeroProblem and a StructProblem.

    Parameters
    ----------
    ap : AeroProblem class instance
        An instance of the AeroProblem class defining the aerodynamic
        part of the problem.

    sp : StructProblem class instance
        An instance of the StructProblem class defining the structural
        part of the problem
    """

    def __init__(self, ap, sp, **kwargs):

        if not isinstance(ap, AeroProblem):
            raise Error("The argument for 'ap' was not an AeroProblem!")
        if not isinstance(sp, StructProblem):
            raise Error("The argument for 'sp' was not a StructProblem!")

        self.AP = ap
        self.SP = sp

        # For consistency, we require that the name of the AP and SP
        # are the same:
        if self.AP.name != self.SP.name:
            raise Error(
                "The name of the AeroProblem and the StructProblem \
            used to create this clsss *must* be the same"
            )
        self.name = self.AP.name
        self.funcNames = {}

    def setDesignVars(self, x):
        """
        Set the variables in the x-dict for this object.

        Parameters
        ----------
        x : dict
            Dictionary of variables which may or may not contain the
            design variable names this object needs
        """
        self.AP.setDesignVars(x)
        self.SP.setDesignVars(x)

    def addVariablesPyOpt(self, optProb):
        """
        Add the current set of variables to the optProb object.

        Parameters
        ----------
        optProb : pyOpt_optimization class
            Optimization problem definition to which variables are added
        """
        self.AP.addVariablesPyOpt(optProb)
        self.SP.addVariablesPyOpt(optProb)

    def __getitem__(self, key):

        return self.funcNames[key]

    def evalFunctions(self, funcs, evalFuncs):
        """
        Evaluate functions of the AP and SP.
        """
        self.AP.evalFunctions(funcs, evalFuncs, ignoreMissing=True)
        self.SP.evalFunctions(funcs, evalFuncs, ignoreMissing=True)

    def evalFunctionsSens(self, funcsSens, evalFuncs):
        """
        Evaluate the sensitivity of the desired functions

        Parameters
        ----------
        funcsSens : dict
            Dictionary into which the function sensitivities are saved
        evalFuncs : iterable object containing strings
            The functions that the user wants evaluated
        """
        self.AP.evalFunctionsSens(funcsSens, evalFuncs, ignoreMissing=True)
        self.SP.evalFunctionsSens(funcsSens, evalFuncs, ignoreMissing=True)
