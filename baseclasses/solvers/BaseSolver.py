"""
BaseSolver

Holds a basic Python Analysis Classes (base and inherited).
"""
from difflib import get_close_matches
import copy
import warnings
from ..utils import CaseInsensitiveDict, CaseInsensitiveSet, Error, pp

# =============================================================================
# BaseSolver Class
# =============================================================================
class BaseSolver:
    """
    Abstract Class for a basic Solver Object
    """

    def __init__(
        self,
        name,
        category,
        defaultOptions={},
        options={},
        immutableOptions=set(),
        deprecatedOptions={},
        comm=None,
        informs={},
        checkDefaultOptions=True,
        caseSensitiveOptions=False,
    ):
        """
        Solver Class Initialization

        Parameters
        ----------
        name : str
            The name of the solver
        category : dict
            The category of the solver
        defaultOptions : dict, optional
            The default options dictionary
        options : dict, optional
            The user-supplied options dictionary
        immutableOptions : set of strings, optional
            A set of immutable option names, which cannot be modified after solver creation.
        deprecatedOptions : dict, optional
            A dictionary containing deprecated option names, and a message to display if they were used.
        comm : MPI Communicator, optional
            The comm object to be used. If none, serial execution is assumed.
        informs : dict, optional
            A dictionary of exit code: exit message mappings.
        checkDefaultOptions : bool, optional
            A flag to specify whether the default options should be used for error checking.
            This is used in cases where the default options are not the complete set, which is common for external solvers.
            In such cases, no error checking is done when calling ``setOption``, but the default options are still set as options
            upon solver creation.
        caseSensitiveOptions : bool, optional
            A flag to specify whether the option names are case sensitive or insensitive.
        """

        self.name = name
        self.category = category
        if not caseSensitiveOptions:
            self.options = CaseInsensitiveDict()
            self.defaultOptions = CaseInsensitiveDict(defaultOptions)
            self.immutableOptions = CaseInsensitiveSet(immutableOptions)
            self.deprecatedOptions = CaseInsensitiveDict(deprecatedOptions)
        else:
            self.options = {}
            self.defaultOptions = defaultOptions
            self.immutableOptions = immutableOptions
            self.deprecatedOptions = deprecatedOptions
        self.comm = comm
        self.informs = informs
        self.solverCreated = False
        self.checkDefaultOptions = checkDefaultOptions

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
        if self.checkDefaultOptions:
            try:
                defaultType, defaultValue = self.defaultOptions[name]
            except KeyError:
                if name in self.deprecatedOptions:
                    raise Error(f"Option {name} is deprecated. {self.deprecatedOptions[name]}")
                else:
                    guess = get_close_matches(name, list(self.defaultOptions.keys()), n=1, cutoff=0.0)[0]
                    raise Error(f"Option {name} is not a valid {self.name} option. Perhaps you meant {guess}?")

        # Make sure we are not trying to change an immutable option if
        # we are not allowed to.
        if self.solverCreated and name in self.immutableOptions:
            raise Error(f"Option {name} cannot be modified after the solver is created.")

        if self.checkDefaultOptions:
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
        else:
            # no error checking
            self.options[name] = value

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

        if name in self.defaultOptions or not self.checkDefaultOptions:
            if name in self.options:
                return self.options[name]
            else:
                raise Error(
                    f"Option {name} was not found. "
                    + "Because options checking has been disabled, make sure the option has been set first."
                )
        else:
            guess = get_close_matches(name, list(self.defaultOptions.keys()), n=1, cutoff=0.0)[0]
            raise Error(f"{name} is not a valid option name. Perhaps you meant {guess}?")

    def printCurrentOptions(self):
        self.printOptions()
        warnings.warn("printCurrentOptions is deprecated. Use printOptions instead.", DeprecationWarning)

    def printOptions(self):
        """
        Prints a nicely formatted dictionary of all the current solver
        options to the stdout on the root processor
        """
        self.pp("+----------------------------------------+")
        self.pp("|" + f"All {self.name} Options:".center(40) + "|")
        self.pp("+----------------------------------------+")
        options = self.getOptions()
        self.pp(options)

    def getOptions(self):
        return copy.copy(self.options)

    def getModifiedOptions(self):
        """
        Prints a nicely formatted dictionary of all the modified solver
        options to the stdout on the root processor
        """
        modifiedOptions = {}
        for key in self.options.keys():
            defaultType, defaultValue = self.defaultOptions[key]
            if defaultType is not list and isinstance(defaultValue, list):
                defaultValue = defaultValue[0]
            optionValue = self.getOption(key)
            if optionValue != defaultValue:
                modifiedOptions[key] = optionValue
        return modifiedOptions

    def printModifiedOptions(self):
        """
        Prints a nicely formatted dictionary of all the current solver
        options that have been modified from the defaults to the root
        processor
        """
        self.pp("+----------------------------------------+")
        self.pp("|" + f"All Modified {self.name} Options:".center(40) + "|")
        self.pp("+----------------------------------------+")
        modifiedOptions = self.getModifiedOptions()
        self.pp(modifiedOptions)

    def pp(self, obj, flush=True):
        """
        This method prints ``obj`` (via pprint) on the root proc of ``self.comm`` if it exists.
        Otherwise it will just print ``obj``.

        Parameters
        ----------
        obj : object
            Any Python object to be printed
        flush : bool
            If True, the stream will be flushed.
        """

        # Call the parallel safe pp routine defined in utils
        pp(obj, self.comm, flush=flush)
