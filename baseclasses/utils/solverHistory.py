"""
==============================================================================
BaseClasses: Solver History Class
==============================================================================

@Description : A general solver history class for storing values from a nonlinear solution.
"""

# ==============================================================================
# Standard Python modules
# ==============================================================================
from collections import OrderedDict
import copy
import os
import time
from typing import Optional, Type, Dict, Any, List, Iterable, Union
import pickle
import warnings


class SolverHistory(object):
    """The SolverHistory class can be used to store and print various useful values during the execution of a solver.

    NOTE: The implementation of this class contains no consideration of parallelism. If you are using a solverHistory
    object in your parallel solver, you will need to take care over which procs you make calls to the SolverHistory
    object on.
    """

    __slots__ = [
        "_variables",
        "_data",
        "_metadata",
        "_iter",
        "_startTime",
        "_defaultFormat",
        "_testValues",
        "_DEFAULT_OTHER_FORMAT",
        "_DEFAULT_OTHER_VALUE",
    ]

    def __init__(self, printIter: bool = True, printTime: bool = True) -> None:
        """Create a solver history instance

        Parameters
        ----------
        printIter : bool, optional
            Whether to include the history's internal iteration variable in the iteration printout, by default True
        printTime : bool, optional
            Whether to include the history's internal timing variable in the iteration printout, by default True
        """
        # Dictionaries for storing variable information and values
        self._variables: Dict[str, Any] = OrderedDict()
        self._data: Dict[str, List] = OrderedDict()
        self._metadata: Dict[str, Any] = {}

        # Initialise iteration counter and solve start time
        self._iter: int = 0
        self._startTime: float = -1.0

        # --- Define default print formatting for some common types ---
        self._defaultFormat: Dict[Type, str] = {}
        # Test values are used to check how wide the printed formatted values of a variable will be, so that we can make
        # sure the columns in the iteration printout are wide enough
        self._testValues: Dict[Type, Any] = {}
        # float
        self._defaultFormat[float] = "{: 17.11e}"
        self._testValues[float] = 0.0
        # complex
        self._defaultFormat[complex] = "{: 9.3e}"
        self._testValues[complex] = complex(0.0)
        # int
        self._defaultFormat[int] = "{: 5d}"
        self._testValues[int] = 0
        # str
        self._defaultFormat[str] = "{:^10}"
        self._testValues[str] = "a"
        # other
        self._DEFAULT_OTHER_FORMAT: str = "{}"
        self._DEFAULT_OTHER_VALUE: list = [2, "b", 3.0]

        # Add fields for the iteration number and time, the only two variables that are always stored
        self.addVariable("Iter", varType=int, printVar=printIter)
        self.addVariable("Time", varType=float, printVar=printTime, printFormat="{:9.3e}")

    def reset(self, clearMetadata: bool = False) -> None:
        """Reset the history to its initial state.

        Parameters
        ----------
        clearMetadata : bool, optional
            Whether to clear the metadata too, by default False
        """ """"""

        # Reset iteration counter
        self._iter = 0

        # Reset solve start time
        self._startTime = -1.0

        # Clear recorded data
        for varName in self._data:
            self._data[varName] = []

        # Clear metadata if required
        if clearMetadata:
            self._metadata = {}

    def addMetadata(self, name: str, data: Any) -> None:
        """Add a piece of metadata to the history

        The metadata attribute is simply a dictionary that can be used to store arbitrary information related to the
        solution being recorded, e.g solver options

        Parameters
        ----------
        name : str
            Item name/key
        data : Any
            Item to store
        """
        self._metadata[name] = data

    def addVariable(
        self,
        name: str,
        varType: Type,
        printVar: bool = False,
        printFormat: Optional[str] = None,
        overwrite: bool = False,
    ) -> None:
        """Define a new field to be stored in the history.

        Parameters
        ----------
        name : str
            Variable name
        varType : Type
            Variable type, i.e int, float, str etc
        printVar : bool, optional
            Whether to include the variable in the iteration printout, by default False
        printFormat : str, optional
            Format string valid for use with the str.format() method (e.g "{:17.11e}" for a float or "{:03d}" for an
            int), only important for variables that are to be printed, by default a predefined format for the given
            `varType` is used
        overwrite : bool, optional
            Whether to overwrite any existing variables with the same name, by default False
        """

        if name not in self._variables or overwrite:
            self._variables[name] = {"print": printVar, "type": varType}

            # Create variable data list
            self._data[name] = []

            # Only store variable's string format if it's going to be printed
            if printVar:
                if printFormat is not None:
                    self._variables[name]["format"] = printFormat
                elif varType in self._defaultFormat:
                    self._variables[name]["format"] = self._defaultFormat[varType]
                else:
                    self._variables[name]["format"] = self._DEFAULT_OTHER_FORMAT

                # Get test value for figuring out how long a string is using the supplied format
                try:
                    testValue = self._testValues[varType]
                except KeyError:
                    testValue = self._DEFAULT_OTHER_VALUE

                # Figure out column width, the maximum of the length of the name and the formatted value, also check
                # that the format string is valid
                try:
                    testString = self._variables[name]["format"].format(testValue)
                except (ValueError, TypeError) as e:
                    raise ValueError(f"Supplied format string \"{self._variables[name]['format']}\" is invalid") from e

                dataLen = len(testString)
                nameLen = len(name)
                self._variables[name]["columnWidth"] = max(dataLen, nameLen)

                # --- Now figure out the format strings for the iteration printout header and values ---
                # The header is simply centred in the available width, which is actually columnWidth + 4
                self._variables[name]["headerFormat"] = f"{{:^{(self._variables[name]['columnWidth'] + 4)}s}}"
            else:
                warnings.warn(f"Variable '{name}' already defined, set `overwrite=True` to overwrite")

    def startTiming(self) -> None:
        """Record the start time of the solver

        This function only needs to be called explicitly if the start time of your solver is separate from the first
        time the `write` method is called.
        """
        self._startTime = time.time()

    def write(self, data: dict) -> None:
        """Record data for a single iteration

        Note that each call to this method is treated as a new iteration. All data to be recorded for a single solver
        iteration must therefore be recorded in a single call to this method.

        Parameters
        ----------
        data : dict
            Dictionary of values to record, with variable names as keys
        """

        # Store time
        if self._startTime < 0.0:
            self.startTiming()
            data["Time"] = 0.0
        else:
            data["Time"] = time.time() - self._startTime

        # Store iteration number
        data["Iter"] = self._iter

        # Store data, only if the supplied data can be converted to the correct type
        for varName in self._variables:
            if varName in data:
                value = data.pop(varName)
                try:
                    convertedValue = None if value is None else self._variables[varName]["type"](value)
                    self._data[varName].append(convertedValue)
                except ValueError as e:
                    raise TypeError(
                        f"Value '{value}' provided for variable '{varName}' could not be converted to the type declared for this variable: {self._variables[varName]['type']}"
                    ) from e
            # If no data was supplied for a given variable, store a None
            else:
                self._data[varName].append(None)

        # Any remaining entries in the data dictionary are variables that have not been defined using addVariable(), throw an error
        if len(data) > 0:
            raise ValueError(
                f"Unknown variables {data.keys()} supplied to Solution History recorder, recorded variables are {self.getVariables()}"
            )

        # Increment iteration counter
        self._iter += 1

    def writeFullVariableHistory(self, name: str, values: Iterable) -> None:
        """Write the entire history of a variable in one go

        This function should be used in the case where your solver already handles the recording of variables during a
        solution (e.g ADflow) but you want to use a SolverHistory object to facilitate writing it to a file

        Parameters
        ----------
        name : str
            Variable name
        values : Iterable
            Values to record, will be converted to a list
        """
        if name not in self._variables:
            raise ValueError(
                f"Unknown variables {name} supplied to Solution History recorder, recorded variables are {self.getVariables()}"
            )
        try:
            self._data[name] = [None if v is None else self._variables[name]["type"](v) for v in values]
        except ValueError as e:
            raise TypeError(
                f"A value provided for variable '{name}' could not be converted to the type declared for this variable: {self._variables[name]['type']}"
            ) from e

    def printHeader(self) -> None:
        """Print the header of the iteration printout

        The header will look something like this:

        .. code-block:: text

            +--------------------------------------------------------------------------...------+
            | Iter  |       Time        |       Var 1       |       Var 2       |      ...      |
            +--------------------------------------------------------------------------...------+

        """

        # Each field will be `columnWidth` characters wide plus 2 spaces each side, plus the vertical bar between each
        # field
        headerString = "|"
        for varName in self._variablesToPrint:
            headerString += self._variables[varName]["headerFormat"].format(varName)
            headerString += "|"
        headerWidth = len(headerString)

        headerBar = "+" + "-" * (headerWidth - 2) + "+"
        print(headerBar)
        print(headerString)
        print(headerBar)

    def printData(self, iters: Optional[Union[int, Iterable[int]]] = None) -> None:
        """Print a selection of lines from the history

        Parameters
        ----------
        iters : int or Iterable of ints, optional
            Iteration numbers to print, by default only the last iteration will be printed
        """
        if iters is None:
            iters = [-1]
        elif isinstance(iters, int):
            iters = [iters]

        if max(iters) >= self._iter or min(iters) < -self._iter:
            if max(iters) >= self._iter:
                badIter = max(iters)
            else:
                badIter = min(iters)
            raise ValueError(
                f"Requested iteration {badIter} is not in the history, only {self._iter} iterations in history"
            )

        for i in iters:
            lineString = "|"
            for varName in self._variablesToPrint:
                if self._data[varName][i] is None:
                    lineString += self._variables[varName]["headerFormat"].format("-")
                else:
                    valueString = self._variables[varName]["format"].format(self._data[varName][i])
                    lineString += self._variables[varName]["headerFormat"].format(valueString)
                lineString += "|"
            print(lineString)

    def save(self, fileName: str) -> None:
        """Write the solution history to a pickle file

        Only the data dictionary is saved

        Parameters
        ----------
        fileName : str
            File path to save the solution history to, file extension not required, will be ignored if supplied
        """
        base = os.path.splitext(fileName)[0]
        fileName = base + ".pkl"

        dataToSave = {"data": self.getData(), "metadata": self.getMetadata()}
        with open(fileName, "wb") as file:
            pickle.dump(dataToSave, file, protocol=pickle.HIGHEST_PROTOCOL)

    def getData(self) -> Dict[str, List]:
        """Get the recorded data

        Returns
        -------
        dict
            Dictionary of recorded data
        """
        return copy.deepcopy(self._data)

    def getMetadata(self) -> Dict[str, Any]:
        """Get the recorded metadata

        Returns
        -------
        dict
            Dictionary of recorded metadata
        """
        return copy.deepcopy(self._metadata)

    def getVariables(self) -> List[str]:
        """Get the recorded variables

        Returns
        -------
        dict
            Dictionary of recorded variables
        """
        return list(self._variables.keys())

    @property
    def _variablesToPrint(self) -> List[str]:
        """Get the variables to print

        Returns
        -------
        list
            List of variables to print
        """
        return [varName for varName in self._variables if self._variables[varName]["print"]]
