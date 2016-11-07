from __future__ import print_function
"""
pyFieldPerformance_problem

Developers:
-----------
- Dr. Charles A.(Sandy) Mader (CAM)
- Nicholas Bons   (NB)

History
-------
    v. 0.1    - Initial Implementation of FieldPerformance Problem
"""

# =============================================================================
# Imports
# =============================================================================
import numpy
import warnings
from ICAOAtmosphere import ICAOAtmosphere 

class CaseInsensitiveDict(dict):
    def __setitem__(self, key, value):
        super(CaseInsensitiveDict, self).__setitem__(key.lower(), value)

    def __getitem__(self, key):
        return super(CaseInsensitiveDict, self).__getitem__(key.lower())

class Error(Exception):
    """
    Format the error message in a box to make it clear this
    was a expliclty raised exception.
    """
    def __init__(self, message):
        msg = '\n+'+'-'*78+'+'+'\n' + '| FieldPerformanceProblem Error: '
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
        
class FieldPerformanceProblem(object):
    """
    The main purpose of this class is to represent all relevant
    information for a single field performance analysis. This includes
    the an internal instance of the atmospheric calculation for computing
    density.

    All parameters are optinonal except for the `name` argument which
    is required. All of the parameters listed below can be acessed and
    set directly after class creation by calling::

    <fieldPerformanceProblem>.<variable> = <value>

    Parameters
    ----------
    name : str
        Name of this aerodynamic problem.

    funcs : iteratble object containing strings
        The names of the functions the user wants evaluated with this
        aeroProblem.

    altitude : float. 

    Area : float. 

    Span : float. 

    englishUnits : bool
        Flag to use all English units: pounds, feet, Rankine etc. 

    Examples
    --------
                         """
    def __init__(self, name, **kwargs):
        # Always have to have the name
        self.name = name
        # These are the parameters that can be simply set directly in
        # the class. 
        paras = set(( 'TOGW', 'span','CLmax','WingHeight','runwayFrictionCoef','Area',
                      'CDo','CDo_LG','T_G','T_T','T_SLS','T_Idle','TSFC_G','TSFC_T',
                      'TSFC_Idle', 'TSFC_SLS','altitude'))

        # By default everything is None
        for para in paras:
            setattr(self, para, None)

        # Check if we have english units:
        self.englishUnits = False
        if 'englishUnits' in kwargs:
            self.englishUnits = kwargs['englishUnits']
           
        # create an internal instance of the atmosphere to use
        self.atm = ICAOAtmosphere(englishUnits=self.englishUnits)

        # Set or create a empty dictionary for additional solver
        # options
        self.solverOptions = CaseInsensitiveDict({})
        if 'solverOptions' in kwargs:
            for key in kwargs['solverOptions']:
                self.solverOptions[key]  = kwargs['solverOptions'][key]

        # Any matching key from kwargs that is in 'paras'
        for key in kwargs:
            if key in paras:
                setattr(self, key, kwargs[key])

        # Check for function list:
        self.evalFuncs = set()
        if 'evalFuncs' in kwargs:
            self.evalFuncs = set(kwargs['evalFuncs'])
        if 'funcs' in kwargs:
            warnings.warn("funcs should **not** be an argument. Use 'evalFuncs'"
                          "instead.")
            self.evalFuncs = set(kwargs['funcs'])
                
        # Check if 'R' is given....if not we assume air
        if 'R' in kwargs:
            self.R = kwargs['R']
        else:
            if self.englishUnits:
                self.R = 1716.493 #FIX THIS
            else:
                self.R = 287.870

        # turn the kwargs into a set
        keys = set(kwargs.keys())

 
        # Specify the set of possible design variables:
        varFuncs = [ 'TOGW', 'span','Area','CDo','CDo_LG','T_G','T_T','T_SLS','T_Idle',
                     'TSFC_G','TSFC_T','TSFC_Idle', 'TSFC_SLS']

        self.possibleDVs = set()
        for var in varFuncs:
            if getattr(self, var) is not None:
                self.possibleDVs.add(var)

        # Now determine the possible functions. Any possible design
        # variable CAN also be a function (pass through)
        self.possibleFunctions = set(self.possibleDVs)
              
        # When a solver calls its evalFunctions() it must write the
        # unique name it gives to funcNames. 
        self.funcNames = {}

        # Storage of DVs
        self.DVs = {}
        self.DVNames = {}

        # compute the densities for this problem
        # Sea level
        P, T = self.atm(0.0)
        self.rho_SL = P/(self.R*T)

        #actual altitude
        P, T = self.atm(self.altitude)
        self.rho = P/(self.R*T)

        
    def addDV(self, key, value=None, lower=None, upper=None, scale=1.0,
              name=None, dvOffset=0.0, addToPyOpt=True):
        """
        Add one of the class attributes as a design
        variable.  An error will be given if the requested DV is
        not allowed to be added 
      

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
            fieldPerformanceProblems explictly use the same design variable.
            
        dvOffset : float. Default is 0.0
            This is the offset used to give to pyOptSparse. It can be used
            to re-center the value about zero. 

        addToPyOpt : bool. Default True. 
            Flag specifying if this variable should be added. Normally this 
            is True. However, if there are multiple aeroProblems sharing
            the same variable, only one needs to add the variables to pyOpt
            and the others can set this to False. 

        Examples
        --------
        >>> # Add alpha variable with typical bounds
        >>> fpp.addDV('TOGW', value=250000, lower=0.0, upper=300000.0, scale=0.1)
        """

        # First check if we are allowed to add the DV:
        if key not in self.possibleDVs:
            raise Error("The DV '%s' could not be added. Potential DVs MUST "
                        "be specified when the fieldPerformanceProblem class is created. "
                        "For example, if you want TOGW as a design variable "
                        "(...,TOGW=value, ...) must be given. The list of "
                        "possible DVs are: %s."% (key, repr(self.possibleDVs)))

        if name is None:
            dvName = key + '_%s'% self.name
        else:
            dvName = name

        if value is None:
            value = getattr(self, key)
         
        self.DVs[dvName] = fieldPerformanceDV(key, value, lower, upper, scale, 
                                  dvOffset, addToPyOpt)
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
                try: # To set in the DV as well if the DV exists:
                    self.DVs[dvName].value = x[dvName]
                except:
                    pass # DV doesn't exist

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
            if dv.addToPyOpt:
                optProb.addVar(key, 'c', value=dv.value, lower=dv.lower,
                               upper=dv.upper, scale=dv.scale, 
                               offset=dv.dvOffset)
            
    def __getitem__(self, key):

        return self.funcNames[key]
        
    def __str__(self):
        for key,val in self.__dict__.items():
           print ("{0:20} : {1:<16}".format(key,val))           


    # def _getDVSens(self, func):
    #     """
    #     Function that computes the derivative of the functions in
    #     evalFuncs, wrt the design variable key 'key'
    #     """
    #     rDict = {}
    #     h = 1e-40j; hr = 1e-40
    #     for key in self.DVNames:
    #         setattr(self, key, getattr(self, key) + h)
    #         rDict[self.DVNames[key]] = numpy.imag(self.__dict__[func])/hr
    #         setattr(self, key, numpy.real(getattr(self, key)))

    #     return rDict
    

class fieldPerformanceDV(object):
    """
    A container storing information regarding an 'fieldPerformance' variable.
    """
    
    def __init__(self, key, value, lower, upper, scale, dvOffset, 
                 addToPyOpt):
        self.key = key
        self.value = value
        self.lower = lower
        self.upper = upper
        self.scale = scale
        self.dvOffset = dvOffset
        self.addToPyOpt = addToPyOpt
