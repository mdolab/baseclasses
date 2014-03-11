"""
pyAero_problem

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
        
class AeroProblem(object):
    """
    The main purpose of this class is to represent all relevant
    information for a single aerodynamic analysis. This will
    include the thermodynamic parameters defining the flow, 
    condition, the reference quantities for normalization.

    There are several different ways of specifying thermodynamic
    conditions. The following describes several of the possible
    ways and the appropriate situations. 

    'mach' + 'altitude'
        This is the preferred method. The 1976 standard atmosphere is
        used to generate all therodynamic properties in a consistent
        manner. This is suitable for all aerodynamic analysis codes,
        including aerostructral analysis.

    'mach' + 'reynolds' + 'reynoldsLength' + 'T':
        Used to precisely match reynolds numbers. Complete
        thermodynamic state is computed. 

    'mach' + 'T' + 'P':
        Any arbitrary temperature and pressure.

    The combinations listed above are the **only** valid combinations
    of arguments that are permitted. Furthermore, since the internal
    processing is based (permenantly) on these parameters, it is
    important that the parameters given on initialization are
    sufficient for the required analysis. For example, if only the
    Mach number is given, an error will be raised if the user tried to
    set the 'P' (pressure) variable. 

    All parameters are optinonal except for the `name` argument which
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
        Set the mach number for the simulation

    alpha : float. Default is 0.0
        Set the angle of attack

    beta : float. Default is 0.0
        Set side-slip angle

    altitude : float. Default is 0.0
        Set all thermodynamic parameters from the 1976 standard atmosphere.
        the altitude must be given in meters.

    phat : float. Default is 0.0
        Set the rolling rate coefficient

    qhat : float. Default is 0.0
        Set the pitch rate coefficient

    rhat : float. Default is 0.0
        Set the yawing rate coefficient

    degPol : integer. Default is 0
        Degree of polynominal for prescribed motion. SUmb only

    coefPol : array_like. Default is [0.0]
        Coefficients of polynominal motion. SUmb only

    degFourier : integer. Default is 0
        Degree of fourrier coefficient for prescribed motion. SUmb only

    omegaFourier : float. Default is 0.0
        Fundamental circular freqnecy for oscillatory motino (Sumb only)

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
        Set the reynolds number

    reynoldslength : float. Default is 1.0
        Set the length reference for the reynolds number calculations

    areaRef : float. Default is 1.0
        Set the reference area used for normalization of Lift, Drag etc.

    chordRef : float. Default is 1.0
        Set the reference length used for moment normaliziation.

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

    R : float
        The gas constant. By defalut we use air. R=287.05

    englishUnits : bool
        Flag to use all English units: pounds, feet, Rankine etc. 
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
    >>> # OneraM6 Test condition (euler)
    >>> ap = AeroProblem('m6_tunnel', mach=0.8395, areaRef=0.772893541, chordRef=0.64607 \
xRef=0.0, zRef=0.0, alpha=3.06)
    >>> # OneraM6 Test condition (RANS)
    >>> ap = AeroProblem('m6_tunnel', mach=0.8395, reynolds=11.72e6, reynoldsLenght=0.64607, \
areaRef=0.772893541, chordRef=0.64607, xRef=0.0, zRef=0.0, alpha=3.06, T=255.56)
                         """
    def __init__(self, name, **kwargs):
        # Always have to have the name
        self.name = name
        # These are the parameters that can be simply set directly in
        # the class. 
        paras = set(('alpha', 'beta', 'areaRef', 'chordRef', 'spanRef', 
                 'xRef', 'yRef', 'zRef','xRot', 'yRot', 'zRot',
                 'phat', 'qhat', 'rhat',
                 'degreePol', 'coefPol', 'degreeFourier', 'omegaFourier',
                 'cosCoefFourier', 'sinCoefFourier'))

        # By default everything is None
        for para in paras:
            setattr(self, para, None)

        # Check if we have english units:
        self.englishUnits = False
        if 'englishUnits' in kwargs:
            self.englishUnits = kwargs['englishUnits']

        # Any matching key from kwargs that is in 'paras'
        for key in kwargs:
            if key in paras:
                setattr(self, key, kwargs[key])

        # Check for function list:
        if 'funcs' in kwargs:
            self.evalFuncs = set(kwargs['funcs'])

        # Check if 'R' is given....if not we assume air
        if 'R' in kwargs:
            self.R = kwargs['R']
        else:
            if self.englishUnits:
                self.R = 1716.493 #FIX THIS
            else:
                self.R = 287.870

        # Check if 'gamma' is given....if not we assume air
        if 'gamma' in kwargs:
            self.gamma = kwargs['gamma']
        else:
            self.gamma = 1.4

        # Now we can do the name matching for the data for the
        # thermodynamic condition. We actually can work backwards from
        # the list given in the doc string.
        fullState = set(['mach', 'V', 'P', 'T', 'rho', 'mu', 'nu', 'a',
                         'q', 'altitude', 're'])
        for key in fullState:
            self.__dict__[key] = None

        keys = set(kwargs.keys())
        if set(('mach', 'T', 'P')) <= keys:
            self.mach = kwargs['mach']
            self.T = kwargs['T']
            self.P = kwargs['P']
            self._update()
        elif set(('mach', 'reynolds', 'reynoldsLength', 'T')) <= keys:
            self.mach = kwargs['mach']
            self.T = kwargs['T']
            self.re = kwargs['reynolds']/kwargs['reynoldsLength']
            self._update()
        elif set(('mach', 'altitude')) <= keys:
            self.mach = kwargs['mach']
            self.altitude = kwargs['altitude']
            self._update()
        else:
            raise Error('There was not sufficient information to form\
            an aerodynamic state. See AeroProblem documentation in for\
            pyAero_problem.py for information on how to correctly \
            specify the aerodynamic state')
   
        # Specify the set of possible design variables:
        varFuncs = ['alpha', 'beta', 'areaRef', 'chordRef', 'spanRef',
                    'xRef', 'yRef', 'zRef', 'xRot', 'yRot', 'zRot',
                    'phat', 'qhat', 'rhat', 'mach', 'altitude', 'P', 'T']

        self.possibleDVs = set()
        for var in varFuncs:
            if getattr(self, var) is not None:
                self.possibleDVs.add(var)

        # Now determine the possible functions. Any possible design
        # variable CAN also be a function (pass through)
        self.possibleFunctions = set(self.possibleDVs)

        # And anything in fullState can be a function:
        for var in fullState:
            if getattr(self, var) is not None:
                self.possibleFunctions.add(var)
                
        # When a solver calls its evalFunctions() it must write the
        # unique name it gives to funcNames. 
        self.funcNames = {}

        # Storage of DVs
        self.DVs = {}
        self.DVNames = {}
        
    def addDV(self, key, value=None, lower=None, upper=None, scale=1.0,
              name=None, offset=0.0):
        """
        Add one of the class attributes as an 'aerodynamic' design
        variable. Typical variables are alpha, mach, altitude,
        chordRef etc. An error will be given if the requested DV is
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
            aeroProblems to explictly use the same design variable.

        offset : float. Default is 0.0

            Specify a specific (constant!) offset of the value used,
            as compared to the actual design variable. This is most
            often used when a single aerodynamic variable is used to
            change multiple aeroProblems. For example. if you have
            three aeroProblems for a multiPoint analysis, and you want
            mach numbers of 0.84, 0.85 and 0.86, but want want only to
            change the center one, and have the other two slave, we
            would do this::

              >>> ap1.addDV('mach',...,name='centerMach', offet=-0.01)
              >>> ap2.addDV('mach',...,name='centerMach', offet= 0.00)
              >>> ap3.addDV('mach',...,name='centerMach', offet=+0.01)

            The result is a single design variable driving three
            different mach numbers. 
            
        Examples
        --------
        >>> # Add alpha variable with typical bounds
        >>> ap.addDV('alpha', value=2.5, lower=0.0, upper=10.0, scale=0.1)
        """

        # First check if we are allowed to add the DV:
        if key not in self.possibleDVs:
            raise Error('The DV \'%s\' could not be added. Potential DVs MUST\
            be specified when the aeroProblem class is created. For example, \
            if you want alpha as a design variable (...,alpha=value, ...) must\
            be given. The list of possible DVs are: %s.'% (
                            key, repr(self.possibleDVs)))

        if name is None:
            dvName = key + '_%s'% self.name
        else:
            dvName = name

        if value is None:
            value = getattr(self, key)
         
        self.DVs[dvName] = aeroDV(key, value, lower, upper, scale, offset)
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
            optProb.addVar(key, 'c', value=dv.value, lower=dv.lower,
                           upper=dv.upper, scale = dv.scale)
            
    def __getitem__(self, key):

        return self.funcNames[key]

    def evalFunctions(self, funcs, evalFuncs):
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
        function of the altitue (and Mach number).

        Also, even if 'altitude' and 'mach' are not parameters, this
        function can be used to evaluate the 'V' value for example. In
        this case, 'V' is simply constant and no sensitivties would be
        calculated which is fine.

        Note that the list of available functions depends on how the
        user has initialzied the flight condition. 

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
                key = self.name + '_%s'% f
                self.funcNames[f] = key
                funcs[key] = getattr(self, f)
        else:
            raise Error('One of the functions in \'evalFuncs\' was not\
            valid. The valid list of functions is: %s.'% (
                            repr(self.possibleFunctions)))

    def evalFunctionsSens(self, funcsSens, evalFuncs):
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
            raise Error('One of the functions in \'evalFunctionsSens\' was not\
            valid. The valid list of functions is: %s.'% (
                            repr(self.possibleFunctions)))

    @property
    def mach(self):
        return self.__dict__['mach']

    @mach.setter
    def mach(self, value):
        self.__dict__['mach'] = value
        self._update()

    @property
    def T(self):
        return self.__dict__['T']

    @T.setter
    def T(self, value):
        self.__dict__['T'] = value
        self._update()

    @property
    def P(self):
        return self.__dict__['P']

    @P.setter
    def P(self, value):
        self.__dict__['P'] = value
        self._update()

    @property
    def rho(self):
        return self.__dict__['rho']

    @rho.setter
    def rho(self, value):
        self.__dict__['rho'] = value
        self._update()
        
    @property
    def re(self):
        return self.__dict__['re']

    @re.setter
    def re(self, value):
        self.__dict__['re'] = value
        self._update()

    @property
    def altitude(self):
        return self.__dict__['altitude']

    @altitude.setter
    def altitude(self, value):
         self.__dict__['altitude'] = value
         self.P, self.T = self._getAltitudeParams(value)
 
    def _update(self):
        """
        Try to finish the complete state:
        """

        SSuthDim  = 110.55
        muSuthDim = 1.716e-5
        TSuthDim  = 273.15

        if self.T is not None:
            self.a = numpy.sqrt(self.gamma*self.R*self.T)
            if self.englishUnits:
                mu = (muSuthDim * (
                        (TSuthDim + SSuthDim) / (self.T/1.8 + SSuthDim)) *
                       (((self.T/1.8)/TSuthDim)**1.5))
                self.mu = mu * 47.9
            else:
                self.mu = (muSuthDim * (
                        (TSuthDim + SSuthDim) / (self.T + SSuthDim)) *
                           ((self.T/TSuthDim)**1.5))

        if self.mach is not None and self.a is not None:
            self.V = self.mach * self.a
            
        if  self.P is not None and self.T is not None:
            self.__dict__['rho'] = self.P/(self.R*self.T)

        if self.rho is not None and self.T is not None:
            self.__dict__['P'] = self.rho*self.R*self.T
            
        if self.mu is not None and self.rho is not None:
            self.nu = self.mu / self.rho
            
        if self.rho is not None and self.V is not None:
            self.q = 0.5*self.rho*self.V**2

        if self.rho is not None and self.V is not None and self.mu is not None:
            self.__dict__['re'] = self.rho*self.V/self.mu
            
        if self.re is not None and self.mu is not None and self.V is not None:
            self.__dict__['rho'] = self.re*self.mu/self.V

    def _getDVSens(self, func):
        """
        Function that computes the derivative of the functions in
        evalFuncs, wrt the design variable key 'key'
        """
        rDict = {}
        h = 1e-40j; hr = 1e-40
        for key in self.DVNames:
            setattr(self, key, getattr(self, key) + h)
            rDict[self.DVNames[key]] = numpy.imag(self.__dict__[func])/hr
            setattr(self, key, numpy.real(getattr(self, key)))

        return rDict
    
    def _getAltitudeParams(self, altitude):
        """
        Compute the atmospheric properties at altitude, 'altitude' in meters
        """
        if altitude is None:
            return None, None, None
        # Convert altitude to km since this is what the ICAO
        # atmosphere uses:
        if self.englishUnits:
            altitude = altitude * .3048 / 1000.0
        else:
            altitude = altitude / 1000.0

        K  = 34.163195
        R0 = 6356.766 # Radius of Earth    
        H  = altitude/(1.0 + altitude/R0)

        # Smoothing region on either side. 0.1 is 100m, seems to work
        # well. Please don't change. 
        dH_smooth = 0.1

        # Sea Level Values
        P0 = 101325 # Pressure

        # The set of break-points in the altitude (in km)
        H_break = numpy.array([11, 20, 32, 47, 51, 71, 84.852])

        def hermite(t, p0, m0, p1, m1):
            """Compute a standard cubic hermite interpolant"""
            return p0*(2*t**3 - 3*t**2 + 1) + m0*(t**3 - 2*t**2 + t) + \
                p1*(-2*t**3 + 3*t**2) + m1*(t**3-t**2)

        def getTP(H, index):
            """Compute temperature and pressure"""
            if index == 0:
                T = 288.15 - 6.5*H
                PP = (288.15/T)**(-K/6.5)
            elif index == 1:
                T = 216.65
                PP = 0.22336*numpy.exp(-K*(H-11)/216.65)
            elif index == 2:
                T = 216.65 + (H-20)
                PP = 0.054032*(216.65/T)**K
            elif index == 3:
                T = 228.65 + 2.8*(H-32)
                PP = 0.0085666*(228.65/T)**(K/2.8)
            elif index == 4:
                T = 270.65
                PP = 0.0010945*numpy.exp(-K*(H-47)/270.65)
            elif index == 5:
                T = 270.65 - 2.8*(H-51)
                PP = 0.00066063*(270.65/T)**(-K/2.8)
            elif index == 6:
                T = 214.65 - 2*(H-71)
                PP = 0.000039046*(214.65/T)**(-K/2)
               
            return T, PP

        # Determine if we need to do smoothing or not:
        smooth = False
        for index in xrange(len(H_break)):
            if (numpy.real(H) > H_break[index] - dH_smooth and
                numpy.real(H) < H_break[index] + dH_smooth):
                smooth = True
                break

        if not smooth:
            index = H_break.searchsorted(H, side='left')

            # Get the nominal values we need
            T, PP = getTP(H, index)
        else:
            H0 = H_break[index]
            # Parametric distance along smoothing region        
            H_left = H0 - dH_smooth
            H_right = H0 + dH_smooth
            
            t = (H - H_left)/(H_right-H_left) # Parametric value from 0 to 1

            # Compute slope and values at the left boundary
            Tph, PPph = getTP(H_left + 1e-40j, index)

            T_left = numpy.real(Tph)
            PP_left = numpy.real(PPph)

            T_slope_left = numpy.imag(Tph)/1e-40 * (dH_smooth*2)
            PP_slope_left = numpy.imag(PPph)/1e-40 * (dH_smooth*2)

            # Compute slope and values at the right boundary
            Tph, PPph = getTP(H_right + 1e-40j, index+1)

            T_right = numpy.real(Tph)
            PP_right = numpy.real(PPph)

            T_slope_right = numpy.imag(Tph)/1e-40 * (dH_smooth*2)
            PP_slope_right = numpy.imag(PPph)/1e-40 * (dH_smooth*2)

            # Standard cubic hermite spline interpolation
            T = hermite(t, T_left, T_slope_left, T_right, T_slope_right)
            PP = hermite(t, PP_left, PP_slope_left, PP_right, PP_slope_right)        
        # end if

        P = P0*PP # Pressure    

        if self.englishUnits:
            P /= 47.88020833333  # FIX ME!
            T *= 1.8

        return P, T

class aeroDV(object):
    """
    A container storing information regarding an 'aerodynamic' variable.
    """
    
    def __init__(self, key, value, lower, upper, scale, offset):
        self.key = key
        self.value = value
        self.lower = lower
        self.upper = upper
        self.scale = scale
        self.offset = offset
