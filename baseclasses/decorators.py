import functools
import unittest
from importlib.util import find_spec


def require_mpi(func):
    return base_require(func, "mpi4py")


def base_require(func, module, message=None):
    """
    This is a generic function that can be used to generate decorators
    that test an import, and skips a test based on whether the library
    was found.

    Parameters
    ----------
    func : callable
        The function that the decorator is applied to. This is the required argument for a decorator and
        is passed in automatically
    module : str
        The module to test import for
    message : str
        The message for skipTest. The default is "<module> is not installed."

    Returns
    -------
    callable
        The function to be executed via the decorator. Either the original function, or
        if the module was not found, SkipTest is raised and the test function is skipped.

    Raises
    ------
    unittest.SkipTest
        If module is not found
    """
    # we check if the module can be found
    module = find_spec(module)
    # if not found
    if module is None:
        if message is None:
            message = f"{module} is not installed."
        # this is the alternative function which gets executed
        # by the decorator, which just raises skiptest

        @functools.wraps(func)
        def skip_wrapper(*args, **kwargs):
            raise unittest.SkipTest(message)

        return skip_wrapper
    # module found, we just return the function and proceed normally
    else:
        return func
