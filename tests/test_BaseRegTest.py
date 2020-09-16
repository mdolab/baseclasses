import os
import unittest
import copy
import numpy as np
from mpi4py import MPI
from baseclasses import BaseRegTest
from baseclasses.BaseRegTest import getTol


comm = MPI.COMM_WORLD
baseDir = os.path.dirname(os.path.abspath(__file__))
# this is the dictionary of values to be added
root_vals = {"scalar": 1.0}
root_vals_ref = copy.copy(root_vals)
root_vals["simple dictionary"] = {"a": 1.0}
root_vals["nested dictionary"] = {"a": {"b": 1.0, "c": 2.0}}
# this is the dictionary of reference values
# note that the format is different, because when we recursively add dictionaries we just modify the key
# and flatten it, instead of storing them as nested dictionaries in JSON
root_vals_ref["simple dictionary: a"] = 1.0
root_vals_ref["nested dictionary: a: b"] = 1.0
root_vals_ref["nested dictionary: a: c"] = 2.0

# this is the dictionary for parallel tests
par_vals = {
    "par val": [0.5, 1.5],
    "par sum": 0.5 + 1.5,
    "par norm": np.sqrt(2.5),
}


def regression_test_root(handler):
    """
    This function adds values for the root proc
    """
    for key, val in root_vals.items():
        if isinstance(val, dict):
            handler.root_add_dict(key, val)
        elif isinstance(val, (float, int)):
            handler.root_add_val(key, val)


def regression_test_par(handler):
    """
    This function adds values in parallel
    """
    val = comm.rank + 0.5
    handler.par_add_val("par val", val)
    handler.par_add_sum("par sum", val)
    handler.par_add_norm("par norm", val)


class TestBaseRegTest(unittest.TestCase):
    N_PROCS = 2

    def test_tol(self):
        """
        Test that the getTol function
        """
        x = 1e-1
        y = 1e-2
        c = 1e-3
        d = 1e-12
        r, a = getTol(atol=x, rtol=y)
        self.assertEqual(a, x)
        self.assertEqual(r, y)
        r, a = getTol(atol=c)
        self.assertEqual(a, c)
        self.assertEqual(r, d)
        r, a = getTol(rtol=c)
        self.assertEqual(a, d)
        self.assertEqual(r, c)
        r, a = getTol(tol=c)
        self.assertEqual(a, c)
        self.assertEqual(r, c)

    def test_train_then_test_root(self):
        """
        Test for adding values to the root, both in training and in testing
        Also tests read/write in the process
        """
        fileName = os.path.join(baseDir, "test_root.ref")
        handler = BaseRegTest(fileName, train=True)
        regression_test_root(handler)
        handler.writeRef()
        test_vals = handler.readRef()
        # self.assertEqual(test_vals, root_vals_ref)
        handler.root_print(test_vals)
        handler.root_print(root_vals_ref)
        handler = BaseRegTest(fileName, train=False)
        regression_test_root(handler)

    def test_train_then_test_par(self):
        """
        Test for adding values in parallel, both in training and in testing
        Also tests read/write in the process
        """
        fileName = os.path.join(baseDir, "test_par.ref")
        handler = BaseRegTest(fileName, train=True)
        regression_test_par(handler)
        handler.writeRef()
        test_vals = handler.readRef()
        self.assertEqual(test_vals, par_vals)
        handler = BaseRegTest(fileName, train=False)
        regression_test_par(handler)
