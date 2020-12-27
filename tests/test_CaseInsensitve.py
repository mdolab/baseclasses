import unittest
from baseclasses import CaseInsensitiveDict, CaseInsensitiveSet


class TestCaseInsensitiveClasses(unittest.TestCase):
    def test_dict(self):
        value1 = 123
        value2 = 321
        value3 = 132
        d = CaseInsensitiveDict({"OPtion1": value1})
        self.assertEqual(d["OPTION1"], value1)
        d["OPTION1"] = value2
        self.assertEqual(d["option1"], value2)
        self.assertIn("Option1", d)
        d["option2"] = value1
        self.assertEqual(len(d), 2)
        self.assertIn("OPTION2", d)
        d.pop("Option2")
        self.assertEqual(len(d), 1)
        self.assertEqual(d.get("opTION1"), value2)
        self.assertEqual(list(d), ["option1"])
        d2 = CaseInsensitiveDict({"OPTION3": value3})
        d.update(d2)
        self.assertIn("option3", d)
        self.assertEqual(d["Option3"], value3)

    def test_set(self):
        s = CaseInsensitiveSet({"Option1"})
        self.assertIn("OPTION1", s)
        s.add("OPTION2")
        self.assertIn("option2", s)
        s2 = CaseInsensitiveSet({"OPTION2", "opTION3"})
        s.update(s2)
        self.assertEqual(len(s), 3)
        s.remove("option3")
        self.assertNotIn("OPTION3", s)
        self.assertEqual(len(s), 2)
