import unittest
from baseclasses.utils import CaseInsensitiveDict, CaseInsensitiveSet


class TestCaseInsensitiveClasses(unittest.TestCase):
    def test_dict(self):
        value1 = 123
        value2 = 321
        value3 = 132
        d = CaseInsensitiveDict({"OPtion1": value1})
        # test __getitem__
        self.assertEqual(d["OPTION1"], value1)
        # test __setitem__
        d["OPTION1"] = value2
        self.assertEqual(d["option1"], value2)
        self.assertIn("OPtion1", d.map)
        # test __contains__
        self.assertIn("Option1", d)
        d["optioN2"] = value1
        self.assertEqual(len(d), 2)
        self.assertIn("OPTION2", d)
        # test original capitalization is preserved on new key
        self.assertIn("optioN2", d.map)
        # test pop()
        d.pop("Option2")
        self.assertEqual(len(d), 1)
        self.assertEqual(d.get("opTION1"), value2)
        self.assertEqual(list(d), ["OPtion1"])
        d2 = CaseInsensitiveDict({"OPTION3": value3})
        # test update()
        d.update(d2)
        self.assertIn("option3", d)
        self.assertEqual(d["Option3"], value3)

    def test_set(self):
        # test __contains__ and add()
        s = CaseInsensitiveSet({"Option1"})
        self.assertIn("OPTION1", s)
        # test original capitalization is preserved on initialization
        self.assertIn("Option1", s.map)
        s.add("OPTION2")
        self.assertIn("option2", s)
        # test original capitalization is preserved on new item
        self.assertIn("OPTION2", s.map)
        # test update()
        s2 = CaseInsensitiveSet({"OPTION2", "opTION3"})
        s.update(s2)
        self.assertEqual(len(s), 3)
        # test set operations
        self.assertTrue(s2.issubset(s))
        self.assertFalse({"Option2"}.issubset(s))  # set is case sensitive so this should fail
        self.assertTrue(CaseInsensitiveSet({"Option2"}).issubset(s))  # and this should pass
        # test remove
        s.remove("option3")
        self.assertNotIn("OPTION3", s)
        self.assertEqual(len(s), 2)
        s3 = s.union(s2)
        self.assertEqual(s3, CaseInsensitiveSet({"option1", "option2", "option3"}))
