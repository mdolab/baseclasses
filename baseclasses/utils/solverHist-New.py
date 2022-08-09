"""
==============================================================================
BaseClasses: Solver History Class
==============================================================================
@File    :   solverHist-New.py
@Date    :   2022/08/09
@Author  :   Alasdair Christison Gray
@Description : A general solver history class for storing values from a nonlinear solution.
"""

# ==============================================================================
# Standard Python modules
# ==============================================================================
from collections import OrderedDict
from warnings import warn
import copy
import os
import time
from typing import Optional, Type, Dict, Any
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
    """

    def __init__(self) -> None:
        # Dictionaries for storing variable information and values
        self.variables: Dict = OrderedDict()
        self.data: Dict = OrderedDict()

        # Initialise iteration counter and solve start time
        self.iter: int = 0
        self.startTime: float = -1.0

        # Add fields for the iteration number and time, the only two variables that are always stored
        self.addVariable("Time", varType=float, printVar=True)
        self.addVariable("Iter", varType=int, printVar=True)

        # --- Define default print formatting for some common types ---
        self.defaultFormat: Dict[Type, str] = {}
        self.testValues: Dict[Type, Any] = {}
        # float
        self.defaultFormat[float] = "{:17.11e}"
        self.testValues[float] = 0.0
        # int
        self.defaultFormat[int] = "{:04d}"
        self.testValues[int] = 0
        # str
        self.defaultFormat[str] = "{:^10}"
        self.testValues[str] = "a"
        # other
        self.DEFAULT_OTHER_FORMAT: str = "{:^10}"
        self.DEFAULT_OTHER_VALUE: str = "a"

        self.__slots__ = [
            "variables",
            "data",
            "iter",
            "startTime",
            "defaultFormat",
            "testValues",
            "DEFAULT_OTHER_FORMAT",
            "DEFAULT_OTHER_VALUE",
        ]

    def reset(self) -> None:
        """Reset the history"""

        # Reset iteration counter
        self.iter = 0

        # Reset solve start time
        self.startTime = -1.0

        # Clear recorded data
        for varName in self.data:
            self.data[varName] = []

    def addVariable(
        self,
        name: str,
        varType: Optional[Type] = None,
        printVar: bool = False,
        valueFormat: Optional[str] = None,
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
        valueFormat : str, optional
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
            if valueFormat is not None:
                self.variables[name]["format"] = valueFormat
            elif varType in self.defaultFormat:
                self.variables[name]["format"] = self.defaultFormat[varType]
                testValue = self.testValues[varType]
            else:
                self.variables[name]["format"] = self.DEFAULT_OTHER_FORMAT
                testValue = self.DEFAULT_OTHER_VALUE

            # --- Figure out column width, the maximum of the length of the name and the formatted value ---
            testString = self.variables[name]["format"].format(testValue)
            dataLen = len(testString)
            nameLen = len(name)
            self.variables[name]["format"]["columnWidth"] = max(dataLen, nameLen)

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

        if self.startTime < 0.0:
            self.startTiming()

        # Store time
        self.data["Time"].append(time.time() - self.startTime)

        # Increment iteration counter
        self.iter += 1

        # Store iteration number
        self.data["Iter"].append(self.iter)

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
                f"Unknown variables {data.keys()} supplied to Solution History recorder, recorded variables are {self.variables.keys()}"
            )

    def writeFullVariableHistory(self, varName: str, values: list) -> None:
        pass

    def printHeader(self) -> None:
        pass

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
        with open(fileName, "wb") as file:
            pickle.dump(self.data, file, protocol=pickle.HIGHEST_PROTOCOL)
