import unittest
from baseclasses import BaseSolver
from baseclasses.utils import Error


class SOLVER(BaseSolver):
    def __init__(self, name, options=None, *args, **kwargs):

        """Create an artificial class for testing"""

        category = "Solver for testing BaseSolver"
        def_opts = {
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

        # Initialize the inherited BaseSolver
        super().__init__(
            name, category, def_opts, options, immutableOptions=immutableOptions, deprecatedOptions=deprecatedOptions
        )


class TestOptions(unittest.TestCase):
    def test_options(self):

        # initialize solver
        floatValue_set = 200.0
        intValue_set = 3
        options = {"floatOption": floatValue_set, "intOption": intValue_set}
        solver = SOLVER("test", options=options)

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

        # test options that accept multiple types
        testValues = ["value", {"key": "value"}]
        for multiValue_set in testValues:
            solver.setOption("multiOption", multiValue_set)
            multiValue_get = solver.getOption("multiOption")
            self.assertEqual(multiValue_set, multiValue_get)

        # test Errors
        with self.assertRaises(Error):
            solver.getOption("invalidOption")  # test name checking
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
