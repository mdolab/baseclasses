"""
pyAero_problem

"""
from ..utils import Error


class TransiProblem:
    def __init__(self, name, **kwargs):
        # Always have to have the name
        # Always have to have the name
        self.name = name
        # These are the parameters that can be simply set directly in
        # the class.
        paras = {"mach", "reynolds", "T", "nCritTS", "nCritCF", "spanDirection", "sectionData", "partName"}

        # By default everything is None
        # print(kwargs)
        for para in paras:
            setattr(self, para, None)

        # Any matching key from kwargs that is in 'paras'
        for key in kwargs:
            if key in paras:
                setattr(self, key, kwargs[key])
                # print (key)
        # print(self.mach,'self.name')

        # these are the possible input values
        possibleInputStates = {
            "mach",
            "reynolds",
            "T",
            "nCritTS",
            "nCritCF",
            "spanDirection",
            "sectionData",
            "partName",
        }

        # turn the kwargs into a set
        keys = set(kwargs.keys())
        # print(keys)

        # save the initials states
        self.inputs = {}
        for key in keys:
            if key in possibleInputStates:
                self.inputs[key] = kwargs[key]
                # print(key,self.inputs[key])
        # print(kwargs.keys(),'self.name')

        # full list of states in the class
        self.fullState = {"mach", "reynolds", "T", "nCritTS", "nCritCF", "spanDirection", "sectionData", "partName"}

        # now call the routine to setup the states
        self._setStates(self.inputs)
        # print(self.phi_le)

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
        if {"mach", "reynolds", "T", "nCritTS", "nCritCF", "spanDirection", "sectionData", "partName"} == inKeys:
            self.__dict__["mach"] = self.inputs["mach"]
            self.__dict__["reynolds"] = self.inputs["reynolds"]
            self.__dict__["T"] = self.inputs["T"]
            self.__dict__["nCritTS"] = self.inputs["nCritTS"]
            self.__dict__["nCritCF"] = self.inputs["nCritCF"]
            self.__dict__["spanDirection"] = self.inputs["spanDirection"]
            self.__dict__["sectionData"] = self.inputs["sectionData"]
            self.__dict__["partName"] = self.inputs["partName"]

        else:
            raise Error("There shold be 14 parameters giiven")
