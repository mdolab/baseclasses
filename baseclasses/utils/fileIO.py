import io
import os
import sys
from contextlib import contextmanager
import pickle
import json
import numpy as np
from .containers import CaseInsensitiveDict, CaseInsensitiveSet


def writeJSON(fname, obj, comm=None):
    """
    Write an object to a JSON file.
    This includes a custom NumPy encoder to reliably write NumPy arrays to JSON, which can then be read back via :meth:`readJSON`.

    Parameters
    ----------
    fname : str
        The file name
    obj : dict or ndarray
        The object to be written to JSON
    comm : mpi4py.MPI.Comm, optional
        The communicator over which this function is called.
        If supplied, only the root proc will be used for file IO.
    """

    class MyEncoder(json.JSONEncoder):
        """
        Custom encoder class for Numpy arrays and CaseInsensitiveDict
        """

        def default(self, o):
            """
            If input object is an ndarray it will be converted into a dict
            holding dtype, shape and the data, base64 encoded.
            """
            if isinstance(o, np.ndarray):
                if o.flags["C_CONTIGUOUS"]:
                    pass
                else:
                    o = np.ascontiguousarray(o)
                    assert o.flags["C_CONTIGUOUS"]
                if o.size == 1:
                    return o.item()
                else:
                    return dict(__ndarray__=o.tolist(), dtype=str(o.dtype), shape=o.shape)
            elif isinstance(o, np.integer):
                return dict(__ndarray__=int(o), dtype=str(o.dtype), shape=o.shape)
            elif isinstance(o, np.floating):
                return dict(__ndarray__=float(o), dtype=str(o.dtype), shape=o.shape)
            elif isinstance(o, CaseInsensitiveDict):
                return dict(o)
            elif isinstance(o, CaseInsensitiveSet):
                return set(o)
            else:
                # Let the base class default method raise the TypeError
                super().default(o)

    if (comm is None) or (comm is not None and comm.rank == 0):
        with open(fname, "w") as json_file:
            json.dump(obj, json_file, sort_keys=True, indent=4, separators=(",", ": "), cls=MyEncoder)
    if comm is not None:
        comm.barrier()


def readJSON(fname, comm=None):
    """
    Reads a JSON file and return the contents as a dictionary.
    This includes a custom NumPy reader to retrieve NumPy arrays, matching the :meth:`writeJSON` function.

    Parameters
    ----------
    file_name : str
        The file name

    comm : mpi4py.MPI.Comm, optional
        The communicator over which this function is called.
        If supplied, only the root proc will be used for file IO.


    References
    ----------
    This is based on `this stack overflow answer <https://stackoverflow.com/questions/3488934/simplejson-and-numpy-array/24375113#24375113>`_
    """

    def json_numpy_obj_hook(dct):
        """
        Decodes a previously encoded numpy ndarray with proper shape and dtype.

        Parameters
        ----------
        dct: dictionary
            JSON dictionary containing the encoded ndarray

        Returns
        -------
        dct: dictionary or Numpy array
            The decoded Numpy array, or the input dct if it is not an encoded Numpy array
        """
        if isinstance(dct, dict) and "__ndarray__" in dct:
            data = dct["__ndarray__"]
            return np.array(data, dct["dtype"]).reshape(dct["shape"])
        return dct

    data = None
    if (comm is None) or (comm is not None and comm.rank == 0):
        with open(fname, "r") as json_file:
            data = json.load(json_file, object_hook=json_numpy_obj_hook)
    if comm is not None:
        data = comm.bcast(data)
    return data


def readPickle(fname, comm=None):
    """
    This is a parallel pickle.load function, which is performed on the root proc only.
    Error checking is necessary to provide py2 compatibility.

    Parameters
    ----------
    fname : str
        The pickle file name
    comm : mpi4py.MPI.Comm, optional
        The communicator over which this function is called.
        If supplied, only the root proc will be used for file IO.

    Returns
    -------
    obj : The object stored in the pickle file
    """
    obj = None
    if (comm is None) or (comm is not None and comm.rank == 0):
        try:
            with open(fname, "rb") as f:
                obj = pickle.load(f)
        except UnicodeDecodeError:  # if pickled with py2
            with open(fname, "rb") as f:
                obj = pickle.load(f, encoding="latin1")
    if comm is not None:
        comm.barrier()
        obj = comm.bcast(obj)
    return obj


def writePickle(fname, obj, comm=None):
    """
    Parallel pickle writing function, only performs operations on the root proc

    Parameters
    ----------
    fname : str
        The pickle file name
    obj : any object which can be pickled by Python
        The object to be pickled
    comm : mpi4py.MPI.Comm, optional
        The communicator over which this function is called.
        If supplied, only the root proc will be used for file IO.
    """
    if (comm is None) or (comm is not None and comm.rank == 0):
        with open(fname, "wb") as handle:
            pickle.dump(obj, handle)
    if comm is not None:
        comm.barrier()


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
        A file stream to redirect stderr to. If none is specified it is set to `f_out`
    """

    if f_err is None:
        f_err = f_out

    orig_out = sys.stdout.fileno()
    orig_err = sys.stderr.fileno()

    # flush the standard out
    sys.stdout.flush()
    sys.stderr.flush()

    # close the standard
    sys.stdout.close()
    sys.stderr.close()

    os.dup2(f_out.fileno(), orig_out)
    os.dup2(f_err.fileno(), orig_err)

    # reopen the stream with new file descriptors
    sys.stdout = io.TextIOWrapper(os.fdopen(orig_out, "wb"))
    sys.stderr = io.TextIOWrapper(os.fdopen(orig_err, "wb"))


@contextmanager
def redirectingIO(f_out, f_err=None):
    """
    A function that redirects stdout in a with block and returns to the stdout after the `with` block completes.
    The filestream passed to this function will be closed after exiting the `with` block.

    Here is an example of usage where all adflow output is redirected to the file `adflow_out.txt`:
    >>> from baseclasses.utils import redirectIO
    >>> print("Printing some information to terminal")
    >>> with redirectIO.redirectingIO(open("adflow_out.txt", "w")):
    ...     CFDSolver = ADFLOW(options=options)
    ...     CFDSolver(AeroProblem(**apOptions)
    >>> print("Printing some more information to terminal")

    Parameters
    ----------
    f_out : file
        A file stream that stdout should be redirected to

    f_err : file
        A file stream to redirect stderr to. If none is specified it is set to `f_out`
    """

    if f_err is None:
        f_err = f_out

    # save the file descriptors to restore to
    saved_stdout_fd = os.dup(sys.stdout.fileno())
    saved_stderr_fd = os.dup(sys.stderr.fileno())

    # redirect the stdout/err streams
    redirectIO(f_out, f_err)

    # yield to the with block
    yield

    orig_out = sys.stdout.fileno()
    orig_err = sys.stderr.fileno()

    # flush output
    sys.stderr.flush()
    sys.stdout.flush()

    # close the output
    sys.stderr.close()
    sys.stdout.close()

    os.dup2(saved_stdout_fd, orig_out)
    os.dup2(saved_stderr_fd, orig_err)

    # reopen the standard streams with original file descriptors
    sys.stdout = io.TextIOWrapper(os.fdopen(orig_out, "wb"))
    sys.stderr = io.TextIOWrapper(os.fdopen(orig_err, "wb"))
