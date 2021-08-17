"""
pyFieldPerformance_problem
"""

# =============================================================================
# Imports
# =============================================================================
import warnings
from .ICAOAtmosphere import ICAOAtmosphere
from .FluidProperties import FluidProperties
from ..utils import CaseInsensitiveDict, Error


class FieldPerformanceProblem:
    """
    The main purpose of this class is to represent all relevant
    information for a single field performance analysis. This includes
    an internal instance of the atmospheric calculation for computing
    density.

    All parameters are optional except for the `name` argument which
    is required. All of the parameters listed below can be acessed and
    set directly after class creation by calling::

    <fieldPerformanceProblem>.<variable> = <value>

    Parameters
    ----------
    name : str
        Name of this aerodynamic problem.
    units : str
        'english' - input/output in English units: pounds, feet, Rankine etc.
        'metric' - input/output in metric units: Newtons, meters, Celsius etc.
    funcs : iteratble object containing strings
        The names of the functions the user wants evaluated with this
        aeroProblem.
    altitude : float
        The altitude of the airport.
    Area : float
        Reference area of the wing.
    BPR : float
        bypass ratio of the engine
    CD0 : float
        Zero-lift drag coefficient of airplane.
    CD0_LG : float
        Zero-lift drag increment due to landing gear extended.
    CD0_HL : float
        Zero-lift drag increment due to flap deflection.
    CLmax : float
        Maximum lift coefficient of the airplane in high-lift configuration.
    e : float
        Span efficiency
    runwayFrictionCoef : float
        Friction coefficient between tires and ground, accounting for braking.
    span : float
        Total wingspan

    ** Note ** Thrust and weight should be specified in terms of force.
    T_VA : float
        Idle thrust during approach. <force>
    T_VF : float
        Idle thrust during flare before landing. <force>
    T_VTD : float
        Idle thrust at touchdown. <force>
    T_VG : float
        The thrust available at 0.7*VLOF on the ground. <force>
    T_VT : float
        Thrust available during transition (at V = 1.15*VS). <force>
    T_TOS : float
        Static thrust at takeoff (V = 0). <force>
    T_V2 : float
        Thrust at takeoff safety speed, all engines operating (V = 1.2*VS). <force>
    T_OEI : float
        Thrust at takeoff safety speed, one engine operating (V = 1.2*VS). <force>
    TOW : float
        Takeoff gross weight. <force>

    ** Note ** TSFC should be specified in terms of mass / time / force.
    TSFC_VA : float
        Thrust-specific fuel consumption with engine in idle during approach.
    TSFC_VF : float
        Thrust-specific fuel consumption with engine in idle during flare.
    TSFC_VTD : float
        Thrust-specific fuel consumption with engine in idle at touchdown.
    TSFC_VG : float
        Thrust-specific fuel consumption at 0.7*VLOF on the ground.
    TSFC_VT : float
        Thrust-specific fuel consumption at V = 1.15*VS
    WingHeight: float
        Height of the wing above the ground.

    Examples
    --------
    FP = FieldPerformance('gulfstream')
    fpp = FieldPerformanceProblem(name='fpp1',TOW=W,span=b,CLmax=CLmax,
                                  WingHeight=5.6,runwayFrictionCoef=0.04,Area=S,
                                  CD0=0.015,CD0_LG=0.0177,CD0_HL=0,
                                  T_VG=T_VG,T_VT=T_VT,TSFC_VG=TSFC,TSFC_VT=TSFC,
                                  altitude=0,units='english')
    fpp.addDV('TOW')
    funcs = {}
    funcsSens = {}
    FP.evalFunctions(fpp, funcs, evalFuncs=['TOFL','TOFT','TOFF'])
    FP.evalFunctionsSens(fpp, funcsSens, evalFuncs=['TOFL','TOFT','TOFF'])
    print funcs, funcsSens
    """

    def __init__(self, name, units, **kwargs):
        # Always have to have the name
        self.name = name
        # These are the parameters that can be simply set directly in
        # the class.
        paras = {
            "TOW",
            "span",
            "WingHeight",
            "Area",
            "runwayFrictionCoef",
            "altitude",
            "CLmax",
            "CD0",
            "CD0_LG",
            "CD0_HL",
            "e",
            "T_VG",
            "T_VT",
            "T_V2",
            "T_TOS",
            "T_OEI",
            "T_VA",
            "T_VF",
            "T_VTD",
            "TSFC_VG",
            "TSFC_VT",
            "TSFC_VA",
            "TSFC_VF",
            "TSFC_VTD",
            "BPR",
        }

        # By default everything is None
        for para in paras:
            setattr(self, para, None)

        # Check if we have english units:
        self.units = units.lower()
        englishUnits = False
        if self.units == "english":
            englishUnits = True

        # Set or create a empty dictionary for additional solver
        # options
        self.solverOptions = CaseInsensitiveDict({})
        if "solverOptions" in kwargs:
            for key in kwargs["solverOptions"]:
                self.solverOptions[key] = kwargs["solverOptions"][key]

        # Any matching key from kwargs that is in 'paras'
        for key in kwargs:
            if key in paras:
                setattr(self, key, kwargs[key])

        # Check for function list:
        self.evalFuncs = set()
        if "evalFuncs" in kwargs:
            self.evalFuncs = set(kwargs["evalFuncs"])
        if "funcs" in kwargs:
            warnings.warn("funcs should **not** be an argument. Use 'evalFuncs' instead.")
            self.evalFuncs = set(kwargs["funcs"])

        # Specify the set of possible design variables:
        varFuncs = [
            "TOW",
            "span",
            "Area",
            "WingHeight",
            "CD0",
            "CD0_LG",
            "CD0_HL",
            "e",
            "CLmax",
            "T_VG",
            "T_VT",
            "T_V2",
            "T_TOS",
            "T_OEI",
            "T_VA",
            "T_VF",
            "T_VTD",
            "TSFC_VG",
            "TSFC_VT",
            "TSFC_VA",
            "TSFC_VF",
            "TSFC_VTD",
            "BPR",
        ]

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

        # create an internal instance of the atmosphere to use
        self.atm = ICAOAtmosphere(englishUnits=englishUnits)

        # Check if 'R' is given....if not we assume air
        fluidprops = FluidProperties(englishUnits=englishUnits, **kwargs)

        # compute the densities for this problem
        # Sea level
        P, T = self.atm(0.0)
        self.rho_SL = P / (fluidprops.R * T)

        # Actual altitude
        P, T = self.atm(self.altitude)
        self.rho = P / (fluidprops.R * T)

    def addDV(self, key, value=None, lower=None, upper=None, scale=1.0, name=None, dvOffset=0.0, addToPyOpt=True):
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
        >>> fpp.addDV('TOW', value=250000, lower=0.0, upper=300000.0, scale=0.1)
        """

        # First check if we are allowed to add the DV:
        if key not in self.possibleDVs:
            raise Error(
                "The DV '%s' could not be added. Potential DVs MUST "
                "be specified when the fieldPerformanceProblem class is created. "
                "For example, if you want TOW as a design variable "
                "(...,TOW=value, ...) must be given. The list of "
                "possible DVs are: %s." % (key, repr(self.possibleDVs))
            )

        if name is None:
            dvName = key + "_%s" % self.name
        else:
            dvName = name

        if value is None:
            value = getattr(self, key)

        self.DVs[dvName] = fieldPerformanceDV(key, value, lower, upper, scale, dvOffset, addToPyOpt)
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
                setattr(self, key, x[dvName] + self.DVs[dvName].dvOffset)
                try:  # To set in the DV as well if the DV exists:
                    self.DVs[dvName].value = x[dvName]
                except:  # noqa
                    pass  # DV doesn't exist

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
                optProb.addVar(
                    key, "c", value=dv.value, lower=dv.lower, upper=dv.upper, scale=dv.scale, offset=dv.dvOffset
                )

    def __getitem__(self, key):

        return self.funcNames[key]

    def __str__(self):
        for key, val in self.__dict__.items():
            print(f"{key:20} : {val:<16}")

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


class fieldPerformanceDV:
    """
    A container storing information regarding an 'fieldPerformance' variable.
    """

    def __init__(self, key, value, lower, upper, scale, dvOffset, addToPyOpt):
        self.key = key
        self.value = value
        self.lower = lower
        self.upper = upper
        self.scale = scale
        self.dvOffset = dvOffset
        self.addToPyOpt = addToPyOpt
