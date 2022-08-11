"""
==============================================================================
BaseClasses: Solver History Class
==============================================================================
@File    :   SolverHistory-New.py
@Date    :   2022/08/09
@Author  :   Alasdair Christison Gray
@Description : A general solver history class for storing values from a nonlinear solution.
"""

# ==============================================================================
# Standard Python modules
# ==============================================================================
from collections import OrderedDict
import copy
import os
import time
from typing import Optional, Type, Dict, Any, List
import pickle

# ==============================================================================
# External Python modules
# ==============================================================================
import numpy as np

# ==============================================================================
# Extension modules
# ==============================================================================


class SolverHistory(object):
    """The SolverHistory class can be used to store and print various useful values during the execution of a solver.

    NOTE: The implementation of this class contains no consideration of parallelism. If you are using a solverHistory
    object in your parallel solver, you will need to take care over which procs you make calls to the SolverHistory
    object on.

    TODO: Add ability to store arbitrary metadata
    """

    __slots__ = [
        "variables",
        "data",
        "metadata",
        "iter",
        "startTime",
        "defaultFormat",
        "testValues",
        "DEFAULT_OTHER_FORMAT",
        "DEFAULT_OTHER_VALUE",
    ]

    def __init__(self) -> None:
        # Dictionaries for storing variable information and values
        self.variables: Dict[str, Any] = OrderedDict()
        self.data: Dict[str, List] = OrderedDict()
        self.metadata: Dict[str, Any] = {}

        # Initialise iteration counter and solve start time
        self.iter: int = 0
        self.startTime: float = -1.0

        # --- Define default print formatting for some common types ---
        self.defaultFormat: Dict[Type, str] = {}
        self.testValues: Dict[Type, Any] = {}
        # float
        self.defaultFormat[float] = "{:17.11e}"
        self.testValues[float] = 0.0
        # int
        self.defaultFormat[int] = "{:5d}"
        self.testValues[int] = 0
        # str
        self.defaultFormat[str] = "{:^10}"
        self.testValues[str] = "a"
        # other
        self.DEFAULT_OTHER_FORMAT: str = "{:^10}"
        self.DEFAULT_OTHER_VALUE: str = "a"

        # Add fields for the iteration number and time, the only two variables that are always stored
        self.addVariable("Time", varType=float, printVar=True)
        self.addVariable("Iter", varType=int, printVar=True)

    def reset(self, clearMetadata: bool = False) -> None:
        """Reset the history"""

        # Reset iteration counter
        self.iter = 0

        # Reset solve start time
        self.startTime = -1.0

        # Clear recorded data
        for varName in self.data:
            self.data[varName] = []

        # Clear metadata if required
        if clearMetadata:
            self.metadata = {}

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
        self.metadata[name] = data

    def addVariable(
        self,
        name: str,
        printVar: bool = False,
        varType: Optional[Type] = None,
        printFormat: Optional[str] = None,
    ) -> None:
        """Define a new field to be stored in the history.

        Parameters
        ----------
        name : str
            Variable name
        printVar : bool, optional
            Whether to include the variable in the iteration printout, by default False
        varType : Type, optional
            Variable type, i.e int, float, str etc, used for formatting when printing, by default None, not used if
            `printVar` is False
        printFormat : str, optional
            Format string valid for use with the str.format() method (e.g "{:17.11e}" for a float or "{:03d}" for an
            int), by default None, in which case a default format for the given `varType` is used, not used if
            `printVar` is False
        """
        self.variables[name] = {"print": printVar}

        # Create variable data list
        self.data[name] = []

        # Only store variable type and string format if it's going to be printed
        if printVar:
            if varType is None:
                raise ValueError(
                    f"Type of variable {name} not supplied, must be specified if variable is to be printed"
                )
            self.variables[name]["type"] = varType
            if printFormat is not None:
                self.variables[name]["format"] = printFormat
            elif varType in self.defaultFormat:
                self.variables[name]["format"] = self.defaultFormat[varType]
                testValue = self.testValues[varType]
            else:
                self.variables[name]["format"] = self.DEFAULT_OTHER_FORMAT
                testValue = self.DEFAULT_OTHER_VALUE

            # Figure out column width, the maximum of the length of the name and the formatted value, also check that
            # the format string is valid
            try:
                testString = self.variables[name]["format"].format(testValue)
            except ValueError as e:
                raise ValueError(f"Supplied format string \"{self.variables[name]['format']}\" is invalid") from e

            dataLen = len(testString)
            nameLen = len(name)
            self.variables[name]["columnWidth"] = max(dataLen, nameLen)
            self.variables[name]["headerFormat"] = "{:^%i}" % (self.variables[name]["columnWidth"] + 4)

    def startTiming(self) -> None:
        """Record the start time of the solver

        This function only needs to be called explicitly if the start time of your solver is separate from the first
        time the `write` method is called.
        """
        self.startTime = time.time()

    def write(self, data: dict) -> None:
        """Record data for a single iteration

        Note that each call to this method is treated as a new iteration. All data to be recorded for an iteration must
        therefore be recorded in a single call to this method.

        Parameters
        ----------
        data : dict
            Dictionary of values to record, with variable names as keys
        """

        # Store time
        if self.startTime < 0.0:
            self.startTiming()
            data["Time"] = 0.0
        else:
            data["Time"] = time.time() - self.startTime

        # Store iteration number
        data["Iter"] = self.iter

        # Store data, only if the supplied data is of the correct type
        for varName in self.variables:
            if varName in data:
                value = data.pop(varName)
                if self.variables[varName]["type"] is None or type(value) == self.variables[varName]["type"]:
                    self.data[varName].append(value)
                else:
                    raise TypeError(
                        f"Variable {varName} has type {type(value)}, expected {self.variables[varName]['type']}"
                    )
            # If no data was supplied for a given variable, store a nan value
            else:
                self.data[varName].append(np.nan)

        # Any remaining entries in the data dictionary are variables that have not been defined using addVariable(), throw an error
        if len(data) > 0:
            raise ValueError(
                f"Unknown variables {data.keys()} supplied to Solution History recorder, recorded variables are {self.getVariables()}"
            )

        # Increment iteration counter
        self.iter += 1

    def writeFullVariableHistory(self, varName: str, values: list) -> None:
        pass

    def printHeader(self) -> None:
        """Print the header of the iteration printout

        The header will look something like this:

        +--------------------------------------------------------------------------...------+
        | Iter  |       Time        |       Var 1       |       Var 2       |      ...      |
        +--------------------------------------------------------------------------...------+
        """

        # Each field will be `columnWidth` characters wide plus 2 spaces each side, plus the vertical bar between each
        # field
        headerString = "|"
        for var in self.variables:
            headerString += self.variables[var]["headerFormat"].format(var)
            headerString += "|"
        headerWidth = len(headerString)

        headerBar = "+" + "-" * (headerWidth - 2) + "+"
        print(headerBar)
        print(headerString)
        print(headerBar)

    def printData(self) -> None:
        pass

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
        return copy.deepcopy(self.data)

    def getMetadata(self) -> Dict[str, Any]:
        """Get the recorded metadata

        Returns
        -------
        dict
            Dictionary of recorded metadata
        """
        return copy.deepcopy(self.metadata)

    def getVariables(self) -> List[str]:
        """Get the recorded variables

        Returns
        -------
        dict
            Dictionary of recorded variables
        """
        return list(self.variables.keys())
