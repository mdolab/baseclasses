from contextlib import contextmanager
import os
import sys

"""
Functions for redirecting stdout/stderr to different streams

Based on: http://eli.thegreenplace.net/2015/redirecting-all-kinds-of-stdout-in-python/.
"""

def redirectSTDOUT(f):
    """
    This function redirects stdout/stderr to the given file handle.
    Written by Bret Naylor

    Parameters
    ----------
    f : fd
        A file descriptor that you want to redirect stdout to 
    """
    original_stdout_fd = sys.stdout.fileno()
    original_stderr_fd = sys.stderr.fileno()

    sys.stdout.flush()
    sys.stderr.flush()

    # Flush and close sys.stdout/err - also closes the file descriptors (fd)
    sys.stdout.close()
    sys.stderr.close()

    # Make original_stdout_fd point to the same file as to_fd
    os.dup2(f.fileno(), original_stdout_fd)
    os.dup2(f.fileno(), original_stderr_fd)

    # Create a new sys.stdout that points to the redirected fd

    # For Python 3.x
    sys.stdout = io.TextIOWrapper(os.fdopen(original_stdout_fd, "wb"))
    sys.stderr = io.TextIOWrapper(os.fdopen(original_stderr_fd, "wb"))

@contextmanager
def redirectIO(f)
    """
    A function that redirects stdout in a with block and returns to the stdout after the with block completes

    Parameters
    ----------
    f : fd
        A file descriptor that stdout should be redirected to
    """

    # save the file descriptors to restore to 
    saved_stdout_fd = os.dup(sys.stdout.fileno())
    saved_stderr_fd = os.dup(sys.stdout.fileno())

    try:
        # change the stdout/err to the new stream
        redirectIO_func(f)
        # yield to the with block
        yield
        # change the stdout/err back to stdout/err
        redirectIO_func()
