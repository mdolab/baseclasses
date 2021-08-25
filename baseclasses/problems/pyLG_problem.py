"""
pyLG_problem

Holds the information to setup a single LG problem.
Right now this is a relatively simple class that computes the load conditions at
the wheel for the main landing gear and an effective max-g load for further structural
computation. Nothing in this computation can be a design variable right now because
the beam model setup in TACS has no provision for changing the load as a design variable.
We will assume a fixed aircraft mass and LG characteristics. The output load can change as a
function of the LG geometry if necessary.
"""

import numpy


class LGProblem:
    """
    Landing Gear Problem Object:

    This Landing Gear Problem Object should contain all of the information
    required to estimate the Landing Loads imparted on a wing by the LG during
    Landing and ground operations.

    Parameters
    ----------

    name : str
        A name for the configuration

    evalFuncs : iteratble object containing strings
        The names of the functions the user wants evaluated for this weight
        problem
    """

    def __init__(self, name, **kwargs):
        """
        Initialize the mission problem
        """
        self.name = name
        # self.units = units.lower()

        # These are the parameters that can be simply set directly in
        # the class.
        paras = {
            "aircraftMass",
            "tireEff",
            "tireDef",
            "shockEff",
            "shockDef",
            "weightCondition",
            "loadCaseType",
            "loadFrac",
        }

        self.g = 9.81  # (m/s)
        self.nMainGear = 2
        # By default everything is None
        for para in paras:
            setattr(self, para, None)

        # Any matching key from kwargs that is in 'paras'
        for key in kwargs:
            if key in paras:
                setattr(self, key, kwargs[key])

        # for key in paras:
        #     print(key,getattr(self,key))

        if self.weightCondition.lower() == "mlw":
            self.V_vert = 3.048  # m/s or 10 fps
        elif self.weightCondition.lower() == "mtow":
            self.V_vert = 1.83  # m/s or 6 fps
        else:
            print("Unrecognized weightCondition:", self.weightCondition)

        if self.loadCaseType.lower() == "braking":
            self.nCondition = 2
            self.nameList = ["Braked rolling", "Reversed Braking"]
        elif self.loadCaseType.lower() == "landing":
            self.nCondition = 7
            self.nameList = [
                "Drag and side load",
                "Drag and side load",
                "Drag and side load",
                "Side load",
                "Side load",
                "High drag and spring-back",
                "High drag and spring-back",
            ]

        else:
            print("Unrecognized loadCaseType:", self.loadCaseType)

        self.name += "_" + self.loadCaseType + "_" + self.weightCondition

        self.nameList = None

        # Check for function list:
        self.evalFuncs = set()
        if "evalFuncs" in kwargs:
            self.evalFuncs = set(kwargs["evalFuncs"])

    def _computeLGForces(self):
        # These equations are from Aircraft Loading and Structural Layout by Denis Howe

        f_stat = self.aircraftMass * self.g / self.nMainGear

        g_load = (self.V_vert ** 2 + (2 * self.g * (1 - self.loadFrac) * (self.tireDef + self.shockDef))) / (
            2.0 * self.g * (self.tireEff * self.tireDef + self.shockEff * self.shockDef)
        )
        # print('gload',self.V_vert**2,(2*self.g*(1-self.loadFrac)*(self.tireDef+self.shockDef)),2.0 , self.g,self.tireEff * self.tireDef,self.shockEff * self.shockDef,self.V_vert**2 /(2.0 * self.g ),  (self.tireEff * self.tireDef + self.shockEff * self.shockDef))
        # f_dyn =  self.aircraftMass * self.V_vert**2 /\
        #          (4.0 * (self.tireEff * self.tireDef + self.shockEff * self.shockDef))

        f_dyn = (1.0 / self.nMainGear) * g_load * self.aircraftMass * self.g

        f_sb = f_dyn

        # print('fdyn',f_stat,f_dyn,f_sb,g_load)
        return f_stat, f_dyn, f_sb, g_load

    def getLoadFactor(self):
        """
        return the load factor for this load case
        """
        f_stat, f_dyn, f_sb, g_load = self._computeLGForces()
        if self.loadCaseType.lower() == "braking":
            loadFactor = 1.0
        elif self.loadCaseType.lower() == "landing":
            loadFactor = g_load
        else:
            print("Unrecognized loadCaseType:", self.loadCaseType)

        return loadFactor

    def getLoadCaseArrays(self):

        f_stat, f_dyn, f_sb, g_load = self._computeLGForces()

        if self.loadCaseType.lower() == "braking":

            if self.weightCondition.lower() == "mlw":
                fVert = numpy.zeros(self.nCondition)
                fVert[0] = 1.2 * f_stat
                fVert[1] = 1.2 * f_stat

                fDrag = numpy.zeros(self.nCondition)
                fDrag[0] = 0.96 * f_stat
                fDrag[1] = -0.66 * f_stat

                fSide = numpy.zeros(self.nCondition)

                closure = numpy.zeros(self.nCondition)
                closure[0] = 0.75 * self.shockDef
                closure[1] = 0.75 * self.shockDef

                gload = numpy.zeros(self.nCondition)
                gload[:] = g_load

            elif self.weightCondition.lower() == "mtow":
                fVert = numpy.zeros(self.nCondition)
                fVert[0] = 1.0 * f_stat
                fVert[1] = 1.0 * f_stat

                fDrag = numpy.zeros(self.nCondition)
                fDrag[0] = 0.8 * f_stat
                fDrag[1] = -0.55 * f_stat

                fSide = numpy.zeros(self.nCondition)

                closure = numpy.zeros(self.nCondition)
                closure[0] = 0.75 * self.shockDef
                closure[1] = 0.75 * self.shockDef

                gload = numpy.zeros(self.nCondition)
                gload[:] = g_load

            else:
                print("Unrecognized weightCondition:", self.weightCondition)

        elif self.loadCaseType.lower() == "landing":
            fVert = numpy.zeros(self.nCondition)
            fVert[0] = f_dyn
            fVert[1] = 0.75 * f_dyn
            fVert[2] = 0.75 * f_dyn
            fVert[3] = 0.5 * f_dyn
            fVert[4] = 0.5 * f_dyn
            fVert[5] = 0.8 * f_sb
            fVert[6] = 0.8 * f_sb

            fDrag = numpy.zeros(self.nCondition)
            fDrag[0] = 0.25 * f_dyn
            fDrag[1] = 0.4 * f_dyn
            fDrag[2] = 0.4 * f_dyn
            fDrag[3] = 0.0
            fDrag[4] = 0.0
            fDrag[5] = 0.64 * f_sb
            fDrag[6] = -0.64 * f_sb

            # sign convention here is that negative is inboard facing
            fSide = numpy.zeros(self.nCondition)
            fSide[0] = 0
            fSide[1] = -0.25 * f_dyn
            fSide[2] = 0.25 * f_dyn
            fSide[3] = -0.4 * f_dyn
            fSide[4] = 0.3 * f_dyn
            fSide[5] = 0.0
            fSide[6] = 0.0

            closure = numpy.zeros(self.nCondition)
            closure[0] = 0.5 * self.shockDef
            closure[1] = 0.25 * self.shockDef
            closure[2] = 0.25 * self.shockDef
            closure[3] = 0.5 * self.shockDef
            closure[4] = 0.5 * self.shockDef
            closure[5] = 0.15 * self.shockDef
            closure[6] = 0.15 * self.shockDef

            gload = numpy.zeros(self.nCondition)
            gload[:] = g_load

        else:
            print("Unrecognized loadCaseType:", self.loadCaseType)

        closure = self.shockDef - closure

        return fVert, fDrag, fSide, closure, gload

    def writeLoadData(self, fileName):
        """
        write a table based on the weight condition
        """

        f_stat, f_dyn, f_sb, g_load = self._computeLGForces()

        caseType = self.weightCondition.upper()
        f = open(fileName, "w")
        f.write("\\begin{tabular}{lr}\n")
        f.write("\\toprule\n")
        f.write("Parameter & Value \\\\\n")
        f.write(" \\midrule\n")
        f.write(f" {caseType} $F_\\text{{stat}}$ (N) &$ {f_stat:10.0f}$ \\\\\n")
        f.write(f" {caseType} $F_\\text{{dyn}}$ (N) &$ {f_dyn:10.0f}$\\\\\n")
        f.write(f" {caseType} Load Factor & {g_load:6.3f}\\\\\n")
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")

        f.close()


# create a dump loads table function
