"""
pyWeight_problem

Holds the weightProblem class for weightandbalance solvers.
"""

import numpy
import copy

try:
    from pygeo import geo_utils
except ImportError:
    geo_utils = None
from ..utils import Error


class WeightProblem:
    """
    Weight Problem Object:

    This Weight Problem Object should contain all of the information required
    to estimate the weight of a particular component configuration.

    Parameters
    ----------

    name : str
        A name for the configuration

    units : str
        Define the units that this weight problem will use. This set of units is transferred to all components when the are added to the weight problem. It is assumed that all user defined parameters provided to the components are in this unit system. Each component converts the user provided inputs from this unit system to the one used internally to perform calculations and then converts the output back to the user defined system.

    evalFuncs : iteratble object containing strings
        The names of the functions the user wants evaluated for this weight
        problem
    """

    def __init__(self, name, units, **kwargs):
        """
        Initialize the mission problem
        """
        self.name = name
        self.units = units.lower()

        self.components = {}
        self.fuelcases = []
        self.funcNames = {}
        self.currentDVs = {}
        self.solveFailed = False
        self.constraintsAdded = False
        self.DVGeo = None
        self.p0 = None
        self.v1 = None
        self.v1 = None

        # Check for function list:
        self.evalFuncs = set()
        if "evalFuncs" in kwargs:
            self.evalFuncs = set(kwargs["evalFuncs"])

        self.mlwfraction = 0.75
        if "mlwFraction" in kwargs:
            self.mlwfraction = kwargs["mlwFraction"]

    def addComponents(self, components):  # *components?
        """
        Append a list of components to the interal component list
        """

        # Check if components is of type Component or list, otherwise raise Error
        if type(components) == list:
            pass
        elif type(components) == object:
            components = [components]
        else:
            raise Error("addComponents() takes in either a list of or a single component")

        # Add the components to the internal list
        for comp in components:
            comp.setUnitSystem(self.units)
            self.components[comp.name] = comp

            # If the component has coords, embed the coordinates into DVGeo
            # with the name provided:
            if comp.hasCoords:
                if self.p0 is not None:
                    comp._generateAreaMesh(self.p0, self.v1, self.v2)
                else:
                    raise Error(
                        "attempting to add a coordinate based component without\
                    providing a surface. Please set a surface using setSurface()"
                    )
                if self.DVGeo is not None:
                    self.DVGeo.addPointSet(comp.coords, comp.name)

            for dvName in comp.DVs:
                key = self.name + "_" + dvName
                self.currentDVs[key] = comp.DVs[dvName].value
            # end

        return

    def _getNumComponents(self):
        """
        This is a call that should only be used by MissionAnalysis
        """
        return len(self.components)

    def setSurface(self, surf):
        """
        Set the surface this configuratoin will use to perform projections for
        various components.

        Parameters
        ----------
        surf : pyGeo object or list

            This is the surface representation to use for
            projections. If available, a pyGeo surface object can be
            used OR a triangulated surface in the form [p0, v1, v2] can
            be used. This triangulated surface form can be supplied
            from pyADflow or from pyTrian.

        Examples
        --------
        >>> CFDsolver = ADFLOW(comm=comm, options=aeroOptions)
        >>> surf = CFDsolver.getTriangulatedMeshSurface()
        >>> wp.setSurface(surf)
        >>> # Or using a pyGeo surface object:
        >>> surf = pyGeo('iges',fileName='wing.igs')
        >>> wp.setSurface(surf)

        """

        if type(surf) == list:
            self.p0 = numpy.array(surf[0])
            self.v1 = numpy.array(surf[1])
            self.v2 = numpy.array(surf[2])
        else:
            if geo_utils is None:
                raise Error("Unable to find pygeo module, which is required for this functionality.")
            else:
                self._generateDiscreteSurface(surf)

    def _generateDiscreteSurface(self, geo):
        """
        Take a pygeo surface and create a discrete triangulated
        surface from it. This is quite dumb code and does not pay any
        attention to things like how well the triangles approximate
        the surface or the underlying parametrization of the surface
        """

        p0 = []
        v1 = []
        v2 = []
        level = 1
        for isurf in range(geo.nSurf):
            surf = geo.surfs[isurf]
            ku = surf.ku
            kv = surf.kv
            tu = surf.tu
            tv = surf.tv

            u = geo_utils.fillKnots(tu, ku, level)
            v = geo_utils.fillKnots(tv, kv, level)

            for i in range(len(u) - 1):
                for j in range(len(v) - 1):
                    P0 = surf(u[i], v[j])
                    P1 = surf(u[i + 1], v[j])
                    P2 = surf(u[i], v[j + 1])
                    P3 = surf(u[i + 1], v[j + 1])

                    p0.append(P0)
                    v1.append(P1 - P0)
                    v2.append(P2 - P0)

                    p0.append(P3)
                    v1.append(P2 - P3)
                    v2.append(P1 - P3)

        self.p0 = numpy.array(p0)
        self.v1 = numpy.array(v1)
        self.v2 = numpy.array(v2)

    def writeSurfaceTecplot(self, fileName):
        """
        Write the triangulated surface mesh used in the weight_problem object
        to a tecplot file for visualization.

        Parameters
        ----------
        fileName : str
            File name for tecplot file. Should have a .dat extension.

        """
        f = open(fileName, "w")
        f.write('TITLE = "weight_problem Surface Mesh"\n')
        f.write('VARIABLES = "CoordinateX" "CoordinateY" "CoordinateZ"\n')
        f.write("Zone T=%s\n" % ("surf"))
        f.write("Nodes = %d, Elements = %d ZONETYPE=FETRIANGLE\n" % (len(self.p0) * 3, len(self.p0)))
        f.write("DATAPACKING=POINT\n")
        for i in range(len(self.p0)):
            points = []
            points.append(self.p0[i])
            points.append(self.p0[i] + self.v1[i])
            points.append(self.p0[i] + self.v2[i])
            for i in range(len(points)):
                f.write(f"{points[i][0]:f} {points[i][1]:f} {points[i][2]:f}\n")

        for i in range(len(self.p0)):
            f.write("%d %d %d\n" % (3 * i + 1, 3 * i + 2, 3 * i + 3))

        f.close()

    def writeTecplot(self, fileName):
        """
        This function writes a visualization file for the components that have
        coordinates. All currently added components with coords are written to a
        tecplot file. This is useful for publication purposes as well as determine if the
        constraints are *actually* what the user expects them to be.

        Parameters
        ----------
        fileName : str
            File name for tecplot file. Should have a .dat extension.
        """

        f = open(fileName, "w")
        f.write('TITLE = "Weight_problem Data"\n')
        f.write('VARIABLES = "CoordinateX" "CoordinateY" "CoordinateZ"\n')

        for compKey in self.components.keys():
            comp = self.components[compKey]
            if comp.hasCoords:
                comp.writeTecplot(f)
        f.close()

    def setDVGeo(self, DVGeo):
        """
        Set the DVGeometry object that will manipulate this object.
        Note that pyWeight_problem doesn't **strictly** need a DVGeometry
        object set, but if optimization is desired it is required.

        Parameters
        ----------
        dvGeo : A DVGeometry object.
            Object responsible for manipulating the constraints that
            this object is responsible for.

        Examples
        --------
        >>> wp.setDVGeo(DVGeo)
        """

        self.DVGeo = DVGeo

    def setDesignVars(self, x):
        """
        Set the variables in the x-dict for this object.

        Parameters
        ----------
        x : dict
            Dictionary of variables which may or may not contain the
            design variable names this object needs
        """

        for compKey in self.components.keys():
            comp = self.components[compKey]
            if comp.hasCoords and self.DVGeo is not None:
                comp.coords = self.DVGeo.update(comp.name)
            for key in comp.DVs:
                dvName = self.name + "_" + key

                if dvName in x:
                    xTmp = {key: x[dvName]}
                    comp.setDesignVars(xTmp)
                    self.currentDVs[dvName] = x[dvName]

        for case in self.fuelcases:
            for key in case.DVs:
                dvName = self.name + "_" + key

                if dvName in x:
                    xTmp = {key: x[dvName]}
                    case.setDesignVars(xTmp)
                    self.currentDVs[dvName] = x[dvName]

    def addVariablesPyOpt(self, optProb):
        """
        Add the current set of variables to the optProb object.

        Parameters
        ----------
        optProb : pyOpt_optimization class
            Optimization problem definition to which variables are added
        """

        for compKey in self.components.keys():
            comp = self.components[compKey]
            for key in comp.DVs:
                dvName = self.name + "_" + key
                dv = comp.DVs[key]
                if dv.addToPyOpt:
                    optProb.addVar(dvName, "c", value=dv.value, lower=dv.lower, upper=dv.upper, scale=dv.scale)

        for case in self.fuelcases:
            for key in case.DVs:
                dvName = self.name + "_" + key

                dv = case.DVs[key]
                if dv.addToPyOpt:
                    optProb.addVar(dvName, "c", value=dv.value, lower=dv.lower, upper=dv.upper, scale=dv.scale)

    def getVarNames(self):
        """
        Get the variable names associate with this weight problem
        """

        names = []
        for compKey in self.components.keys():
            comp = self.components[compKey]
            for key in comp.DVs:
                dvName = self.name + "_" + key
                names.append(dvName)

        for case in self.fuelcases:
            for key in case.DVs:
                dvName = self.name + "_" + key
                names.append(dvName)

        return names

    def addConstraintsPyOpt(self, optProb=None):
        """
        Add the linear constraints for each of the fuel cases.

        Also add non-linear constraints that all of the fuel cases have a total
        TOW less than MTOW


        Parameters
        ----------
        optProb : pyOpt_optimization class
            Optimization problem definition to which variables are added
        """
        constraints = []
        for case in self.fuelcases:
            constraints.append(case.addLinearConstraint(optProb=optProb, prefix=self.name))
        self.constraintsAdded = True
        for case in self.fuelcases:
            conName = self.name + "_" + case + "_MTOW"
            optProb.addCon(conName, upper=0.0)  # , wrt=[]) figure out the wrt...
            self.evalFuncs.add(conName)

        return constraints

    def addFuelCases(self, cases):
        """
        Append a list of fuel cases to the weight problem
        """

        # Check if case is a single entry or a list, otherwise raise Error
        if type(cases) == list:
            pass
        elif type(cases) == object:
            cases = [cases]
        else:
            raise Error("addFuelCases() takes in either a list of or a single fuelcase")

        # Add the fuel cases to the problem
        for case in cases:
            self.fuelcases.append(case)

            for dvName in case.DVs:
                key = self.name + "_" + dvName
                self.currentDVs[key] = case.DVs[dvName].value
            # end
        return

    def getFuelCase(self, caseName):
        """
        Get the fuel case object associated with the caseName.

        Parameters
        ----------
        caseName : str
            Name of the fuel case to return
        """
        currentCase = None
        for case in self.fuelcases:
            if case.name == caseName:
                currentCase = case

        if currentCase:
            return currentCase
        else:
            raise Error("Supplied fuel caseName: %s, not found" % caseName)

    def setFuelCase(self, case):
        """
        loop over the components and set the specified fuel case

        Parameters
        ----------
        case : fuelCase object
           The fuel case to set

        """

        # Get just the fuel components
        fuelKeys = self._getComponentKeys(includeType="fuel")

        for key in fuelKeys:
            self.components[key].setFuelCase(case)
        # end

    def resetFuelCase(self):
        """
        reset the fuel weight for this case.
        """
        # Get just the fuel components
        fuelKeys = self._getComponentKeys(includeType="fuel")

        for key in fuelKeys:
            self.components[key].resetFuelCase()
        # end

    def _getComponentKeys(self, include=None, exclude=None, includeType=None, excludeType=None):
        """
        Get a list of component keys based on inclusion and exclusion

        Parameters
        ----------
        include : list or str
           (Optional) String or list of components to be included in the sum
        exclude : list or str
           (Optional) String or list of components to be excluded in the sum
        includeType :
           (Optional) String or list of component types to include in the weight keys
        excludeType :
           (Optional) String or list of component types to exclude in the weight keys
        """

        weightKeys = set(self.components.keys())

        if includeType is not None:
            # Specified a list of component types to include
            if type(includeType) == str:
                includeType = [includeType]
            weightKeysTmp = set()
            for key in weightKeys:
                if self.components[key].compType in includeType:
                    weightKeysTmp.add(key)
            weightKeys = weightKeysTmp

        if include is not None:
            # Specified a list of compoents to include
            if type(include) == str:
                include = [include]
            include = set(include)
            weightKeys.intersection_update(include)

        if exclude is not None:
            # Specified a list of components to exclude
            if type(exclude) == str:
                exclude = [exclude]
            exclude = set(exclude)
            weightKeys.difference_update(exclude)

        if excludeType is not None:
            # Specified a list of compoent types to exclude
            if type(excludeType) == str:
                excludeType = [excludeType]
            weightKeysTmp = copy.copy(weightKeys)
            for key in weightKeys:
                if self.components[key].compType in excludeType:
                    weightKeysTmp.remove(key)
            weightKeys = weightKeysTmp

        return weightKeys

    def writeMassesTecplot(self, filename):
        """
        Get a list of component keys based on inclusion and exclusion

        Parameters
        ----------

        filename: str
            filename for writing the masses. This string will have the
            .dat suffix appended to it.
        """

        fileHandle = filename + ".dat"
        f = open(fileHandle, "w")
        nMasses = len(self.nameList)
        f.write('TITLE = "%s: Mass Data"\n' % self.name)
        f.write('VARIABLES = "X", "Y", "Z", "Mass"\n')
        locList = ["current", "fwd", "aft"]

        for loc in locList:
            f.write('ZONE T="%s", I=%d, J=1, K=1, DATAPACKING=POINT\n' % (loc, nMasses))

            for key in self.components.keys():
                CG = self.components[key].getCG(loc)
                mass = self.components[key].getMass()
                x = numpy.real(CG[0])
                y = numpy.real(CG[1])
                z = numpy.real(CG[2])
                m = numpy.real(mass)

                f.write(f"{x:f} {y:f} {z:f} {m:f}\n")

            # end
            f.write("\n")
        # end

        # textOffset = 0.5
        # for loc in locList:
        #     for name in self.nameList:
        #         x= numpy.real(self.componentDict[name].CG[loc][0])
        #         y= numpy.real(self.componentDict[name].CG[loc][1])
        #         z= numpy.real(self.componentDict[name].CG[loc][2])+textOffset
        #         m= numpy.real(self.componentDict[name].W)

        #         f.write('TEXT CS=GRID3D, HU=POINT, X=%f, Y=%f, Z=%f, H=12, T="%s"\n'%(x,y,z,name+' '+loc))
        #     # end

        # # end

        f.close()
        return

    def writeProblemData(self, fileName):
        """
        Write the problem data to a file
        """
        fileHandle = fileName + ".txt"
        f = open(fileHandle, "w")
        f.write("Name, W, Mass, CG \n")
        for key in sorted(self.components.keys()):
            CG = self.components[key].getCG(self.units, "current")
            mass = self.components[key].getMass(self.units)
            W = self.components[key].getWeight(self.units)
            name = self.components[key].name
            f.write(f"{name}: {W:f}, {mass:f}, {CG[0]:f} {CG[1]:f} {CG[2]:f} \n")
        # end

        f.close()
        return

    def __str__(self):
        """
        loop over the components and call the owned print function
        """
        for key in self.components.keys():
            print(key)
            print(self.components[key])

        return " "


