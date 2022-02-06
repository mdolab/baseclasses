try:
    from mpi4py import MPI
except ImportError:
    # parallel functions will throw errors
    MPI = None
import numpy
import os
import sys
from contextlib import contextmanager
from ..utils import Error
from ..utils import writeJSON, readJSON


def getTol(**kwargs):
    """
    Returns the tolerances based on kwargs.
    There are two ways of specifying tolerance:

    1. pass in ``tol`` which will set ``atol = rtol = tol``
    2. individually set ``atol`` and ``rtol``

    If any values are unspecified, the default value will be used.

    Parameters
    ----------
    atol : float
        absolute tolerance, default: 1E-12
    rtol : float
        relative tolerance, default: 1E-12
    tol : float
        tolerance. If specified, ``atol`` and ``rtol`` values are ignored and both set to this value

    Returns
    -------
    rtol : float
        relative tolerance
    atol : float
        absolute tolerance
    """
    DEFAULT_TOL = 1e-12
    if "tol" in kwargs:
        rtol = kwargs["tol"]
        atol = kwargs["tol"]
    else:
        if "rtol" in kwargs:
            rtol = kwargs["rtol"]
        else:
            rtol = DEFAULT_TOL
        if "atol" in kwargs:
            atol = kwargs["atol"]
        else:
            atol = DEFAULT_TOL
    return rtol, atol


