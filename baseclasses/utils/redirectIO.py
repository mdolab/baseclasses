from contextlib import contextmanager
import io
import os
import sys

"""
Functions for redirecting stdout/stderr to different streams

Based on: http://eli.thegreenplace.net/2015/redirecting-all-kinds-of-stdout-in-python/.
"""


def redirectIO(f_out, f_err=None):
    """
    This function redirects stdout/stderr to the given file handle.

    Parameters
    ----------
    f_out : file
        A file stream to redirect stdout to

    f_err : file
        A file stream to redirect stderr to, if none is specified it is set to `f_out`
    """

    if not f_err:
        f_err = f_out

    # flush the standard out
    sys.stdout.flush()
    sys.stderr.flush()

    # close the standard
    sys.stdout.close()
    sys.stderr.close()

    # reopen the stream with new file descriptors
    sys.stdout = io.TextIOWrapper(os.fdopen(f_out.fileno(), "wb"))
    sys.stderr = io.TextIOWrapper(os.fdopen(f_err.fileno(), "wb"))


@contextmanager
def redirectingIO(f_out, f_err=None):
    """
    A function that redirects stdout in a with block and returns to the stdout after the with block completes

    Parameters
    ----------
    f_out : file
        A file stream that stdout should be redirected to

    f_err : file
        A file stream that stderr should be redirected to
    """

    if not f_err:
        f_err = f_out

    # save the file descriptors to restore to
    saved_stdout_fd = os.dup(sys.stdout.fileno())
    saved_stderr_fd = os.dup(sys.stderr.fileno())

    # redirect the stdout/err streams
    redirectIO(f_out, f_err)

    # yield to the with block
    yield

    # flush output
    sys.stderr.flush()
    sys.stdout.flush()

    # close the output
    sys.stderr.close()
    sys.stdout.close()

    # reopen the standard streams with original file descriptors
    sys.stdout = io.TextIOWrapper(os.fdopen(saved_stdout_fd, "wb"))
    sys.stderr = io.TextIOWrapper(os.fdopen(saved_stderr_fd, "wb"))
