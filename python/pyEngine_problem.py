from __future__ import print_function
"""
pyEngine_problem

Developers:
-----------
- Dr. Gaetan K. W. Kenway (GKWK)

History
-------
    v. 0.1    - Complete overall of AeroProblem (GKWK, 2014)
"""

# =============================================================================
# Imports
# =============================================================================
import numpy

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
        
class EngineProblem(object):
    """
    The main purpose of this class is to represent the all relevant 
    information for a engine anlysis using the EngineModel class. 

    It contains an instance of an aeroProblem that defines the necessary
    aerodynamic conditions. 
    
    Parameters
    ----------
    name : str
        Name of this Engine problem.

    funcs : iteratble object containing strings
        The names of the functions the user wants evaluated for this
        engineProblem.
"""

    def __init__(self, name, AP, throttle=1.0, **kwargs):
        # Always have to have the name
        self.name = name
        self.AP = AP
        self.throttle = throttle
        # When a solver calls its evalFunctions() it must write the
        # unique name it gives to funcNames. 
        self.funcNames = {}
        self.evalFuncs = set()

        if 'evalFuncs' in kwargs:
            self.evalFuncs = set(kwargs['evalFuncs'])

        # Storage of DVs
        self.DVs = {}
        self.DVNames = {}
        self.possibleDVs = set(['throttle'])
        
    def addDV(self, key, value=None, lower=None, upper=None, scale=1.0,
              name=None):
        """
        Add a DV to the engineProblem. An error will be given if the
              requested DV is not allowed to be added 
      
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
            Overwrite the name of this variable. This is typically
            only used when the user wishes to have multiple
            engineProblems to explictly use the same design variable.
        """
        
        # First check if we are allowed to add the DV:
        if key not in self.possibleDVs:
            raise Error("The DV '%s' could not be added. The list of "
                        "possible DVs are: %s."% (key, repr(self.possibleDVs)))

        if name is None:
            dvName = key + '_%s'% self.name
        else:
            dvName = name

        if value is None:
            value = getattr(self, key)
         
        self.DVs[dvName] = EngineDV(key, value, lower, upper, scale)
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
                setattr(self, key, x[dvName])
                try: # To set in the DV as well if the DV exists:
                    self.DVs[dvName].value = x[dvName]
                except:
                    pass
        self.AP.setDesignVars(x)
        
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
            optProb.addVar(key, 'c', value=dv.value, lower=dv.lower,
                           upper=dv.upper, scale=dv.scale)
        self.AP.addVariablesPyOpt(optProb)
        
    def __getitem__(self, key):

        return self.funcNames[key]

    def evalFunctions(self, funcs, evalFuncs, ignoreMissing=False):
        """No functions in the engineProblem itself, but evaluate the AP for
        consistency
        """
        self.AP.evalFunctions(funcs, evalFuncs, ignoreMissing)
    
    def evalFunctionsSens(self, funcsSens, evalFuncs, ignoreMissing=True):
        """
        No functions in the enginProblem itself, but evaluate the AP for
        consistency
        """
        self.AP.evalFunctionsSens(funcsSens, evalFuncs, ignoreMissing)
    
class EngineDV(object):
    """
    A container storing information regarding an 'engine' variable.
    """
    
    def __init__(self, key, value, lower, upper, scale):
        self.key = key
        self.value = value
        self.lower = lower
        self.upper = upper
        self.scale = scale
