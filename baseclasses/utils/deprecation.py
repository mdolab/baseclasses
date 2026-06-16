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
        Name of the package whose version the removal is based on. Note that the package name is the name as listed on
        pyPI (and used to pip install), not necessarily the name you import the package as (e.g the
        ``mdolab-baseclasses`` package is imported as ``baseclasses``).
    removal_version : str
        Version of the package at which the deprecated API will be removed (e.g., "1.2.3", "2.3", "3").
    new_name : Optional[str], optional
        Name of the new method that should be used instead of the deprecated one if applicable, by default None
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
