import functools
from importlib.metadata import version
from typing import Optional
import warnings
from packaging.version import Version
import unittest
from importlib.util import find_spec


def require_mpi(func):
    """A decorator to skip tests unless ``mpi4py`` is available

    Examples
    --------
    .. code-block:: python

       @require_mpi
       def test_mpi4py(self):
           print(self.comm.rank)

    """
    return base_require(func, "mpi4py")


def base_require(func, moduleName, message=None):
    """
    This is a generic function that can be used to generate decorators
    that test an import, and skips a test based on whether the library
    was found.

    Parameters
    ----------
    func : callable
        The function that the decorator is applied to. This is the required argument for a decorator and
        is passed in automatically
    moduleName : str
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
    module = find_spec(moduleName)
    # if not found
    if module is None:
        if message is None:
            message = f"{moduleName} is not installed."
        # this is the alternative function which gets executed
        # by the decorator, which just raises skiptest

        @functools.wraps(func)
        def skip_wrapper(*args, **kwargs):
            raise unittest.SkipTest(message)

        return skip_wrapper
    # module found, we just return the function and proceed normally
    else:
        return func


def expire_deprecation(package_name: str, removal_version: str, new_name: Optional[str] = None):
    """Decorator for methods that have been deprecated and potentially replaced by a new method

    This decorator will raise a warning when the decorated method is called, and will raise an error if the current
    version of the package is greater than or equal to the specified removal version, helping to ensure that deprecated
    APIs are removed in a timely manner.

    Parameters
    ----------
    package_name : str
        _description_
    removal_version : str
        _description_
    new_name : Optional[str], optional
        _description_, by default None
    """
    removal = Version(removal_version)
    current = Version(version(package_name))

    def decorator(func):
        if current >= removal:
            raise AssertionError(
                f"{func.__qualname__}: deprecated API should have been "
                f"removed in {package_name} v{removal} "
                f"(current: v{current}). Please delete this shim."
            )

        msg = f"{func.__name__}() is deprecated and will be removed in {package_name} v{removal}."
        if new_name is not None:
            msg += f" Use {new_name} instead."

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            return func(self, *args, **kwargs)

        return wrapper

    return decorator
