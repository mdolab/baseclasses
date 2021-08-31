"""
pyAero_problem
"""

# =============================================================================
# Imports
# =============================================================================
import numpy
import warnings
from .ICAOAtmosphere import ICAOAtmosphere
from .FluidProperties import FluidProperties
from ..utils import CaseInsensitiveDict, Error


class AeroProblem(FluidProperties):
    """
    The main purpose of this class is to represent all relevant
    information for a single aerodynamic analysis. This will
    include the thermodynamic parameters defining the flow
    condition and the reference quantities for normalization.

    There are several different ways of specifying thermodynamic
    conditions. The following describes several of the possible
    ways and the appropriate situations.

    'mach' + 'altitude'
        This is the preferred method for specifying flight conditions.
        The 1976 standard atmosphere is used to generate all thermodynamic properties in a consistent manner.
        The resulting Reynolds number depends on the scale of the mesh.
        This is suitable for all aerodynamic analysis codes, including aerostructural analysis.

    'mach' + 'reynolds' + 'reynoldsLength' + 'T':
        Used to precisely match Reynolds numbers.
        Complete thermodynamic state is computed.

    'V' + 'reynolds' + 'reynoldsLength' + 'T':
        Used to precisely match Reynolds numbers for low speed cases.
        Complete thermodynamic state is computed.

    'mach' + 'T' + 'P':
        Any arbitrary temperature and pressure.

    'mach' + 'T' + 'rho':
        Any arbitrary temperature and density.

    'mach' + 'rho' + 'P':
        Any arbitrary density and pressure.

    'V' + 'rho' + 'T'
        Generally for low speed specifications

    'V' + 'rho' + 'P'
        Generally for low speed specifications

    'V' + 'T' + 'P'
        Generally for low speed specifications

    The combinations listed above are the **only** valid combinations
    of arguments that are permitted. Furthermore, since the internal
    processing is based (permanently) on these parameters, it is
    important that the parameters given on initialization are
    sufficient for the required analysis. For example, if only the
    Mach number is given, an error will be raised if the user tries to
    set the 'P' (pressure) variable.

    All parameters are optional except for the `name` argument which
    is required. All of the parameters listed below can be acessed and
    set directly after class creation by calling::

    <aeroProblem>.<variable> = <value>

    An attempt is made internally to maintain consistency of the
    supplied arguments. For example, if the altitude variable is set
    directly, the other thermodynamic properties (rho, P, T, mu, a)
    are updated accordingly.

    Parameters
    ----------
    name : str
        Name of this aerodynamic problem.

    funcs : iteratble object containing strings
        The names of the functions the user wants evaluated with this
        aeroProblem.

    mach : float. Default is 0.0
        Set the Mach number for the simulation

    machRef : float. Default is None
        Sets the reference Mach number for the simulation.

    machGrid : float. Default is None
        Set the Mach number for the grid.

    alpha : float. Default is 0.0
        Set the angle of attack

    beta : float. Default is 0.0
        Set side-slip angle

    altitude : float. Default is 0.0
        Set all thermodynamic parameters from the 1976 standard atmosphere.
        The altitude must be given in meters.

    phat : float. Default is 0.0
        Set the rolling rate coefficient

    qhat : float. Default is 0.0
        Set the pitch rate coefficient

    rhat : float. Default is 0.0
        Set the yawing rate coefficient

    degPol : integer. Default is 0
        Degree of polynomial for prescribed motion. ADflow only

    coefPol : array_like. Default is [0.0]
        Coefficients of polynomial motion. ADflow only

    degFourier : integer. Default is 0
        Degree of Fourier coefficient for prescribed motion. ADflow only

    omegaFourier : float. Default is 0.0
        Fundamental circular frequency for oscillatory motion. ADflow only

    cosCoefFourier : array_like. Default is [0.0]
        Coefficients for cos terms

    sinCoefFourier : array_like. Default is [0.0]
        Coefficients for the sin terms

    P : float.
        Set the ambient pressure

    T : float.
        Set the ambient temperature

    gamma : float. Default is 1.4
        Set the ratio of the specific heats in ideal gas law

    reynolds : float. Default is None
        Set the Reynolds number

    reynoldslength : float. Default is 1.0
        Set the reference length for the Reynolds number calculations

    areaRef : float. Default is 1.0
        Set the reference area used for normalization of lift, drag, etc.

    chordRef : float. Default is 1.0
        Set the reference length used for moment normalization

    spanRef : float. Default is 1.0
        Set reference length for span. Only used for normalization of
        p-derivatives

    xRef : float. Default is 0.0
        Set the x-coordinate location of the center about which moments
        are taken

    yRef : float. Default is 0.0
        Set the y-coordinate location of the center about which moments
        are taken

    zRef : float. Default is 0.0
        Set the z-coordinate location of the center about which moments
        are taken

    momentAxis : iterable object containing floats.
        Default is [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]
        Set the reference axis for non-x/y/z based moment calculations

    R : float
        The gas constant. By default we use air. R=287.05

    englishUnits : bool
        Flag to use all English units: pounds, feet, Rankine etc.

    solverOptions : dict
        A set of solver specific options that temporarily override the solver's
        internal options for this aero problem only. It must contain the name of
        the solver followed by a dictionary of options for that solver. For example
        ``solverOptions={'adflow':{'vis4':0.018}}``. Currently, the only solver
        supported is 'adflow' and must use the specific key 'adflow'.

    Examples
    --------
    >>> # DPW4 Test condition (metric)
    >>> ap = AeroProblem('tunnel_condition', mach=0.85, reynolds=5e6, \
reynoldsLength=275.8*.0254, T=310.93, areaRef=594720*.0254**2, \
chordRef=275.8*.0254, xRef=1325.9*0.0254, zRef=177.95*.0254)
    >>> # DPW4 Flight condition (metric)
    >>> ap = AeroProblem('flight_condition', mach=0.85, altitude=37000*.3048, \
areaRef=594720*.0254**2, chordRef=275.8*.0254, \
xRef=1325.9*0.0254, zRef=177.95*.0254)
    >>> # Onera M6 Test condition (Euler)
    >>> ap = AeroProblem('m6_tunnel', mach=0.8395, areaRef=0.772893541, chordRef=0.64607 \
xRef=0.0, zRef=0.0, alpha=3.06)
    >>> # Onera M6 Test condition (RANS)
    >>> ap = AeroProblem('m6_tunnel', mach=0.8395, reynolds=11.72e6, reynoldsLength=0.64607, \
areaRef=0.772893541, chordRef=0.64607, xRef=0.0, zRef=0.0, alpha=3.06, T=255.56)
                         """

    def __init__(self, name, **kwargs):

        # Set basic fluid properties
        super().__init__(**kwargs)

        # Always have to have the name
        self.name = name

        # These are the parameters that can be simply set directly in
        # the class.
        paras = {
            "alpha",
            "beta",
            "areaRef",
            "chordRef",
            "spanRef",
            "xRef",
            "yRef",
            "zRef",
            "xRot",
            "yRot",
            "zRot",
            "phat",
            "qhat",
            "rhat",
            "momentAxis",
            "degreePol",
            "coefPol",
            "degreeFourier",
            "omegaFourier",
            "cosCoefFourier",
            "sinCoefFourier",
            "machRef",
            "machGrid",
        }

        # By default everything is None
        for para in paras:
            setattr(self, para, None)

        # create an internal instance of the atmosphere to use
        if "altitude" in kwargs:
            self.atm = ICAOAtmosphere(englishUnits=self.englishUnits)

        # Set or create an empty dictionary for additional solver
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

        # we cast the set to a sorted list, so that each proc can loop over in the same order
        self.evalFuncs = sorted(self.evalFuncs)

        # these are the possible input values
        possibleInputStates = {"mach", "V", "P", "T", "rho", "altitude", "reynolds", "reynoldsLength"}

        # turn the kwargs into a set
        keys = set(kwargs.keys())

        # save the initials states
        self.inputs = {}
        for key in keys:
            if key in possibleInputStates:
                self.inputs[key] = kwargs[key]

        # full list of states in the class
        self.fullState = {
            "mach",
            "V",
            "P",
            "T",
            "rho",
            "mu",
            "nu",
            "a",
            "q",
            "altitude",
            "re",
            "reynolds",
            "reynoldsLength",
        }

        # now call the routine to setup the states
        self._setStates(self.inputs)

        # Specify the set of possible design variables:
        self.allVarFuncs = [
            "alpha",
            "beta",
            "areaRef",
            "chordRef",
            "spanRef",
            "xRef",
            "yRef",
            "zRef",
            "xRot",
            "yRot",
            "zRot",
            "momentAxis",
            "phat",
            "qhat",
            "rhat",
            "mach",
            "altitude",
            "P",
            "T",
            "reynolds",
            "reynoldsLength",
        ]

        self.possibleDVs = set()
        for var in self.allVarFuncs:
            if getattr(self, var) is not None:
                self.possibleDVs.add(var)

        BCVarFuncs = ["Pressure", "PressureStagnation", "Temperature", "TemperatureStagnation", "Thrust", "Heat"]
        self.possibleBCDVs = set(BCVarFuncs)

        # Now determine the possible functions. Any possible design
        # variable CAN also be a function (pass through)
        self.possibleFunctions = set(self.possibleDVs)

        # And anything in fullState can be a function:
        for var in self.fullState:
            if getattr(self, var) is not None:
                self.possibleFunctions.add(var)

        # When a solver calls its evalFunctions() it must write the
        # unique name it gives to funcNames.
        self.funcNames = {}

        # Storage of DVs
        self.DVs = {}

        # Storage of BC varible values
        # vars are keyed by (bcVarName, Family)
        self.bcVarData = {}

    def _setStates(self, inputDict):
        """
        Take in a dictionary and set up the full set of states.
        """

        # Now we can do the name matching for the data for the
        # thermodynamic condition. We actually can work backwards from
        # the list given in the doc string.

        for key in self.fullState:
            self.__dict__[key] = None

        keys = set(inputDict.keys())
        inKeys = set(self.inputs.keys())

        # first check that the keys in inputDict are valid
        for key in keys:
            if key in self.inputs.keys():
                pass
            else:
                validKeys = ""
                for vkey in self.inputs:
                    validKeys += vkey + ", "

                raise Error(
                    "Invalid input parameter: %s . Only values initially specifed"
                    " as inputs may be modifed. valid inputs include: %s" % (key, validKeys)
                )
        # now we know our inputs are valid. update self.Input and update states
        for key in inputDict:
            self.inputs[key] = inputDict[key]

        if {"mach", "T", "P"} <= inKeys:
            self.__dict__["mach"] = self.inputs["mach"]
            self.__dict__["T"] = self.inputs["T"]
            self.__dict__["P"] = self.inputs["P"]
            self.__dict__["rho"] = self.P / (self.R * self.T)
            # now calculate remaining states
            self._updateFromM()
        elif {"mach", "T", "rho"} <= inKeys:
            self.__dict__["mach"] = self.inputs["mach"]
            self.__dict__["T"] = self.inputs["T"]
            self.__dict__["rho"] = self.inputs["rho"]
            self.__dict__["P"] = self.rho * self.R * self.T
            # now calculate remaining states
            self._updateFromM()
        elif {"mach", "P", "rho"} <= inKeys:
            self.__dict__["mach"] = self.inputs["mach"]
            self.__dict__["rho"] = self.inputs["rho"]
            self.__dict__["P"] = self.inputs["P"]
            self.__dict__["T"] = self.P / (self.rho * self.R)
            # now calculate remaining states
            self._updateFromM()
        elif {"mach", "reynolds", "reynoldsLength", "T"} <= inKeys:
            self.__dict__["mach"] = self.inputs["mach"]
            self.__dict__["T"] = self.inputs["T"]
            self.__dict__["re"] = self.inputs["reynolds"] / self.inputs["reynoldsLength"]
            self.__dict__["reynolds"] = self.inputs["reynolds"]
            self.__dict__["reynoldsLength"] = self.inputs["reynoldsLength"]
            # now calculate remaining states
            self._updateFromRe()
        elif {"V", "reynolds", "reynoldsLength", "T"} <= inKeys:
            self.__dict__["V"] = self.inputs["V"]
            self.__dict__["T"] = self.inputs["T"]
            self.__dict__["re"] = self.inputs["reynolds"] / self.inputs["reynoldsLength"]
            self.__dict__["reynolds"] = self.inputs["reynolds"]
            self.__dict__["reynoldsLength"] = self.inputs["reynoldsLength"]
            # now calculate remaining states
            self._updateFromRe()
        elif {"mach", "altitude"} <= inKeys:
            self.__dict__["mach"] = self.inputs["mach"]
            self.__dict__["altitude"] = self.inputs["altitude"]
            P, T = self.atm(self.inputs["altitude"])
            self.__dict__["T"] = T
            self.__dict__["P"] = P
            self.__dict__["rho"] = self.P / (self.R * self.T)
            self._updateFromM()
        elif {"V", "rho", "T"} <= inKeys:
            self.__dict__["V"] = self.inputs["V"]
            self.__dict__["rho"] = self.inputs["rho"]
            self.__dict__["T"] = self.inputs["T"]
            # calculate pressure
            self.__dict__["P"] = self.rho * self.R * self.T
            self._updateFromV()
        elif {"V", "rho", "P"} <= inKeys:
            self.__dict__["V"] = self.inputs["V"]
            self.__dict__["rho"] = self.inputs["rho"]
            self.__dict__["P"] = self.inputs["P"]
            # start by calculating the T
            self.__dict__["T"] = self.P / (self.rho * self.R)
            self._updateFromV()
        elif {"V", "T", "P"} <= inKeys:
            self.__dict__["V"] = self.inputs["V"]
            self.__dict__["T"] = self.inputs["T"]
            self.__dict__["P"] = self.inputs["P"]
            # start by calculating the T
            self.__dict__["rho"] = self.P / (self.R * self.T)
            self._updateFromV()
        else:
            raise Error(
                "There was not sufficient information to form "
                "an aerodynamic state. See AeroProblem documentation "
                "in for pyAero_problem.py for information on how "
                "to correctly specify the aerodynamic state"
            )

    def setBCVar(self, varName, value, familyName):
        """
        set the value of a BC variable on a specific variable
        """

        self.bcVarData[varName, familyName] = value
        print("update bc", value)

    def addDV(
        self,
        key,
        value=None,
        lower=None,
        upper=None,
        scale=1.0,
        name=None,
        offset=0.0,
        dvOffset=0.0,
        addToPyOpt=True,
        family=None,
        units=None,
    ):
        """
        Add one of the class attributes as an 'aerodynamic' design
        variable. Typical variables are alpha, mach, altitude,
        chordRef, etc. An error will be given if the requested DV is
        not allowed to be added.


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
            aeroProblems to explictly use the same design variable.

        offset : float. Default is 0.0

            Specify a constant offset of the value relative
            to the actual design variable. This is most
            often used when a single aerodynamic variable is used to
            change multiple aeroProblems. For example, if you have
            three aeroProblems for a multiPoint analysis with
            Mach numbers of 0.84, 0.85 and 0.86, and you want all
            three to change by the same amount, you could do this::

              >>> ap1.addDV('mach',..., name='centerMach', offset=-0.01)
              >>> ap2.addDV('mach',..., name='centerMach', offset= 0.00)
              >>> ap3.addDV('mach',..., name='centerMach', offset=+0.01)

            The result is a single design variable driving three
            different Mach numbers.

        dvOffset : float. Default is 0.0
            This is the offset used to give to pyOptSparse. It can be used
            to re-center the value about zero.

        addToPyOpt : bool. Default True.
            Flag specifying if this variable should be added. Normally this
            is True. However, if there are multiple aeroProblems sharing
            the same variable, only one needs to add the variables to pyOpt
            and the others can set this to False.

        units : str or None. Default None
            Physical units of the variable


        Examples
        --------
        >>> # Add alpha variable with typical bounds
        >>> ap.addDV('alpha', value=2.5, lower=0.0, upper=10.0, scale=0.1)
        """

        if (key not in self.allVarFuncs) and (key not in self.possibleBCDVs):
            raise ValueError("%s is not a valid design variable" % key)

        # First check if we are allowed to add the DV:
        elif (key not in self.possibleDVs) and (key in self.allVarFuncs):
            raise Error(
                "The DV '%s' could not be added. Potential DVs MUST "
                "be specified when the aeroProblem class is created. "
                "For example, if you want alpha as a design variable "
                "(...,alpha=value, ...) must be given. The list of "
                "possible DVs are: %s." % (key, repr(self.possibleDVs))
            )
        if key in self.possibleBCDVs:
            if family is None:
                raise Error("The family must be given for BC design variables")

            if name is None:
                dvName = f"{key}_{family}_{self.name}"
            else:
                dvName = name

            if value is None:
                if (key, family) not in self.bcVarData:
                    raise Error("The value must be given or set using the setBCVar routine")
                value = self.bcVarData[key, family]
        else:
            if name is None:
                dvName = key + "_%s" % self.name
            else:
                dvName = name

            if value is None:
                value = getattr(self, key)
            family = None

        self.DVs[dvName] = aeroDV(key, value, lower, upper, scale, offset, dvOffset, addToPyOpt, family, units)

    def updateInternalDVs(self):
        """
        A specialized function that allows for the updating of the
        internally stored DVs. This would be used for, example, if a
        CLsolve is done before the optimization and that value needs
        to be used."""

        for dvName in self.DVs:
            if self.DVs[dvName].family is None:
                self.DVs[dvName].value = getattr(self, self.DVs[dvName].key)

    def setDesignVars(self, x):
        """
        Set the variables in the x-dict for this object.

        Parameters
        ----------
        x : dict
            Dictionary of variables which may or may not contain the
            design variable names this object needs
        """

        for dvName in self.DVs:
            if dvName in x:
                key = self.DVs[dvName].key
                family = self.DVs[dvName].family
                value = x[dvName] + self.DVs[dvName].offset
                if family is None:
                    setattr(self, key, value)
                else:
                    self.bcVarData[key, family] = value

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

        for dvName in self.DVs:
            dv = self.DVs[dvName]
            if dv.addToPyOpt:
                if type(dv.value) == numpy.ndarray:
                    optProb.addVarGroup(
                        dvName,
                        dv.value.size,
                        "c",
                        value=dv.value,
                        lower=dv.lower,
                        upper=dv.upper,
                        scale=dv.scale,
                        offset=dv.dvOffset,
                        units=dv.units,
                    )
                else:
                    optProb.addVar(
                        dvName,
                        "c",
                        value=dv.value,
                        lower=dv.lower,
                        upper=dv.upper,
                        scale=dv.scale,
                        offset=dv.dvOffset,
                        units=dv.units,
                    )

    def __getitem__(self, key):

        return self.funcNames[key]

    def __str__(self):
        output_str = ""
        for key, val in self.__dict__.items():
            output_str += f"{key:20} : {val:<16}\n"
        return output_str

    def evalFunctions(self, funcs, evalFuncs, ignoreMissing=False):
        """
        Evaluate the desired aerodynamic functions. It may seem
        strange that the aeroProblem has 'functions' associated with
        it, but in certain instances, this is the case.

        For an aerodynamic optimization, consider the case when 'mach'
        is a design variable, and the objective is ML/D. We need the
        mach variable explictly in our our objCon function. In this
        case, the 'function' is simply the design variable itself, and
        the derivative of the function with respect the design
        variable is 1.0.

        A more complex example is when 'altitude' is used for an
        aerostructural optimization.  If we use the Breguet range
        equation is used for either the objective or constraints we
        need to know the flight velocity, 'V', which is a non-trivial
        function of the altitude (and Mach number).

        Also, even if 'altitude' and 'mach' are not parameters, this
        function can be used to evaluate the 'V' value for example. In
        this case, 'V' is simply constant and no sensitivties would be
        calculated which is fine.

        Note that the list of available functions depends on how the
        user has initialized the flight condition.

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
                    "One of the functions in 'evalFunctionsSens' was "
                    "not valid. The valid list of functions is: %s." % (repr(self.possibleFunctions))
                )

    def evalFunctionsSens(self, funcsSens, evalFuncs, ignoreMissing=True):
        """
        Evaluate the sensitivity of the desired aerodynamic functions.

        Parameters
        ----------
        funcsSens : dict
            Dictionary into which the function sensitivities are saved
        evalFuncs : iterable object containing strings
            The functions that the user wants evaluated
        """

        # Make sure all the functions have been evaluated.
        tmp = {}
        self.evalFunctions(tmp, evalFuncs)

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

    def _set_aeroDV_val(self, key, value):
        # Find the DV matching this value. This is inefficient, but
        # there are not generally *that* many aero DVs
        for dvName in self.DVs:
            if self.DVs[dvName].key.lower() == key.lower():
                self.DVs[dvName].value

    @property
    def mach(self):
        return self.__dict__["mach"]

    @mach.setter
    def mach(self, value):
        self._setStates({"mach": value})
        self._set_aeroDV_val("mach", value)

    @property
    def T(self):
        return self.__dict__["T"]

    @T.setter
    def T(self, value):
        self._setStates({"T": value})
        self._set_aeroDV_val("T", value)

    @property
    def P(self):
        return self.__dict__["P"]

    @P.setter
    def P(self, value):
        self._setStates({"P": value})
        self._set_aeroDV_val("P", value)

    @property
    def rho(self):
        return self.__dict__["rho"]

    @rho.setter
    def rho(self, value):
        self._setStates({"rho": value})
        self._set_aeroDV_val("rho", value)

    @property
    def re(self):
        return self.__dict__["re"]

    @re.setter
    def re(self, value):
        self._setStates({"re": value})
        self._set_aeroDV_val("re", value)

    @property
    def reynolds(self):
        return self.__dict__["reynolds"]

    @reynolds.setter
    def reynolds(self, value):
        self._setStates({"reynolds": value})
        self._set_aeroDV_val("reynolds", value)

    @property
    def reynoldsLength(self):
        return self.__dict__["reynoldsLength"]

    @reynoldsLength.setter
    def reynoldsLength(self, value):
        self._setStates({"reynoldsLength": value})
        self._set_aeroDV_val("reynoldsLength", value)

    @property
    def altitude(self):
        return self.__dict__["altitude"]

    @altitude.setter
    def altitude(self, value):
        self._setStates({"altitude": value})
        self._set_aeroDV_val("altitude", value)

    # def _update(self):
    #     """
    #     Try to finish the complete state:
    #     """

    #     if self.T is not None:
    #         self.a = numpy.sqrt(self.gamma*self.R*self.T)
    #         if self.englishUnits:
    #             mu = (self.muSuthDim * (
    #                     (self.TSuthDim + self.SSuthDim) / (self.T/1.8 + self.SSuthDim)) *
    #                    (((self.T/1.8)/self.TSuthDim)**1.5))
    #             self.mu = mu / 47.9
    #         else:
    #             self.mu = (self.muSuthDim * (
    #                     (self.TSuthDim + self.SSuthDim) / (self.T + self.SSuthDim)) *
    #                        ((self.T/self.TSuthDim)**1.5))

    #     if self.mach is not None and self.a is not None:
    #         self.V = self.mach * self.a

    #     if self.a is not None and self.V is not None:
    #         self.__dict__['mach'] = self.V/self.a

    #     if  self.P is not None and self.T is not None:
    #         self.__dict__['rho'] = self.P/(self.R*self.T)

    #     if self.rho is not None and self.T is not None:
    #         self.__dict__['P'] = self.rho*self.R*self.T

    #     if self.rho is not None and self.P is not None:
    #         self.__dict__['T'] = self.P /(self.rho*self.R)

    #     if self.mu is not None and self.rho is not None:
    #         self.nu = self.mu / self.rho

    #     if self.rho is not None and self.V is not None:
    #         self.q = 0.5*self.rho*self.V**2

    #     if self.rho is not None and self.V is not None and self.mu is not None:
    #         self.__dict__['re'] = self.rho*self.V/self.mu

    #     if self.re is not None and self.mu is not None and self.V is not None:
    #         self.__dict__['rho'] = self.re*self.mu/self.V

    def _updateFromRe(self):
        """
        update the full set of states from M,T,P
        """
        # calculate the speed of sound
        self.a = numpy.sqrt(self.gamma * self.R * self.T)

        # Update the dynamic viscosity based on T using Sutherland's Law
        self.updateViscosity(self.T)

        # calculate Velocity
        if self.V is None:
            self.V = self.mach * self.a
        else:
            self.__dict__["mach"] = self.V / self.a

        # calculate density
        self.__dict__["rho"] = self.re * self.mu / self.V
        # calculate pressure
        self.__dict__["P"] = self.rho * self.R * self.T

        # calculate kinematic viscosity
        self.nu = self.mu / self.rho

        # calculate dynamic pressure
        self.q = 0.5 * self.rho * self.V ** 2

    def _updateFromM(self):
        """
        update the full set of states from M,T,P, Rho
        """
        # calculate the speed of sound
        self.a = numpy.sqrt(self.gamma * self.R * self.T)

        # Update the dynamic viscosity based on T using Sutherland's Law
        self.updateViscosity(self.T)

        # calculate Velocity
        self.V = self.mach * self.a

        # calulate reynolds per length
        self.__dict__["re"] = self.rho * self.V / self.mu

        # calculate kinematic viscosity
        self.nu = self.mu / self.rho

        # calculate dynamic pressure
        self.q = 0.5 * self.rho * self.V ** 2

    def _updateFromV(self):
        """
        update the full set of states from V,T,P, Rho
        """
        # calculate the speed of sound
        self.a = numpy.sqrt(self.gamma * self.R * self.T)

        # Update the dynamic viscosity based on T using Sutherland's Law
        self.updateViscosity(self.T)

        # calculate kinematic viscosity
        self.nu = self.mu / self.rho

        # calculate dynamic pressure
        self.q = 0.5 * self.rho * self.V ** 2

        # calculate Mach Number
        self.__dict__["mach"] = self.V / self.a

        # calulate reynolds per length
        self.__dict__["re"] = self.rho * self.V / self.mu

    def _getDVSens(self, func):
        """
        Function that computes the derivative of the functions in
        evalFuncs, wrt the design variable key 'key'
        """
        rDict = {}
        h = 1e-40j
        hr = 1e-40
        for dvName in self.DVs:
            key = self.DVs[dvName].key
            family = self.DVs[dvName].family
            if family is None:
                setattr(self, key, getattr(self, key) + h)
                rDict[dvName] = numpy.imag(self.__dict__[func]) / hr
                setattr(self, key, numpy.real(getattr(self, key)))

        return rDict


class aeroDV:
    """
    A container storing information regarding an 'aerodynamic' variable.
    """

    def __init__(self, key, value, lower, upper, scale, offset, dvOffset, addToPyOpt, family, units):
        self.key = key
        self.value = value
        self.lower = lower
        self.upper = upper
        self.scale = scale
        self.offset = offset
        self.dvOffset = offset
        self.addToPyOpt = addToPyOpt
        self.family = family
        self.units = units