class BaseRegTest:
    def __init__(self, ref_file, train=False, comm=None):
        """
        The class for handling regression tests.

        Parameters
        ----------
        ref_file : str
            The name of the reference file, containing its full path.
        train : bool, optional
            Whether to train the reference values, or test against existing reference values, by default False
        comm : MPI communicator, optional
            The MPI comm if testing in parallel, by default None
        check_arch : bool, optional
            Whether to check and set the appropriate PETSc arch prior to running tests, by default False.
            Note this option does not currently work.
        """
        self.ref_file = ref_file
        if MPI is None:
            self.comm = None
            self.rank = 0
        else:
            if comm is not None:
                self.comm = comm
            else:
                self.comm = MPI.COMM_WORLD
            self.rank = self.comm.rank

        self.train = train
        if self.train:
            self.db = {}
        else:
            # We need to check here that the reference file exists, otherwise
            # it will hang when it tries to open it on the root proc.
            assert os.path.isfile(self.ref_file)
            self.db = self.readRef()

    def __enter__(self):
        """
        Boilerplate code since we do not do anything special on opening the handler
        """
        return self

    def __exit__(self, *args, **kwargs):
        """
        Write the reference file on closing the handler
        """
        if self.train:
            self.writeRef()

    def getRef(self):
        return self.db

    def writeRef(self):
        """
        Write the reference file from the root proc
        """
        # move metadata to the end of the file
        if "metadata" in self.db:
            self.db["metadata"] = self.db.pop("metadata")
        with multi_proc_exception_check(self.comm):
            writeJSON(self.ref_file, self.db, comm=self.comm)

    def readRef(self):
        """
        Read in the reference file on the root proc, then broadcast to all procs
        """
        with multi_proc_exception_check(self.comm):
            db = readJSON(self.ref_file, comm=self.comm)
            self.metadata = db.pop("metadata", None)
        return db

    # *****************
    # Public functions
    # *****************

    def root_print(self, s):
        """
        Print a message on the root proc

        Parameters
        ----------
        s : str
            The message to print
        """
        if self.rank == 0:
            print(s)

    def add_metadata(self, metadata):
        """
        Add a metadata entry to the reference file, which is not used when checking reference values.

        Parameters
        ----------
        metadata : dict
            The dictionary of metadata to add
        """
        if self.rank == 0:
            self._add_values("metadata", metadata)

    def get_metadata(self):
        """
        Returns the metadata

        Returns
        -------
        dict
            The metadata stored in the reference file
        """
        return self.metadata

    # Add values from root only
    def root_add_val(self, name, values, **kwargs):
        """
        Add values but only on the root proc

        Parameters
        ----------
        name : str
            the name of the value
        values : [type]
            [description]
        """
        with multi_proc_exception_check(self.comm):
            if self.rank == 0:
                self._add_values(name, values, **kwargs)

    def root_add_dict(self, name, d, **kwargs):
        """
        Only write from the root proc

        Parameters
        ----------
        name : str
            The name of the dictionary
        d : dict
            The dictionary to add
        **kwargs
            See :meth:`getTol <baseclasses.BaseRegTest.getTol>` on how to specif tolerances.
        """
        with multi_proc_exception_check(self.comm):
            if self.rank == 0:
                self._add_dict(name, d, name, **kwargs)

    # Add values from all processors
    def par_add_val(self, name, values, **kwargs):
        """
        Add value(values) from parallel process in sorted order

        Parameters
        ----------
        name : str
            The name of the value
        values : ndarray
            The array to be added. This must be a numpy array distributed over self.comm
        **kwargs
            See :meth:`getTol <baseclasses.BaseRegTest.getTol>` on how to specif tolerances.
        """
        if self.comm is None:
            raise Error("Parallel functionality requires mpi4py!")
        values = self.comm.gather(values)
        with multi_proc_exception_check(self.comm):
            if self.rank == 0:
                self._add_values(name, values, **kwargs)

    def par_add_sum(self, name, values, **kwargs):
        """
        Add the sum of sum of the values from all processors.

        Parameters
        ----------
        name : str
            The name of the value
        values : ndarray
            The array to be added. This must be a numpy array distributed over self.comm
        **kwargs
            See :meth:`getTol <baseclasses.BaseRegTest.getTol>` on how to specif tolerances.
        """
        if self.comm is None:
            raise Error("Parallel functionality requires mpi4py!")
        reducedSum = self.comm.reduce(numpy.sum(values))
        with multi_proc_exception_check(self.comm):
            if self.rank == 0:
                self._add_values(name, reducedSum, **kwargs)

    def par_add_norm(self, name, values, **kwargs):
        """
        Add the norm across values from all processors.

        Parameters
        ----------
        name : str
            The name of the value
        values : ndarray
            The array to be added. This must be a numpy array distributed over self.comm
        **kwargs
            See :meth:`getTol <baseclasses.BaseRegTest.getTol>` on how to specif tolerances.
        """
        if self.comm is None:
            raise Error("Parallel functionality requires mpi4py!")
        reducedSum = self.comm.reduce(numpy.sum(values ** 2))
        with multi_proc_exception_check(self.comm):
            if self.rank == 0:
                self._add_values(name, numpy.sqrt(reducedSum), **kwargs)

    # *****************
    # Private functions
    # *****************
    def assert_allclose(self, actual, reference, name, rtol, atol, full_name=None):
        if full_name is None:
            full_name = name
        msg = f"Failed value for: {full_name}"
        numpy.testing.assert_allclose(actual, reference, rtol=rtol, atol=atol, err_msg=msg)

    def _add_values(self, name, values, db=None, **kwargs):
        """
        Add values in special value format
        If ``compare=True``, it will compare the supplied value against an existing value
        in the database instead of adding the value, even in training mode. This is useful
        for example in dot product tests when comparing two values.

        Parameters
        ----------
        name : str
            Name of the value
        values : float or list of floats or numpy array
            The value to add
        db : dict, optional
            The database to add the values to, only used to recursively add dictionary entries
            If none, ``self.db`` is used.
        """
        # if metadata, only add it to db if train
        # else do nothing
        if name == "metadata":
            if self.train:
                self.db[name] = values
            return
        if not isinstance(name, str):
            raise TypeError("All keys in the dictionary must use string indexing.")
        rtol, atol = getTol(**kwargs)
        compare = kwargs["compare"] if "compare" in kwargs else False
        full_name = kwargs["full_name"] if "full_name" in kwargs else None
        if db is None:
            db = self.db
        if not self.train or (self.train and compare):
            self.assert_allclose(values, db[name], name, rtol, atol, full_name)
        else:
            if name in db.keys():
                raise KeyError(f"The name {name} is already in the training database. Please give UNIQUE keys.")
            if isinstance(values, numpy.ndarray):
                db[name] = values.copy()
            else:
                db[name] = values

    def _add_dict(self, dict_name, d, full_name, db=None, **kwargs):
        """
        Add all values in a dictionary in sorted key order.
        This function is called recursively on nested dictionaries, which is why ``full_name`` is needed to preserve the nested keys.
        Eventually, the recursion encounters a list or scalar, at which point :meth:`_add_values` is called to actually add the value to the database.

        Parameters
        ----------
        dict_name : str
            Name of the dictionary
        d : dict
            The dictionary
        full_name : str
            The full name of the dictionary
        db : dict, optional
            The database to add the values to, only used to recursively add dictionary entries
            If none, ``self.db`` is used.
        """
        rtol, atol = getTol(**kwargs)
        if db is None:
            db = self.db
        if self.train:
            db[dict_name] = {}
        elif dict_name not in db.keys():
            raise ValueError(f"The key '{dict_name}' was not found in the reference file!")

        for key in sorted(d.keys()):
            full_name = f"{full_name}: {key}"
            if isinstance(d[key], bool):
                self._add_values(key, int(d[key]), rtol=rtol, atol=atol, db=db[dict_name], full_name=full_name)
            elif isinstance(d[key], dict):
                # do some good ol' fashion recursion
                self._add_dict(key, d[key], full_name, rtol=rtol, atol=atol, db=db[dict_name])
            else:
                self._add_values(key, d[key], rtol=rtol, atol=atol, db=db[dict_name], full_name=full_name)


# This strategy of dealing with error propagation to multiple procs is taken directly form openMDAO.utils;
# It was not imported and used here to avoid adding openMDAO as a dependency.
# If openMDAO is added as a dependency in the future this context manager definition should be replaced by an import


@contextmanager
def multi_proc_exception_check(comm):
    """
    Raise an exception on all procs if it is raised on one.
    Wrap this around code that you want to globally fail if it fails
    on any MPI process in comm.  If not running under MPI, don't
    handle any exceptions.

    Parameters
    ----------
    comm : MPI communicator or None
        Communicator from the ParallelGroup that owns the calling solver.
    """
    if MPI is None or comm is None or comm.size == 1:
        yield
    else:
        try:
            yield
        except Exception:
            exc = sys.exc_info()

            fail = 1
        else:
            fail = 0

        failed = comm.allreduce(fail)
        if failed:
            if fail:
                msg = f"{exc[1]}"
            else:
                msg = None
            allmsgs = comm.allgather(msg)
            if fail:
                msg = f"Exception raised on rank {comm.rank}: {exc[1]}"
                raise exc[0](msg).with_traceback(exc[2])
            else:
                for m in allmsgs:
                    if m is not None:
                        raise RuntimeError(f"Exception raised on other rank: {m}.")
