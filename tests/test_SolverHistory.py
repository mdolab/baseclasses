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
import sys
import io
import unittest
import pickle
from typing import Type

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
        varType: Type,
        printVar: bool = False,
    ) -> None:
        """Check that a variable is added correctly"""

        # Check for corresponding keys in the variables and data dictionaries
        self.assertIn(name, self.solverHistory.variables)
        self.assertIn(name, self.solverHistory.data)

        # Check that the print variable is correct
        self.assertIn("print", self.solverHistory.variables[name])
        self.assertEqual(self.solverHistory.variables[name]["print"], printVar)

        # Check that the type variable is correct
        self.assertIn("type", self.solverHistory.variables[name])
        self.assertEqual(self.solverHistory.variables[name]["type"], varType)

        # If the variable is printed we should have values for the "format", "type" and "columnWidth" keys in the
        # variables dictionary, otherwiuse we should not
        if printVar:
            self.assertEqual(self.solverHistory.variables[name]["type"], varType)
            self.assertIn("format", self.solverHistory.variables[name])
            self.assertIn("columnWidth", self.solverHistory.variables[name])
        else:
            self.assertNotIn("format", self.solverHistory.variables[name])
            self.assertNotIn("columnWidth", self.solverHistory.variables[name])

    def test_addNoPrintVariable(self) -> None:
        """Check that adding a variable that is not to be printed goes as expected"""
        name = "TestVar"
        varType = float
        printVar = False
        self.solverHistory.addVariable(name, varType=varType, printVar=printVar)
        self.checkVariableAddedCorrectly(name=name, varType=varType, printVar=printVar)

    def test_addPrintVariable(self) -> None:
        """Check that adding a variable that is to be printed goes as expected"""
        self.checkVariableAddedCorrectly(name="Iter", varType=int, printVar=True)

    def test_addVariableWrongFormat(self) -> None:
        """Check that adding a variable with an invalid printing format throws an error"""
        with self.assertRaises(ValueError):
            self.solverHistory.addVariable(name="test", varType=list, printVar=True, printFormat="{:.2f}")


class TestSolverHistoryWriting(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(seed=0)
        self.solverHistory = SolverHistory()
        self.solverHistory.addVariable("Random Int", varType=int, printVar=True)
        self.solverHistory.addVariable("Random Float", varType=float, printVar=True)
        self.solverHistory.addVariable("Random String", varType=str, printVar=True)
        self.solverHistory.addVariable("Random List", varType=list, printVar=True)
        self.solverHistory.addVariable("Don't print", varType=float, printVar=False)

        self.metadata = {"Some very important metadata": "Important metadata"}
        metadataKey = list(self.metadata.keys())[0]
        self.solverHistory.addMetadata(metadataKey, self.metadata[metadataKey])

        self.numIters = 10

        for _ in range(self.numIters):
            iterData = {
                "Random Int": rng.integers(low=-100, high=100),
                "Random Float": rng.random() - 0.5,
                "Random String": str(rng.integers(low=-100, high=100)),
                "Random List": [rng.integers(low=-100, high=100)],
                "Don't print": rng.random(),
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
            metadata = self.solverHistory.getMetadata()
            with open(baseName + ".pkl", "rb") as f:
                loadedFile = pickle.load(f)
                loadedData = loadedFile["data"]
                loadedMetadata = loadedFile["metadata"]
            self.assertEqual(data, loadedData)
            self.assertEqual(metadata, loadedMetadata)
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
        for var in ["Random Int", "Random Float", "Random String", "Random List", "Don't print"]:
            self.assertEqual(data[var], [None])

        # Check metadata clearing
        self.assertEqual(self.solverHistory.getMetadata(), self.metadata)
        self.solverHistory.reset(clearMetadata=True)
        self.assertEqual(self.solverHistory.getMetadata(), {})

    def test_printHeader(self) -> None:
        """Check that the header is printed as expected"""
        capturedOutput = io.StringIO()
        sys.stdout = capturedOutput
        self.solverHistory.printHeader()
        sys.stdout = sys.__stdout__
        expectedHeader = """+-------------------------------------------------------------------------------------------------+
|  Iter   |    Time     |  Random Int  |     Random Float     |  Random String  |   Random List   |
+-------------------------------------------------------------------------------------------------+\n"""
        self.assertEqual(capturedOutput.getvalue(), expectedHeader)

    def test_printData(self) -> None:
        """Test that printing of iteration data"""

        # Test that trying to print an iteration outside the range of recorded iterations throws an error
        with self.assertRaises(ValueError):
            self.solverHistory.printData(iters=self.numIters + 1)
        with self.assertRaises(ValueError):
            self.solverHistory.printData(iters=-(self.numIters + 1))

        # Test that printing the last line works correctly
        # Need to everwrite the time values so that they are deterministic
        timeList = [0.1] * self.numIters
        timeList[0] = None
        self.solverHistory.writeFullVariableHistory(name="Time", values=timeList)
        capturedOutput = io.StringIO()
        sys.stdout = capturedOutput
        self.solverHistory.printData()
        sys.stdout = sys.__stdout__
        expectedLine = (
            "|      9  |  1.000e-01  |       37     |  -3.64903494978e-01  |       15        |      [44]       |\n"
        )
        self.assertEqual(capturedOutput.getvalue(), expectedLine)

        # Same thing but for the first iteration
        capturedOutput = io.StringIO()
        sys.stdout = capturedOutput
        self.solverHistory.printData(0)
        sys.stdout = sys.__stdout__
        expectedLine = (
            "|      0  |      -      |       70     |  -2.30213286236e-01  |       27        |      [-39]      |\n"
        )
        self.assertEqual(capturedOutput.getvalue(), expectedLine)

    def test_writeFullVariableHistory(self) -> None:
        """Test the ability to write the entire histro y of a variable in one go with various types"""
        newIntHistory = range(self.numIters)
        newIntHistoryList = list(newIntHistory)

        # Add history as a range
        self.solverHistory.writeFullVariableHistory("Random Int", newIntHistory)
        self.assertEqual(self.solverHistory.getData()["Random Int"], newIntHistoryList)

        # Add as a list
        self.solverHistory.writeFullVariableHistory("Random Int", newIntHistoryList)
        self.assertEqual(self.solverHistory.getData()["Random Int"], newIntHistoryList)

        # Add as array
        self.solverHistory.writeFullVariableHistory("Random Int", np.array(newIntHistory))
        self.assertEqual(self.solverHistory.getData()["Random Int"], newIntHistoryList)

        # Ensure that trying to write a variable that isn't being recorded throws an error
        with self.assertRaises(ValueError):
            self.solverHistory.writeFullVariableHistory("Not a Random Int", newIntHistoryList)

        # Ensure that writing with a wrong variable type throws an error
        newIntHistoryList[3] = "Not an int"
        with self.assertRaises(TypeError):
            self.solverHistory.writeFullVariableHistory("Random Int", newIntHistoryList)


if __name__ == "__main__":
    unittest.main()