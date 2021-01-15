try:
    from mpi4py import MPI
except ImportError:
    MPI = None

import unittest
from baseclasses import BaseSolver
from baseclasses.utils import Error


class SOLVER(BaseSolver):
    def __init__(self, name, options={}, comm=None, checkDefaultOptions=True, caseSensitiveOptions=False):

        """Create an artificial class for testing"""

        category = "Solver for testing BaseSolver"
        defaultOptions = {
            "boolOption": [bool, True],
            "floatOption": [float, 10.0],
            "intOption": [int, [1, 2, 3]],
            "strOption": [str, ["str1", "str2", "str3"]],
            "listOption": [list, []],
            "multiOption": [(str, dict), {}],
        }
        immutableOptions = {"strOption"}
        deprecatedOptions = {
            "oldOption": "Use boolOption instead.",
        }

        informs = {
            -1: "Failure -1",
            0: "Success",
            1: "Failure 1",
        }

        # Initialize the inherited BaseSolver
        super().__init__(
            name,
            category,
            defaultOptions=defaultOptions,
            options=options,
            immutableOptions=immutableOptions,
            deprecatedOptions=deprecatedOptions,
            comm=comm,
            informs=informs,
            checkDefaultOptions=checkDefaultOptions,
            caseSensitiveOptions=caseSensitiveOptions,
        )


class TestOptions(unittest.TestCase):
    def test_options(self):

        # initialize solver
        floatValue_set = 200.0
        intValue_set = 3
        options = {"floatOption": floatValue_set, "intOption": intValue_set}
        solver = SOLVER("test", options=options)
        solver.printCurrentOptions()

        # test getOption for initialized option
        floatValue_get = solver.getOption("floatOption")
        self.assertEqual(floatValue_set, floatValue_get)

        # test getOption for default option
        strValue_get = solver.getOption("strOption")
        self.assertEqual("str1", strValue_get)

        # test CaseInsensitiveDict
        intValue_get1 = solver.getOption("intoption")
        intValue_get2 = solver.getOption("INTOPTION")
        self.assertEqual(intValue_get1, intValue_get2)

        # test setOption
        solver.setOption("boolOption", False)
        boolValue_get = solver.getOption("boolOption")
        self.assertEqual(False, boolValue_get)

        # test List type options
        listValue_get = solver.getOption("listOption")
        self.assertEqual([], listValue_get)
        listValue_set = [1, 2, 3]
        solver.setOption("listOption", listValue_set)
        listValue_get = solver.getOption("listOption")
        self.assertEqual(listValue_set, listValue_get)
        solver.printModifiedOptions()

        # test options that accept multiple types
        testValues = ["value", {"key": "value"}]
        for multiValue_set in testValues:
            solver.setOption("multiOption", multiValue_set)
            multiValue_get = solver.getOption("multiOption")
            self.assertEqual(multiValue_set, multiValue_get)

        # test Errors
        with self.assertRaises(Error) as context:
            solver.getOption("invalidOption")  # test invalid option in getOption
        self.assertTrue("intoption" in context.exception.message)  # check that intoption is offered as a suggestion
        with self.assertRaises(Error) as context:
            solver.setOption("invalidOption", 1)  # test invalid option in setOption
        self.assertTrue("intoption" in context.exception.message)  # check that intoption is offered as a suggestion
        with self.assertRaises(Error):
            solver.setOption("intOption", 4)  # test value not in list
        with self.assertRaises(Error):
            solver.setOption("intOption", "3")  # test type checking with list
        with self.assertRaises(Error):
            solver.setOption("floatOption", 4)  # test type checking without list
        with self.assertRaises(Error):
            solver.setOption("strOPTION", "str2")  # test  immutableOptions
        with self.assertRaises(Error):
            solver.setOption("oldoption", 4)  # test deprecatedOptions

    def test_checkDefaultOptions(self):
        # initialize solver
        solver = SOLVER("test", checkDefaultOptions=False)
        solver.setOption("newOption", 1)
        self.assertEqual(solver.getOption("newOption"), 1)
        with self.assertRaises(Error):
            solver.getOption("nonexistant option")  # test that this name should be rejected

    def test_caseSensitive(self):
        # initialize solver
        solver = SOLVER("test", caseSensitiveOptions=True)
        with self.assertRaises(Error):
            solver.getOption("booloption")  # test that this name should be rejected


class TestComm(unittest.TestCase):

    N_PROCS = 2

    @unittest.skipIf(MPI is None, "mpi4py not imported")
    def test_comm_with_mpi(self):
        # initialize solver
        solver = SOLVER("testComm", comm=MPI.COMM_WORLD)
        self.assertFalse(solver.comm is None)
        solver.printCurrentOptions()

    def test_comm_without_mpi(self):
        # initialize solver
        solver = SOLVER("testComm", comm=None)
        self.assertTrue(solver.comm is None)
        solver.printCurrentOptions()


class TestInforms(unittest.TestCase):
    def test_informs(self):
        solver = SOLVER("testInforms")
        self.assertEqual(solver.informs[0], "Success")