class FuelCase:
    """
    class to handle individual fuel cases.
    """

    def __init__(self, name, fuelFraction=0.9, reserveFraction=0.1):
        """
        Initialize the fuel case

        Parameters
        ----------

        name : str
           A name for the fuel case.

        fuelFraction : float
           Fraction of fuel component volume that contains fuel.

        reserveFraction : float
           Fraction of fuel component volume that contains reserve fuel.
        """

        self.name = name
        self.fuelFraction = fuelFraction
        self.reserveFraction = reserveFraction

        # Storage of DVs
        self.DVs = {}
        self.DVNames = {}
        self.possibleDVs = ["fuelFraction", "reserveFraction"]

        return

    def addDV(
        self, key, value=None, lower=None, upper=None, scale=1.0, name=None, offset=0.0, axis=None, addToPyOpt=True
    ):

        """
        Add one of the fuel case parameters as a weight and balance design
        variable. Typical variables are fuelfraction and reservefraction.
        An error will be given if the requested DV is not allowed to
        be added .


        Parameters
        ----------
        key : str
            Name of variable to add. See above for possible ones

        value : float. Default is None
            Initial value for variable. If not given, current value
            of the attribute will be used.

        lower : float. Default is None
            Optimization lower bound. Default is unbounded.

        upper : float. Default is None
            Optimization upper bound. Default is unbounded.

        scale : float. Default is 1.0
            Set scaling parameter for the optimization to use.

        name : str. Default is None
            Overwrite the name of this variable. This is typically
            only used when the user wishes to have multiple
            components explictly use the same design variable.

        offset : float. Default is 0.0

            Specify a specific (constant!) offset of the value used,
            as compared to the actual design variable.

        addToPyOpt : bool. Default True.
            Flag specifying if this variable should be added. Normally this
            is True. However, if there are multiple weightProblems sharing
            the same variable, only one needs to add the variables to pyOpt
            and the others can set this to False.

        Examples
        --------
        >>> # Add W variable with typical bounds
        >>> fuelCase.addDV('fuelFraction', value=0.5, lower=0.0, upper=1.0, scale=0.1)
        >>> fuelCase.addDV('reserveFraction', value=0.1, lower=0.0, upper=1.0, scale=0.1)
        """

        # First check if we are allowed to add the DV:
        if key not in self.possibleDVs:
            raise Error(f"The DV '{key}' could not be added.  The list of possible DVs are: {repr(self.possibleDVs)}.")

        if name is None:
            dvName = "%s_" % self.name + key
        else:
            dvName = name

        if axis is not None:
            dvName += "_%s" % axis

        if value is None:
            value = getattr(self, key)

        self.DVs[dvName] = fuelCaseDV(key, value, lower, upper, scale, offset, addToPyOpt)
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
                self.DVs[dvName].value = x[dvName]

    def addLinearConstraint(self, optProb=None, prefix=None):
        """
        add the linear constraint for the fuel fractions
        """
        reserveDV = False
        fuelDV = False
        for key in self.DVNames:
            if key.lower() == "fuelfraction":
                fuelDV = True

            if key.lower() == "reservefraction":
                reserveDV = True

        conName = prefix + "_" + self.name + "_fuelcase"
        var1Name = prefix + "_" + self.name + "_fuelFraction"
        var2Name = prefix + "_" + self.name + "_reserveFraction"
        args = ()
        if reserveDV and fuelDV:
            args = (
                conName,
                {
                    "lower": 0,
                    "upper": 1,
                    "scale": 1,
                    "linear": True,
                    "wrt": [var1Name, var2Name],
                    "jac": {var1Name: [[1]], var2Name: [[1]]},
                },
            )
        elif reserveDV:
            args = (
                conName,
                {
                    "lower": 0,
                    "upper": 1 - self.fuelFraction,
                    "scale": 1,
                    "linear": True,
                    "wrt": [var2Name],
                    "jac": {var2Name: [[1]]},
                },
            )
        elif fuelDV:
            args = (
                conName,
                {
                    "lower": 0,
                    "upper": 1 - self.reserveFraction,
                    "scale": 1,
                    "linear": True,
                    "wrt": [var1Name],
                    "jac": {var1Name: [[1]]},
                },
            )

        if optProb and args:  # might be none, if you just want the constraint args for OpenMDAO
            optProb.addCon(args[0], **args[1])
        return args

    def addLinearMTOWConstraint(self, optProb=None, prefix=None):
        mtowReserveDV = False
        mtowFuelDV = False
        for key in self.DVNames:
            if key.lower() == "mtowfuelfraction":
                mtowFuelDV = True

            if key.lower() == "mtowreservefraction":
                mtowReserveDV = True

        conName = prefix + "_" + self.name + "_mtowFuelcase"
        var1Name = prefix + "_" + self.name + "_mtowFuelFraction"
        var2Name = prefix + "_" + self.name + "_mtowReserveFraction"
        args = ()
        if mtowReserveDV and mtowFuelDV:
            args = (
                conName,
                {
                    "lower": 0,
                    "upper": 1,
                    "scale": 1,
                    "linear": True,
                    "wrt": [var1Name, var2Name],
                    "jac": {var1Name: [[1]], var2Name: [[1]]},
                },
            )
        elif mtowReserveDV:
            args = (
                conName,
                {
                    "lower": 0,
                    "upper": 1 - self.fuelFraction,
                    "scale": 1,
                    "linear": True,
                    "wrt": [var2Name],
                    "jac": {var2Name: [[1]]},
                },
            )
        elif mtowFuelDV:
            args = (
                conName,
                {
                    "lower": 0,
                    "upper": 1 - self.reserveFraction,
                    "scale": 1,
                    "linear": True,
                    "wrt": [var1Name],
                    "jac": {var1Name: [[1]]},
                },
            )

        if optProb and args:  # might be none, if you just want the constraint args for OpenMDAO
            optProb.addCon(args[0], **args[1])

        return args


class fuelCaseDV:
    """
    A container storing information regarding a fuel case variable.
    """

    def __init__(self, key, value, lower, upper, scale, offset, addToPyOpt):
        self.key = key
        self.value = value
        self.lower = lower
        self.upper = upper
        self.scale = scale
        self.offset = offset
        self.addToPyOpt = addToPyOpt
