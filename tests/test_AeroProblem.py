"""
==============================================================================
Aero Problem unit tests
==============================================================================
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
from baseclasses.problems import AeroProblem
from baseclasses.utils import Error as baseclassesError


class TestAeroProblem(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(1)
        self.ap = AeroProblem(
            "ONERAM6",
            mach=0.84,
            alpha=3.06,
            reynolds=11.71e6,
            reynoldsLength=0.646,
            chordRef=0.646,
            areaRef=0.75750,
            T=26.85,  # 540 R in C
            evalFuncs=["cl", "cd", "cmz"],
        )

        # Keep track of the design variables we can and can't add to the AeroProblem
        self.DVs = {}
        self.invalidDVs = []

        for dv in self.ap.possibleDVs:
            if dv in self.ap.fullState and dv not in self.ap.inputs:
                self.invalidDVs.append(dv)
            else:
                value = self.rng.random()
                name = dv.upper()
                self.DVs[dv] = {"value": value, "name": name}

        for dv in self.ap.possibleBCDVs:
            value = self.rng.random()
            name = dv.upper()
            self.ap.setBCVar(varName=dv, value=value, familyName="familyName")
            self.DVs[dv] = {"value": value, "name": name, "family": "familyName"}

    def addDesignVariables(self):
        for dv in self.DVs:
            if "family" in self.DVs[dv]:
                self.ap.addDV(dv, self.DVs[dv]["value"], name=self.DVs[dv]["name"], family=self.DVs[dv]["family"])
            else:
                self.ap.addDV(dv, self.DVs[dv]["value"], name=self.DVs[dv]["name"])

    def test_addInvalidDV(self):
        """Ensure that an error is raised if we try setting a flight condition DV that wasn't specified in the constructor"""
        for dv in self.invalidDVs:
            with self.subTest(f"Testing `addDV` for {dv} variable", dv=dv):
                self.assertRaises(baseclassesError, self.ap.addDV, dv, self.rng.random())

    def test_addNonexistentDV(self):
        """Ensure that an error is raised if we try setting a DV that doesn't exist"""
        self.assertRaises(ValueError, self.ap.addDV, "nonexistentDV", self.rng.random())

    # Test that the DVs added to the AeroProblem exist in the dictionary returned by getDesignVars and that the values are correct
    def test_addValidDV(self):
        self.addDesignVariables()
        dvs = self.ap.getDesignVars()
        for dv in self.DVs:
            with self.subTest(f"Testing `addDV` for {dv} variable", dv=dv):
                dvName = self.DVs[dv]["name"]
                self.assertIn(dvName, dvs, msg=f"{dv} not in DVs returned by getDesignVars")
                self.assertEqual(self.DVs[dv]["value"], dvs[dvName], msg=f"{dvName} DV value is incorrect")

    def test_setDV(self):
        self.addDesignVariables()
        # Create and set new design variables
        newDVs = {}
        for dv in self.DVs:
            newDVs[self.DVs[dv]["name"]] = self.rng.random()

        self.ap.setDesignVars(newDVs)
        setDVs = self.ap.getDesignVars()
        for dv in self.DVs:
            with self.subTest(f"Testing `setDesignVars` for {dv} variable", dv=dv):
                dvName = self.DVs[dv]["name"]
                self.assertEqual(newDVs[dvName], setDVs[dvName], msg=f"{dv} DV value is incorrect")


if __name__ == "__main__":
    unittest.main()
