"""
pyStrut_problem
"""

# =============================================================================
# Imports
# =============================================================================
from ..utils import Error


class StructProblem:
    """
    The main purpose of this class is to represent all relevant
    information for a structural analysis. This will include
    information defining the loading condition as well as various
    other pieces of information.

    Parameters
    ----------
    name : str
        Name of this structural problem

    loadFile : str
        Filename of the (static) external load file. Should be
        generated from either ADflow or Tripan.

    Examples
    --------
    >>> sp = StructProblem('lc0', loadFile='loads.txt')
    """

    def __init__(self, name, loadFile=None, loadFactor=None, evalFuncs=None):

        # Always have to have the name
        self.name = name

        self.loadFile = loadFile

        # Set defaults for loadFactor and evalFuncs if not supplied
        if loadFactor is None:
            self.loadFactor = 1.0
        else:
            self.loadFactor = loadFactor

        if evalFuncs is None:
            self.evalFuncs = set()
        else:
            self.evalFuncs = set(evalFuncs)

        # we cast the set to a sorted list, so that each proc can loop over in the same order
        self.evalFuncs = sorted(self.evalFuncs)

        # When a solver calls its evalFunctions() it must write the
        # unique name it gives to funcNames.
        self.funcNames = {}
        self.possibleFunctions = set()

        # Storage of DVs (non as of yet)
        self.DVs = {}
        self.DVNames = {}

    def addDV(self, key, value=None, lower=None, upper=None, scale=1.0, name=None):
        """
        No design variable functions yet.

        Parameters
        ----------
        key : str
            Name of variable to add. See above for possible ones

        value : float. Default is None
            Initial value for variable. If not given, current value
            of the attribute will be used.

        lower : float. Default is None
            Optimization lower bound. Default is unbonded.

        upper : float. Default is None
            Optimization upper bound. Default is unbounded.

        scale : float. Default is 1.0
            Set scaling parameter for the optimization to use.

        name : str. Default is None
            Overwrite the default auto-generated name of this variable.
        """

        # First check if we are allowed to add the DV:
        if key not in self.possibleDVs:
            raise Error(
                "The DV '%s' could not be added. \
            The list of possible DVs are: %s."
                % (key, repr(self.possibleDVs))
            )

        if name is None:
            dvName = key + "_%s" % self.name
        else:
            dvName = name

        if value is None:
            raise Error("Value must be given for keyword 'value'.")

        self.DVs[dvName] = structDV(key, value, lower, upper, scale, offset)  # noqa
        self.DVNames[key] = dvName

    def setDesignVars(self, x):
        """
        Set the variables in the x-dict for this object.

        Parameters
        ----------
        x : dict
            Dictionary of variables which may or may not contain the
            design variable names this object needs
        """

        for key in self.DVNames:
            dvName = self.DVNames[key]
            if dvName in x:
                setattr(self, key, x[dvName] + self.DVs[dvName].offset)

    def addVariablesPyOpt(self, optProb):
        """
        Add the current set of variables to the optProb object.

        Parameters
        ----------
        optProb : pyOpt_optimization class
            Optimization problem definition to which variables are added
        """

        for key in self.DVs:
            dv = self.DVs[key]
            optProb.addVar(key, "c", value=dv.value, lower=dv.lower, upper=dv.upper, scale=dv.scale)

    def __getitem__(self, key):

        return self.funcNames[key]

    def evalFunctions(self, funcs, evalFuncs, ignoreMissing=False):
        """
        No current functions

        Parameters
        ----------
        funcs : dict
            Dictionary into which the functions are save
        evalFuncs : iterable object containing strings
            The functions that the user wants evaluated
        """

        if set(evalFuncs) <= self.possibleFunctions:
            # All the functions are ok:
            for f in evalFuncs:
                # Save the key into funcNames
                key = self.name + "_%s" % f
                self.funcNames[f] = key
                funcs[key] = getattr(self, f)
        else:
            if not ignoreMissing:
                raise Error(
                    "One of the functions in 'evalFuncs' was not "
                    "valid. The valid list of functions is: %s." % (repr(self.possibleFunctions))
                )

    def evalFunctionsSens(self, funcsSens, evalFuncs, ignoreMissing=False):
        """
        Evaluate the sensitivity of the desired functions

        Parameters
        ----------
        funcsSens : dict
            Dictionary into which the function sensitivities are saved
        evalFuncs : iterable object containing strings
            The functions that the user wants evaluated
        """

        # Make sure all the functions have been evaluated.
        tmp = {}
        self.evalFunctions(tmp, evalFuncs, ignoreMissing)

        # Check that all functions are ok:
        if set(evalFuncs) <= self.possibleFunctions:
            for f in evalFuncs:
                funcsSens[self.funcNames[f]] = self._getDVSens(f)
        else:
            if not ignoreMissing:
                raise Error(
                    "One of the functions in 'evalFunctionsSens' was "
                    "not valid. The valid list of functions is: %s." % (repr(self.possibleFunctions))
                )


class structDV:
    """
    A container storing information regarding an 'structral problem' variable.
    """

    def __init__(self, key, value, lower, upper, scale, offset):
        self.key = key
        self.value = value
        self.lower = lower
        self.upper = upper
        self.scale = scale
        self.offset = offset
