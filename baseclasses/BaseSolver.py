"""
BaseSolver

Holds a basic Python Analysis Classes (base and inherited).
"""
from pprint import pprint as pp
from .utils import CaseInsensitiveDict, CaseInsensitiveSet, Error

# =============================================================================
# BaseSolver Class
# =============================================================================
class BaseSolver(object):
    """
    Abstract Class for a basic Solver Object
    """

    def __init__(self, name, category={}, def_options={}, options={}, imOptions=set(), depOptions={}):
        """
        Solver Class Initialization
        """

        self.name = name
        self.category = category
        self.options = CaseInsensitiveDict()
        self.defaultOptions = CaseInsensitiveDict(def_options)
        self.imOptions = CaseInsensitiveSet(imOptions)
        self.deprecatedOptions = CaseInsensitiveDict(depOptions)
        self.solverCreated = False

        # Initialize Options
        for key, (optionType, optionValue) in self.defaultOptions.items():

            # Check if the default is given in a list of possible values
            if isinstance(optionValue, list) and optionType is not list:
                # Default is the first element of the list
                self.setOption(key, optionValue[0])
            else:
                self.setOption(key, optionValue)

        for key in options:
            self.setOption(key, options[key])

        self.solverCreated = True

    def __call__(self, *args, **kwargs):
        """
        Run Analyzer (Calling Routine)
        """

        # Checks
        pass

    def setOption(self, name, value):
        """
        Default implementation of setOption()

        Parameters
        ----------
        name : str
           Name of option to set. Not case sensitive.
        value : varies
           Value to set. Type is checked for consistency.

        """
        # Check if the option exists
        try:
            defaultType, defaultValue = self.defaultOptions[name]
        except KeyError:
            raise Error(f"Option {name} is not a valid {self.name} option.")

        if name in self.deprecatedOptions:
            raise Error(f"Option {name} is deprecated. {self.deprecatedOptions[name]}")

        # Make sure we are not trying to change an immutable option if
        # we are not allowed to.
        if self.solverCreated and name in self.imOptions:
            raise Error("Option '%-35s' cannot be modified after the solver " "is created." % name)

        # If the default provides a list of acceptable values, check whether the value is valid
        if isinstance(defaultValue, list) and defaultType is not list:
            if value in defaultValue:
                self.options[name] = value
            else:
                raise Error(
                    f"Value for option {name} is not valid. "
                    + f"Value must be one of {defaultValue} with data type {defaultType}. "
                    + f"Received value is {value} with data type {type(value)}."
                )
        else:
            # If a list is not provided, check just the type
            if isinstance(value, defaultType):
                self.options[name] = value
            else:
                raise Error(
                    f"Datatype for option {name} is not valid. "
                    + f"Expected data type {defaultType}. "
                    + f"Received data type is {type(value)}."
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

        if name in self.defaultOptions:
            return self.options[name]
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
