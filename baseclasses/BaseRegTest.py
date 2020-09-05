try:
    from mpi4py import MPI
except ImportError:
    print("Warning: unable to find mpi4py. Parallel regression tests will cause errors")
import numpy
import os
import json
from collections import deque


class BaseRegTest(object):
    def __init__(self, ref_file, train=False, comm=None, check_arch=False):
        self.ref_file = ref_file
        self.train = train
        if self.train:
            self.db = {}
        else:
            # We need to check here that the reference file exists, otherwise
            # it will hang when it tries to open it on the root proc.
            assert os.path.isfile(self.ref_file)
            self.db = self.readRef()

        if comm is not None:
            self.comm = comm
        else:
            self.comm = MPI.COMM_WORLD

        self.rank = self.comm.rank

        # dictionary of real/complex PETSc arch names
        self.arch = {"real": None, "complex": None}
        # If we specify the test type, verify that the $PETSC_ARCH contains 'real' or 'complex',
        # and sets the self.arch flag appropriately
        if check_arch:
            self.checkPETScArch()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # self.save()
        pass

    def getRef(self):
        return self.db

    def writeRef(self):
        writeRefJSON(self.ref_file, self.db)

    def readRef(self):
        return readRefJSON(self.ref_file)

    def checkPETScArch(self):
        # Determine real/complex petsc arches: take the one when the script is
        # called to be the real:
        self.arch["real"] = os.environ.get("PETSC_ARCH")
        pdir = os.environ.get("PETSC_DIR")
        # Directories in the root of the petsc directory
        dirs = [o for o in os.listdir(pdir) if os.path.isdir(pdir + "/" + o)]
        # See if any one has 'complex' in it...basically we want to see if
        # an architecture has 'complex' in it which means it is (most
        # likely) a complex build
        carch = []
        for d in dirs:
            if "complex" in d.lower():
                carch.append(d)
        if len(carch) > 0:
            # take the first one if there are multiple
            self.arch["complex"] = carch[0]
        else:
            self.arch["complex"] = None

    # *****************
    # Public functions
    # *****************

    def root_print(self, s):
        if self.rank == 0:
            print(s)

    # Add values from root only
    def root_add_val(self, values, name, rel_tol=1e-12, abs_tol=1e-12):
        """Add values but only on the root proc"""
        if self.rank == 0:
            self._add_values(values, name, rel_tol, abs_tol)

    def root_add_dict(self, d, name, rel_tol=1e-12, abs_tol=1e-12):
        """Only write from the root proc"""
        if self.rank == 0:
            self._add_dict(d, name, rel_tol, abs_tol)

    # Add values from all processors
    def par_add_val(self, values, name, rel_tol=1e-12, abs_tol=1e-12):
        """Add value(values) from parallel process in sorted order"""
        values = self.comm.gather(values)
        if self.rank == 0:
            for i in range(len(values)):
                print("Value(s) on processor: %d" % i)
                self._add_values(values[i], name, rel_tol, abs_tol)

    def par_add_sum(self, values, name, rel_tol=1e-12, abs_tol=1e-12):
        """Add the sum of sum of the values from all processors."""
        reducedSum = self.comm.reduce(numpy.sum(values))
        if self.rank == 0:
            self._add_value(reducedSum, name, rel_tol, abs_tol)

    def par_add_norm(self, values, name, rel_tol=1e-12, abs_tol=1e-12):
        """Add the norm across values from all processors."""
        reducedSum = self.comm.reduce(numpy.sum(values ** 2))
        if self.rank == 0:
            self._add_value(numpy.sqrt(reducedSum), name, rel_tol, abs_tol)

    # *****************
    # Private functions
    # *****************
    def _add_value(self, value, name, rel_tol, abs_tol, db=None, err_name=None):
        # We only check floats and integers
        if db is None:
            db = self.db

        if err_name is None:
            err_name = name

        value = numpy.atleast_1d(value).flatten()
        assert value.size == 1

        value = value[0]
        if self.train:
            db[name] = value
        else:
            self.assert_allclose(value, db[name], err_name, rel_tol, abs_tol)

    def assert_allclose(self, actual, reference, name, rel_tol, abs_tol):
        msg = "Failed value for: {}".format(name)
        numpy.testing.assert_allclose(actual, reference, rtol=rel_tol, atol=abs_tol, err_msg=msg)

    def _add_values(self, values, name, rel_tol, abs_tol, db=None, err_name=None):
        """Add values in special value format"""
        # values = numpy.atleast_1d(values)
        # values = values.flatten()
        # for val in values:
        #     self._add_value(val, *args, **kwargs)

        if db is None:
            db = self.db
        if err_name is None:
            err_name = name
        if self.train:
            db[name] = values
        else:
            self.assert_allclose(values, db[name], err_name, rel_tol, abs_tol)

    def _add_dict(self, d, dict_name, rel_tol, abs_tol, db=None, err_name=None):
        """Add all values in a dictionary in sorted key order"""

        if self.train:
            self.db[dict_name] = {}
        if db is None:
            db = self.db

        for key in sorted(d.keys()):
            print(dict_name, key)
            # if msg is None:
            #     key_msg = key
            if err_name:
                key_msg = err_name + ":" + dict_name + ": " + key
            else:
                key_msg = dict_name + ": " + key

            if type(d[key]) == bool:
                self._add_value(int(d[key]), key, rel_tol, abs_tol, db=db[dict_name], err_name=key_msg)
            if isinstance(d[key], dict):
                # do some good ol' fashion recursion
                self._add_dict(d[key], key, rel_tol, abs_tol, db=db[dict_name], err_name=dict_name)
            else:
                self._add_values(d[key], key, rel_tol, abs_tol, db=self.db[dict_name], err_name=key_msg)

    # *****************
    # Static helper method
    # *****************

    @staticmethod
    def setLocalPaths(baseDir, sys_path):
        """added the necessary paths to the version of the files within the same 
        repo"""
        repoDir = baseDir.split("/tests/")[0]
        sys_path.append(repoDir)

        testDir = baseDir.split("/reg_tests/")[0]
        regTestDir = testDir + "/reg_tests"
        sys_path.append(regTestDir)

    @staticmethod
    def getLocalDirPaths(baseDir):
        """Returns the paths to the reference files and input and outputs based on the 
        directory of the file (baseDir)"""
        refDir = baseDir.replace("reg_tests", "reg_tests/refs")

        testDir = baseDir.split("/reg_tests")[0]
        inputDir = os.path.join(testDir, "input_files")
        outputDir = os.path.join(testDir, "output_files")

        return refDir, inputDir, outputDir


