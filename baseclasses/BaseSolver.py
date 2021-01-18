"""
BaseSolver

Holds a basic Python Analysis Classes (base and inherited).
"""


# =============================================================================
# BaseSolver Class
# =============================================================================
class BaseSolver(object):

    """
    Abstract Class for a basic Solver Object
    """

    def __init__(self, name, category={}, def_options={}, **kwargs):
        """
        Solver Class Initialization

        Documentation last updated:
        """

        #
        self.name = name
        self.category = category
        self.options = CaseInsensitiveDict()
        self.defaultOptions = def_options
        self.solverCreated = False
        self.imOptions = {}

        # Initialize Options
        for key in self.defaultOptions:
            self.setOption(key, self.defaultOptions[key][1])

        koptions = kwargs.pop("options", CaseInsensitiveDict())
        for key in koptions:
            self.setOption(key, koptions[key])

        self.solverCreated = True

    def __call__(self, *args, **kwargs):
        """
        Run Analyzer (Calling Routine)

        Documentation last updated:
        """

        # Checks
        pass

    def setOption(self, name, value):
        """
        Default implementation of setOption()

        Parameters
        ----------
        name : str
           Name of option to set. Not case sensitive
        value : varies
           Value to set. Type is checked for consistency.

        """
        name = name.lower()
        try:
            self.defaultOptions[name]
        except KeyError:
            Error("Option '%-30s' is not a valid %s option." % (name, self.name))

        # Make sure we are not trying to change an immutable option if
        # we are not allowed to.
        if self.solverCreated and name in self.imOptions:
            raise Error("Option '%-35s' cannot be modified after the solver " "is created." % name)

        # Now we know the option exists, lets check if the type is ok:
        if isinstance(value, self.defaultOptions[name][0]):
            # Just set:
            self.options[name] = [type(value), value]
        else:
            raise Error(
                "Datatype for Option %-35s was not valid \n "
                "Expected data type is %-47s \n "
                "Received data type is %-47s" % (name, self.defaultOptions[name][0], type(value))
            )

    def getOption(self, name):
        """
        Default implementation of getOption()

        Parameters
        ----------
        name : str
           Name of option to get. Not case sensitive

        Returns
        -------
        value : varies
           Return the current value of the option.
        """

        if name.lower() in self.defaultOptions:
            return self.options[name.lower()][1]
        else:
            raise Error("%s is not a valid option name." % name)

    def printCurrentOptions(self):
        """
        Prints a nicely formatted dictionary of all the current solver
        options to the stdout on the root processor"""
        if self.comm.rank == 0:
            print("+---------------------------------------+")
            print("|          All %s Options:          |" % self.name)
            print("+---------------------------------------+")
            # Need to assemble a temporary dictionary
            tmpDict = {}
            for key in self.options:
                tmpDict[key] = self.getOption(key)
            pp(tmpDict)

    def printModifiedOptions(self):
        """
        Prints a nicely formatted dictionary of all the current solver
        options that have been modified from the defaults to the root
        processor"""
        if self.comm.rank == 0:
            print("+---------------------------------------+")
            print("|      All Modified %s Options:     |" % self.name)
            print("+---------------------------------------+")
            # Need to assemble a temporary dictionary
            tmpDict = {}
            for key in self.options:
                if self.getOption(key) != self.defaultOptions[key][1]:
                    tmpDict[key] = self.getOption(key)
            pp(tmpDict)


# ==============================================================================
# Optimizer Test
# ==============================================================================
if __name__ == "__main__":

    print("Testing ...")

    # Test Optimizer
    azr = BaseSolver("Test")
    dir(azr)
