"""
==============================================================================
Unit tests for deprecation utilities
==============================================================================
@File    :   test_deprecation.py
@Date    :   2026/06/15
@Author  :   Alasdair Christison Gray
@Description :
"""

# ==============================================================================
# Standard Python modules
# ==============================================================================
import unittest
from importlib.metadata import version

# ==============================================================================
# External Python modules
# ==============================================================================
from packaging.version import Version

# ==============================================================================
# Extension modules
# ==============================================================================
from baseclasses.utils import expire_deprecation

PACKAGE_NAME = "mdolab-baseclasses"
NEW_METHOD_NAME = "newMethod"
FUTURE_REMOVAL_VERSION = "100.0.0"  # set to a very high version to avoid triggering the error
PAST_REMOVAL_VERSION = "0.0.1"  # set to a very low version to trigger the error
CURRENT_VERSION = str(Version(version(PACKAGE_NAME)))  # the version installed in this environment


@expire_deprecation(PACKAGE_NAME, FUTURE_REMOVAL_VERSION, new_name=NEW_METHOD_NAME)
def deprecated_method():
    return None


@expire_deprecation(PACKAGE_NAME, FUTURE_REMOVAL_VERSION)
def deprecated_method_no_replacement():
    return None


class DummyClass:
    """A class with a deprecated method, used to check that the decorator works on methods as well as free functions."""

    @expire_deprecation(PACKAGE_NAME, FUTURE_REMOVAL_VERSION, new_name=NEW_METHOD_NAME)
    def deprecatedMethod(self, value):
        return value


class TestDeprecation(unittest.TestCase):
    def test_deprecation_warning(self):
        """When a method is marked with `expire_deprecation`, and the removal version is in the future, and the method is
        called, a deprecation warning should be raised. The warning should include:
        - The package name
        - The new method name
        - The removal version.

        This is checked for both a decorated free function and a decorated method.
        """
        # --- Free function ---
        with self.assertWarns(DeprecationWarning) as cm:
            deprecated_method()
        message = str(cm.warning)
        self.assertIn(PACKAGE_NAME, message)
        self.assertIn(NEW_METHOD_NAME, message)
        self.assertIn(FUTURE_REMOVAL_VERSION, message)

        # --- Method ---
        obj = DummyClass()
        with self.assertWarns(DeprecationWarning) as cm:
            obj.deprecatedMethod(1)
        message = str(cm.warning)
        self.assertIn(PACKAGE_NAME, message)
        self.assertIn(NEW_METHOD_NAME, message)
        self.assertIn(FUTURE_REMOVAL_VERSION, message)

    def test_past_deprecation_warning(self):
        """When a method is marked with `expire_deprecation`, and the removal version is in the past, an error should be
        raised. The error is raised when the decorator is applied (i.e. at import/definition time), not when the method
        is called, so this is tested by applying the decorator inside the test. The error message should include:
        - The package name.
        - The current version.
        - The removal version.
        """
        with self.assertRaises(AssertionError) as cm:

            @expire_deprecation(PACKAGE_NAME, PAST_REMOVAL_VERSION, new_name=NEW_METHOD_NAME)
            def past_deprecated_method():
                return None

        message = str(cm.exception)
        self.assertIn(PACKAGE_NAME, message)
        self.assertIn(CURRENT_VERSION, message)
        self.assertIn(PAST_REMOVAL_VERSION, message)

    def test_no_replacement_warning(self):
        """When `new_name` is not provided, the warning should still be raised but should not suggest a replacement."""
        with self.assertWarns(DeprecationWarning) as cm:
            deprecated_method_no_replacement()
        message = str(cm.warning)
        self.assertIn(PACKAGE_NAME, message)
        self.assertNotIn("Use", message)

    def test_removal_version_boundary(self):
        """The error should be raised when the current version is exactly equal to the removal version, since the check
        is `current >= removal`."""
        with self.assertRaises(AssertionError):

            @expire_deprecation(PACKAGE_NAME, CURRENT_VERSION)
            def boundary_method():
                return None

    def test_arguments_and_return_forwarded(self):
        """The decorated callable should forward its arguments untouched and return the wrapped callable's result, for
        both free functions and methods."""

        # --- Free function with positional and keyword arguments ---
        @expire_deprecation(PACKAGE_NAME, FUTURE_REMOVAL_VERSION)
        def echo(aa, bb, cc=0):
            return (aa, bb, cc)

        with self.assertWarns(DeprecationWarning):
            result = echo(1, 2, cc=3)
        self.assertEqual(result, (1, 2, 3))

        # --- Method (self must bind correctly and the argument must pass through) ---
        obj = DummyClass()
        with self.assertWarns(DeprecationWarning):
            result = obj.deprecatedMethod(42)
        self.assertEqual(result, 42)


if __name__ == "__main__":
    unittest.main()
