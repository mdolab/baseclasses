"""
==============================================================================
Solver History unit tests
==============================================================================
@File    :   test_SolverHistory.py
@Date    :   2022/08/10
@Author  :   Alasdair Christison Gray
@Description :
"""

# ==============================================================================
# Standard Python modules
# ==============================================================================
import os
import random
import unittest
import pickle
from typing import Optional, Type

# ==============================================================================
# External Python modules
# ==============================================================================
import numpy as np

# ==============================================================================
# Extension modules
# ==============================================================================
from baseclasses.utils import SolverHistory


class TestSolverHistoryVariableAdding(unittest.TestCase):
    def setUp(self):
        self.solverHistory = SolverHistory()

    def checkVariableAddedCorrectly(
        self,
        name: str,
        printVar: bool = False,
        varType: Optional[Type] = None,
    ) -> None:
        """Check that a variable is added correctly"""

        # Check for corresponding keys in the variables and data dictionaries
        self.assertIn(name, self.solverHistory.variables)
        self.assertIn(name, self.solverHistory.data)

        # Check that the print variable is correct
        self.assertIn("print", self.solverHistory.variables[name])
        self.assertEqual(self.solverHistory.variables[name]["print"], printVar)

        # If the variable is printed we should have values for the "format", "type" and "columnWidth" keys in the
        # variables dictionary, otherwiuse we should not
        if printVar:
            self.assertIn("type", self.solverHistory.variables[name])
            self.assertEqual(self.solverHistory.variables[name]["type"], varType)
            self.assertIn("format", self.solverHistory.variables[name])
            self.assertIn("columnWidth", self.solverHistory.variables[name])
        else:
            self.assertNotIn("type", self.solverHistory.variables[name])
            self.assertNotIn("format", self.solverHistory.variables[name])
            self.assertNotIn("columnWidth", self.solverHistory.variables[name])

    def test_addNoPrintVariable(self) -> None:
        """Check that adding a variable that is not to be printed goes as expected"""
        name = "TestVar"
        varType = float
        printVar = False
        self.solverHistory.addVariable(name, varType=varType, printVar=printVar)
        self.checkVariableAddedCorrectly(name, printVar, varType)

    def test_addPrintVariable(self) -> None:
        """Check that adding a variable that is to be printed goes as expected"""
        self.checkVariableAddedCorrectly(name="Iter", printVar=True, varType=int)

    def test_addPrintVariableWithNoType(self) -> None:
        """Make sure that addVariable throws an error if you try to add a printed variable without giving a type"""
        self.assertRaises(ValueError, self.solverHistory.addVariable, "TestVar", printVar=True)


class TestSolverHistoryWriting(unittest.TestCase):
    def setUp(self):
        self.solverHistory = SolverHistory()
        self.solverHistory.addVariable("Random Int", varType=int, printVar=True)
        self.solverHistory.addVariable("Random Float", varType=float, printVar=True)
        self.solverHistory.addVariable("Random String", varType=str, printVar=True)
        self.solverHistory.addVariable("Random List", varType=list, printVar=True)

        self.numIters = 10

        for _ in range(self.numIters):
            iterData = {
                "Random Int": random.randint(0, 10),
                "Random Float": np.random.rand(),
                "Random String": str(random.randint(0, 10)),
                "Random List": [random.randint(0, 10)],
            }
            self.solverHistory.write(iterData)

    def test_dataListLength(self) -> None:
        """Check that the data list has the correct length"""
        for var in self.solverHistory.variables:
            self.assertEqual(len(self.solverHistory.data[var]), self.numIters)

    def test_writeWrongVariableType(self) -> None:
        """Check that writing with a wrong variable type throws an error"""
        self.assertRaises(TypeError, self.solverHistory.write, {"Random Int": "Not an int"})

    def test_writeExtraVariables(self) -> None:
        """Check that trying to write an extra variable"""
        self.assertRaises(
            ValueError, self.solverHistory.write, {"Random Int": 90, "Extra Variable": "Some other value"}
        )

    def test_getData(self) -> None:
        """Test the getData returns a copy of the recorded data"""
        data = self.solverHistory.getData()
        self.assertEqual(data, self.solverHistory.data)

        data["NewKey"] = 10
        self.assertNotEqual(data, self.solverHistory.data)

    def test_saveData(self) -> None:
        """Check that the data saved to a file is the same as that returned by getData"""
        baseName = "TestData"
        self.solverHistory.save(baseName)
        try:
            data = self.solverHistory.getData()
            with open(baseName + ".pkl", "rb") as f:
                loadedData = pickle.load(f)
            self.assertEqual(data, loadedData)
        finally:
            os.remove(baseName + ".pkl")

    def test_historyReset(self) -> None:
        """Check that the history is reset correctly"""
        self.solverHistory.reset()
        self.assertEqual(self.solverHistory.iter, 0)
        self.assertTrue(self.solverHistory.startTime < 0.0)
        for var in self.solverHistory.variables:
            self.assertEqual(self.solverHistory.data[var], [])
        self.solverHistory.write({})
        data = self.solverHistory.getData()
        self.assertEqual(data["Iter"], [0])
        self.assertEqual(data["Time"], [0.0])
        for var in ["Random Int", "Random Float", "Random String", "Random List"]:
            self.assertEqual(data[var], [np.nan])


if __name__ == "__main__":
    unittest.main()
