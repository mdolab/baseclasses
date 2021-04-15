import functools
import unittest


def require_mpi(func):
    try:
        from mpi4py import MPI  # noqa

        # this is a wrapper on func
        # but we inject the MPI option in the signature
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)

        return wrapper
    except ImportError:
        msg = "mpi4py is not installed."
        if not isinstance(func, type):
            # this wraps obj, which is the actual function
            @functools.wraps(func)
            def skip_wrapper(*args, **kwargs):
                raise unittest.SkipTest(msg)

            obj = skip_wrapper
        obj.__unittest_skip__ = True
        obj.__unittest_skip_why__ = msg
        return obj
