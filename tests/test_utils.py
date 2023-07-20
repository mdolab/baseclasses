# ==============================================================================
# Standard Python modules
# ==============================================================================
import unittest

# ==============================================================================
# External Python modules
# ==============================================================================
from parameterized import parameterized_class

# ==============================================================================
# Extension modules
# ==============================================================================
from baseclasses.utils import ParseStringFormat


@parameterized_class(
    [
        {
            "fmt": "{: 17.11e}",
            "true_align": None,
            "true_sign": " ",
            "true_width": 17,
            "true_precision": 11,
            "true_grouping_option": None,
            "true_type": "e",
        },
        {
            "fmt": "{:9.3e}",
            "true_align": None,
            "true_sign": None,
            "true_width": 9,
            "true_precision": 3,
            "true_grouping_option": None,
            "true_type": "e",
        },
        {
            "fmt": "{:< 5d}",
            "true_align": "<",
            "true_sign": " ",
            "true_width": 5,
            "true_precision": None,
            "true_grouping_option": None,
            "true_type": "d",
        },
        {
            "fmt": "{:^10}",
            "true_align": "^",
            "true_sign": None,
            "true_width": 10,
            "true_precision": None,
            "true_grouping_option": None,
            "true_type": None,
        },
        {
            "fmt": "{:> 15,}",
            "true_align": ">",
            "true_sign": " ",
            "true_width": 15,
            "true_precision": None,
            "true_grouping_option": ",",
            "true_type": None,
        },
        {
            "fmt": "{:> 15,} some other bracket {:< 9.2e}",
            "true_align": ">",
            "true_sign": " ",
            "true_width": 15,
            "true_precision": None,
            "true_grouping_option": ",",
            "true_type": None,
        },
    ]
)
class TestUtilsParseStringFormat(unittest.TestCase):
    def setUp(self):
        self.pf = ParseStringFormat(self.fmt)

    def test_align_property(self):
        self.assertEqual(self.pf.align, self.true_align)

    def test_sign_property(self):
        self.assertEqual(self.pf.sign, self.true_sign)

    def test_width_property(self):
        self.assertEqual(self.pf.width, self.true_width)

    def test_precision_property(self):
        self.assertEqual(self.pf.precision, self.true_precision)

    def test_grouping_option_property(self):
        self.assertEqual(self.pf.grouping_option, self.true_grouping_option)

    def test_ftype_property(self):
        self.assertEqual(self.pf.ftype, self.true_type)


if __name__ == "__main__":
    unittest.main()
