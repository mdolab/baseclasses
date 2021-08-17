try:
    from mpi4py import MPI
except ImportError:
    # parallel functions will throw errors
    MPI = None
import numpy
import os
import sys
import json
from collections import deque
from contextlib import contextmanager
from ..utils import CaseInsensitiveDict, CaseInsensitiveSet, Error


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
        with multi_proc_exception_check(self.comm):
            if self.rank == 0:
                self.writeRefJSON(self.ref_file, self.db)

    def readRef(self):
        """
        Read in the reference file on the root proc, then broadcast to all procs
        """
        with multi_proc_exception_check(self.comm):
            if self.rank == 0:
                db = self.readRefJSON(self.ref_file)
            else:
                db = None
            if self.comm is not None:
                db = self.comm.bcast(db)
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

    # =============================================================================
    #                         reference files I/O
    # =============================================================================
    # based on this stack overflow answer https://stackoverflow.com/questions/3488934/simplejson-and-numpy-array/24375113#24375113

    @staticmethod
    def writeRefJSON(file_name, ref):
        """
        Write a dictionary to a reference JSON file.
        This includes a custom NumPy encoder to reliably write NumPy arrays to JSON, which can then be read back via :meth:`readRefJSON`.

        Parameters
        ----------
        file_name : str
            The file name
        ref : dict
            The dictionary
        """

        class MyEncoder(json.JSONEncoder):
            """
            Custom encoder class for Numpy arrays and CaseInsensitiveDict
            """

            def default(self, obj):
                """
                If input object is an ndarray it will be converted into a dict
                holding dtype, shape and the data, base64 encoded.
                """
                if isinstance(obj, numpy.ndarray):
                    if obj.flags["C_CONTIGUOUS"]:
                        pass
                    else:
                        obj = numpy.ascontiguousarray(obj)
                        assert obj.flags["C_CONTIGUOUS"]
                    if obj.size == 1:
                        return obj.item()
                    else:
                        return dict(__ndarray__=obj.tolist(), dtype=str(obj.dtype), shape=obj.shape)
                elif isinstance(obj, numpy.integer):
                    return dict(__ndarray__=int(obj), dtype=str(obj.dtype), shape=obj.shape)
                elif isinstance(obj, numpy.floating):
                    return dict(__ndarray__=float(obj), dtype=str(obj.dtype), shape=obj.shape)
                elif isinstance(obj, CaseInsensitiveDict):
                    return dict(obj)
                elif isinstance(obj, CaseInsensitiveSet):
                    return set(obj)

                # Let the base class default method raise the TypeError
                super().default(obj)

        # move metadata to end of db if it exists
        if "metadata" in ref:
            ref["metadata"] = ref.pop("metadata")
        with open(file_name, "w") as json_file:
            json.dump(ref, json_file, sort_keys=True, indent=4, separators=(",", ": "), cls=MyEncoder)

    # based on this stack overflow answer https://stackoverflow.com/questions/3488934/simplejson-and-numpy-array/24375113#24375113
    @staticmethod
    def readRefJSON(file_name):
        """
        Reads a JSON file and return the contents as a dictionary.
        This includes a custom NumPy reader to retrieve NumPy arrays, matching the :meth:`writeRefJSON` function.

        Parameters
        ----------
        file_name : str
            The file name
        """

        def json_numpy_obj_hook(dct):
            """Decodes a previously encoded numpy ndarray with proper shape and dtype.

            :param dct: (dict) json encoded ndarray
            :return: (ndarray) if input was an encoded ndarray
            """
            if isinstance(dct, dict) and "__ndarray__" in dct:
                data = dct["__ndarray__"]
                return numpy.array(data, dct["dtype"]).reshape(dct["shape"])
            return dct

        with open(file_name) as json_file:
            data = json.load(json_file, object_hook=json_numpy_obj_hook)

        return data

    @staticmethod
    def convertRegFileToJSONRegFile(file_name, output_file=None):
        """
        Converts from the old format of regression test file to the new JSON format

        Parameters
        ----------
        file_name : str
            The file name
        output_file : The output file name, optional
            If None, the same filename will be used, but with a ``.json`` suffix.
        """
        if output_file is None:
            output_file = os.path.splitext(file_name)[0] + ".json"

        ref = {}
        line_history = deque(maxlen=3)

        def saveValueInRef(value, key, mydict):
            """a helper function to add values to our ref dict"""

            if key in mydict:
                # turn the value into a numpy array and append or just append if
                # the value is already an numpy.array

                if isinstance(mydict[key], numpy.ndarray):
                    mydict[key] = numpy.append(mydict[key], value)
                else:
                    mydict[key] = numpy.array([mydict[key], value])
            else:
                mydict[key] = value

        curr_dict = ref
        with open(file_name) as fid:
            for line in fid:
                # key ideas
                #    - lines starting with @value aren't added to the queque

                # check to see if it is the start of dictionary of values
                if "Dictionary Key: " in line:

                    # if there are other lines in the queque this isn't following
                    # an @value
                    if len(line_history) > 0:

                        # We must create a new dictionary and add it to ref
                        last_line = line_history[-1].rstrip()
                        if "Dictionary Key: " in last_line:
                            # this is a nested dict
                            key = last_line[len("Dictionary Key: ") :]

                            if len(line_history) > 1:
                                prior_dict = curr_dict
                                curr_dict[key] = {}
                                curr_dict = curr_dict[key]
                            else:
                                prior_dict[key] = {}
                                curr_dict = prior_dict[key]
                            print("nested dict", last_line)
                        else:
                            print("dict ", last_line)
                            ref[last_line] = {}
                            curr_dict = ref[last_line]

                if "@value" in line:
                    # get the value from the ref file
                    value = float(line.split()[1])

                    # if a value was not just added
                    if line_history:
                        # grab the data and use them as the keys for the reference dictionary
                        key = line_history[-1].rstrip()
                        if "Dictionary Key: " in key:
                            key = key[len("Dictionary Key: ") :]
                        else:
                            curr_dict = ref

                    saveValueInRef(value, key, curr_dict)
                    line_history.clear()
                else:
                    # When deque reaches 2 lines, will automatically evict oldest
                    line_history.append(line)

        BaseRegTest.writeRefJSON(output_file, ref)


"""This strategy of dealing with error propagation to multiple procs is taken directly form openMDAO.utils;
It was not imported and used here to avoid adding openMDAO as a dependency. If openMDAO is added as a dependency in
the future this context manager definition should be replaced by an import"""


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
                raise exc[0](msg).with_traceback(exc[2])
            else:
                for m in allmsgs:
                    if m is not None:
                        raise RuntimeError(f"Exception raised on other rank: {m}.")