# =============================================================================
#                         reference files I/O
# =============================================================================

# based on this stack overflow answer https://stackoverflow.com/questions/3488934/simplejson-and-numpy-array/24375113#24375113
def writeRefJSON(file_name, ref):

    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            """If input object is an ndarray it will be converted into a dict 
            holding dtype, shape and the data, base64 encoded.
            """
            if isinstance(obj, numpy.ndarray):
                if obj.flags["C_CONTIGUOUS"]:
                    pass
                else:
                    obj = numpy.ascontiguousarray(obj)
                    assert obj.flags["C_CONTIGUOUS"]
                shape = obj.shape
                return dict(__ndarray__=obj.tolist(), dtype=str(obj.dtype), shape=shape)

            # Let the base class default method raise the TypeError
            super(NumpyEncoder, self).default(obj)

    with open(file_name, "w") as json_file:
        json.dump(ref, json_file, sort_keys=True, indent=4, separators=(",", ": "), cls=NumpyEncoder)

# based on this stack overflow answer https://stackoverflow.com/questions/3488934/simplejson-and-numpy-array/24375113#24375113
def readRefJSON(file_name):
    def json_numpy_obj_hook(dct):
        """Decodes a previously encoded numpy ndarray with proper shape and dtype.

        :param dct: (dict) json encoded ndarray
        :return: (ndarray) if input was an encoded ndarray
        """
        if isinstance(dct, dict) and "__ndarray__" in dct:
            data = dct["__ndarray__"]
            return numpy.array(data, dct["dtype"]).reshape(dct["shape"])
        return dct

    with open(file_name, "r") as json_file:
        data = json.load(json_file, object_hook=json_numpy_obj_hook)

    return data

def convertRegFileToJSONRegFile(file_name, output_file=None):
    """ converts from the old format of regression test file to the new JSON format"""

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
    with open(file_name, "r") as fid:
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

    writeRefJSON(output_file, ref)
