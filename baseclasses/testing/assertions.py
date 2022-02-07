import numpy as np

DEFAULT_TOL = 1e-12


def assert_equal(a, b):
    """
    This replaces the assertEqual functionality provided by unittest.TestCase
    so that we can call this outside the class
    """
    if type(a) != type(b):
        raise AssertionError("The two objects are not the same type!")
    if isinstance(a, np.ndarray):
        if not np.all(a == b):
            raise AssertionError(f"{a} and {b} are not equal.")
    elif isinstance(a, dict):
        if set(a.keys()) != set(b.keys()):
            raise AssertionError("The two dictionaries do not have the same keys")
        for k in a.keys():
            assert_equal(a[k], b[k])
    elif not a == b:
        raise AssertionError(f"{a} and {b} are not equal.")


def assert_dict_allclose(actual, desired, atol=DEFAULT_TOL, rtol=DEFAULT_TOL, partial=False):
    """
    Simple assert for two flat dictionaries, where the values are
    assumed to be numpy arrays

    The keys are checked first to make sure that they match

    Parameters
    ----------
    actual : 1D dictionary
        A dictionary of str: array_like pairs
    desired : 1D dictionary
        A dictionary of str: array_like pairs
    atol : float
        Absolute tolerance
    rtol : float
        Relative tolerance
    partial : bool
        Whether the assertion allows for partial keys, i.e. when the dictionaries
        do not have matching keys.
        If True, we assume that ``desired`` contains a subset of the keys of ``actual``.

    Raises
    ------
    AssertionError
        if the values for any key do not match to the target tolerance.
    """
    if not partial:
        assert set(actual.keys()) == set(desired.keys())
    else:
        assert set(desired.keys()).issubset(set(actual.keys()))
    commonKeys = sorted(set(actual.keys()).intersection(set(desired.keys())))

    for key in commonKeys:
        np.testing.assert_allclose(actual[key], desired[key], atol=atol, rtol=rtol, err_msg=f"Failed for key {key}")


def assert_dict_not_allclose(actual, desired, atol=DEFAULT_TOL, rtol=DEFAULT_TOL):
    """
    The opposite of assert_dict_allclose
    """
    assert_equal(set(actual.keys()), set(desired.keys()))
    for key in actual.keys():
        if np.allclose(actual[key], desired[key], atol=atol, rtol=rtol):
            raise AssertionError(f"Dictionaries are close! Got {actual} and {desired} for key {key}")


def assert_not_allclose(actual, desired, atol=DEFAULT_TOL, rtol=DEFAULT_TOL):
    """
    The numpy array version
    """
    if np.allclose(actual, desired, atol=atol, rtol=rtol):
        raise AssertionError(f"Arrays are close! Inputs are {actual} and {desired}")
