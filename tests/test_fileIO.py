import unittest
import os
from parameterized import parameterized
from baseclasses.testing.decorators import require_mpi
from baseclasses.testing.assertions import assert_equal
from baseclasses.utils import readPickle, writePickle, readJSON, writeJSON
import numpy as np

try:
    from mpi4py import MPI
except ImportError:
    MPI = None

a_dict = {"a": 1, "b": 2}
a_set = {"a", "b", "c"}
a_numpy_array = np.array([1.2, 3.4])
a_numpy_dict = {"a": a_numpy_array}


class TestFileIO(unittest.TestCase):
    N_PROCS = 1

    def setUp(self):
        if MPI is not None:
            self.comm = MPI.COMM_WORLD
        else:
            self.comm = None

    @parameterized.expand(
        [
            ("dict", a_dict),
            ("set", a_set),
            ("array", a_numpy_array),
        ]
    )
    @require_mpi
    def test_pickle(self, name, obj):
        self.fileName = f"{name}.pkl"
        writePickle(self.fileName, obj, comm=self.comm)
        newObj = readPickle(self.fileName, comm=self.comm)
        assert_equal(obj, newObj)

    @parameterized.expand(
        [
            ("dict", a_dict),
            ("array", a_numpy_dict),
        ]
    )
    @require_mpi
    def test_JSON(self, name, obj):
        self.fileName = f"{name}.json"
        writeJSON(self.fileName, obj, comm=self.comm)
        newObj = readJSON(self.fileName, comm=self.comm)
        assert_equal(obj, newObj)

    def tearDown(self):
        if self.comm.rank == 0:
            os.remove(self.fileName)
