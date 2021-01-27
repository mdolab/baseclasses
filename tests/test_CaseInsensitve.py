import unittest
from baseclasses.utils import CaseInsensitiveDict, CaseInsensitiveSet
from parameterized import parameterized

try:
    from mpi4py import MPI
except ImportError:
    MPI = None

value1 = 123
value2 = 321
value3 = 132


class TestCaseInsensitiveDict(unittest.TestCase):
    def setUp(self):
        self.d = CaseInsensitiveDict({"OPtion1": value1})
        self.d2 = CaseInsensitiveDict({"opTION1": value2, "optioN2": value2})
        self.d3 = CaseInsensitiveDict({"OPTION3": value3})
        self.d4 = {"regular dict": 1}

    def test_get(self):
        # test __getitem__
        self.assertEqual(self.d["OPTION1"], value1)
        with self.assertRaises(KeyError):
            self.d["INVALID"]
        # test get()
        self.assertEqual(self.d.get("OPTION1"), value1)
        self.assertEqual(self.d.get("INVALID"), None)
        self.assertEqual(self.d.get("INVALID", value2), value2)

    def test_set(self):
        # update value
        self.d["OPTION1"] = value2
        self.assertEqual(self.d["option1"], value2)
        self.assertEqual({"OPtion1"}, set(self.d.keys()))  # old capitalization is preserved on key update
        # add new key
        self.d["OPTION2"] = value2
        self.assertEqual(self.d["option2"], value2)
        # update value with another capitalization
        self.d["OPtion2"] = value1
        self.assertEqual({"OPtion1", "OPTION2"}, set(self.d.keys()))  # old capitalization is preserved on key update

    def test_contains(self):
        self.assertIn("Option1", self.d)
        self.d["optioN2"] = value1
        # check case insensitive contain
        self.assertIn("OPTION2", self.d)
        self.assertNotIn("INVALID", self.d)

    def test_del(self):
        # test __del__
        del self.d["option1"]
        self.assertNotIn("option1", self.d)

    def test_len(self):
        self.assertEqual(len(self.d2), 2)
        self.d2["Option3"] = value3
        self.assertEqual(len(self.d2), 3)

    def test_pop(self):
        self.d2.pop("option2")
        self.assertEqual(len(self.d2), 1)
        with self.assertRaises(KeyError):
            self.d2.pop("INVALID")

    def test_update(self):
        # test update()
        self.d.update(self.d2)
        self.assertEqual(len(self.d), 2)
        self.assertIn("option2", self.d)
        self.assertEqual(self.d["Option2"], value2)
        # make sure original capitalization is preserved
        self.assertEqual(set(self.d.keys()), {"OPtion1", "optioN2"})

    def test_update_dict_with_regular_dict(self):
        # test regular dict update
        self.d.update(self.d4)
        self.assertTrue(isinstance(self.d, CaseInsensitiveDict))
        self.assertIn("REGULAR DICT", self.d)
        # check update preserves old capitalization
        self.assertEqual(set(self.d.keys()), {"OPtion1", "regular dict"})

    def test_update_regular_dict_with_dict(self):
        # update regular dict with this dict
        self.d4.update(self.d)
        self.assertFalse(isinstance(self.d4, CaseInsensitiveDict))
        self.assertTrue(isinstance(self.d4, dict))
        self.assertNotIn("REGULAR DICT", self.d4)  # d3 is a dict and is not case insensitive
        self.assertIn("regular dict", self.d4)  # this works

    def test_equal(self):
        # test case insensitive comparison
        d = CaseInsensitiveDict({"opTIon1": value1})
        self.assertEqual(d, self.d)


class TestCaseInsensitiveSet(unittest.TestCase):
    def setUp(self):
        self.s = CaseInsensitiveSet({"Option1"})
        self.s2 = CaseInsensitiveSet({"OPTION1", "opTION2"})
        self.s4 = {"regular set"}

    def test_add_contains(self):
        # test __contains__ and add()
        self.assertIn("OPTION1", self.s)
        # test original capitalization is preserved on initialization
        self.assertEqual({"Option1"}, self.s._getKeys())
        self.s.add("OPTION2")
        self.assertIn("option2", self.s)
        # now add the same key again with different capitalization
        self.s.add("option2")
        self.assertNotIn("option2", self.s._getKeys())
        self.assertIn("OPTION2", self.s._getKeys())
        # test original capitalization is preserved on new item
        self.assertEqual({"Option1", "OPTION2"}, self.s._getKeys())

    def test_len(self):
        self.assertEqual(len(self.s2), 2)
        self.s2.remove("Option2")
        self.assertEqual(len(self.s2), 1)

    def test_update(self):
        # test update()
        self.s.update(self.s2)
        self.assertTrue(isinstance(self.s, CaseInsensitiveSet))
        self.assertEqual(len(self.s), 2)
        self.assertEqual(self.s._getKeys(), {"Option1", "opTION2"})

    def test_update_with_regular_set(self):
        # test regular set update
        self.s.update(self.s4)
        self.assertTrue(isinstance(self.s, CaseInsensitiveSet))
        self.assertIn("REGULAR SET", self.s)
        self.assertEqual({"Option1", "regular set"}, self.s._getKeys())

    def test_update_regular_set_with_set(self):
        self.s4.update(self.s)
        self.assertFalse(isinstance(self.s4, CaseInsensitiveSet))
        self.assertTrue(isinstance(self.s4, set))
        self.assertNotIn("REGULAR SET", self.s4)  # s4 is a set and is not case insensitive
        self.assertIn("regular set", self.s4)  # this works
        self.assertEqual(self.s4, {"Option1", "regular set"})

    def test_subsets(self):
        # test set operations
        self.assertFalse(self.s2.issubset(self.s))
        self.s.update(self.s2)
        self.assertTrue(self.s2.issubset(self.s))
        self.assertFalse({"Option2"}.issubset(self.s))  # set is case sensitive so this should fail
        self.assertTrue(CaseInsensitiveSet({"Option2"}).issubset(self.s))  # and this should pass

    def test_union(self):
        s3 = self.s.union(self.s2)
        self.assertTrue(isinstance(s3, CaseInsensitiveSet))
        self.assertEqual(s3, CaseInsensitiveSet({"option1", "option2"}))
        # NOTE capitalization is NOT guaranteed since union is transitive!
        # we only guarantee the entries are there, but for duplicate keys the capitalization can be from either

    def test_remove(self):
        # test remove
        with self.assertRaises(KeyError):
            self.s2.remove("INVALID")
        self.s2.remove("option2")
        self.assertNotIn("OPTION2", self.s2)
        self.assertEqual(len(self.s2), 1)

    def test_equal(self):
        self.assertNotEqual(self.s, self.s2)
        self.s2.remove("opTION2")
        self.assertEqual(self.s, self.s2)


class TestParallel(unittest.TestCase):
    N_PROCS = 2

    @unittest.skipIf(MPI is None, "mpi4py not imported")
    @parameterized.expand(["CaseInsensitiveDict", "CaseInsensitiveSet"])
    def test_bcast(self, class_type):
        comm = MPI.COMM_WORLD
        d = {"OPtion1": 1}
        s = {"OPtion1"}
        if comm.rank == 0:
            if class_type == "CaseInsensitiveDict":
                obj = CaseInsensitiveDict(d)
            elif class_type == "CaseInsensitiveSet":
                obj = CaseInsensitiveSet(s)
        else:
            obj = None
        obj = comm.bcast(obj, root=0)
        self.assertIn("option1", obj)
