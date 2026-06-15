"""
==============================================================================

==============================================================================
@File    :   deprecation.py
@Date    :   2026/06/15
@Author  :   Alasdair Christison Gray
@Description :
"""

# ==============================================================================
# Standard Python modules
# ==============================================================================
from importlib.metadata import version
from typing import Optional
import warnings
import functools

# ==============================================================================
# External Python modules
# ==============================================================================
from packaging.version import Version

# ==============================================================================
# Extension modules
# ==============================================================================


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
        def wrapper(*args, **kwargs):
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        return wrapper

    return decorator
