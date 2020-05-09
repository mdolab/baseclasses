from __future__ import print_function
from mpi4py import MPI
import numpy
import os
import pprint

class BaseRegTest(object):

    def __init__(self, ref , train=False, comm=None, check_arch=False):
        # self.ref_file = ref_file

        self.setRef(ref)
        self.train = train

        if comm is not None:
            self.comm = comm
        else:
            self.comm = MPI.COMM_WORLD

        self.rank = self.comm.rank

        # dictionary of real/complex PETSc arch names
        self.arch = {'real':None,'complex':None}
        # If we specify the test type, verify that the $PETSC_ARCH contains 'real' or 'complex',
        # and sets the self.arch flag appropriately
        if check_arch:
            self.checkPETScArch()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # self.save()
        pass

    def setRef(self, ref):
        self.db = ref

    def getRef(self):
        return self.db

    def setMode(self,train=False):
        self.train = train

    def checkPETScArch(self):
        # Determine real/complex petsc arches: take the one when the script is
        # called to be the real:
        self.arch['real'] = os.environ.get("PETSC_ARCH")
        pdir = os.environ.get("PETSC_DIR")
        # Directories in the root of the petsc directory
        dirs = [o for o in os.listdir(pdir) if os.path.isdir(pdir+'/'+o)]
        # See if any one has 'complex' in it...basically we want to see if
        # an architecture has 'complex' in it which means it is (most
        # likely) a complex build
        carch = []
        for d in dirs:
            if 'complex' in d.lower():
                carch.append(d)
        if len(carch) > 0:
            # take the first one if there are multiple
            self.arch['complex'] = carch[0]
        else:
            self.arch['complex'] = None

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
                print ('Value(s) on processor: %d'%i)
                self._add_values(values[i], name, rel_tol, abs_tol)

    def par_add_sum(self, values, name, rel_tol=1e-12, abs_tol=1e-12):
        """Add the sum of sum of the values from all processors."""
        reducedSum = self.comm.reduce(numpy.sum(values))
        if self.rank == 0:
            self._add_value(reducedSum, name, rel_tol, abs_tol)

    def par_add_norm(self, values, name, rel_tol=1e-12, abs_tol=1e-12):
        """Add the norm across values from all processors."""
        reducedSum = self.comm.reduce(numpy.sum(values**2))
        if self.rank == 0:
            self._add_value(numpy.sqrt(reducedSum), name, rel_tol, abs_tol)

    # *****************
    # Private functions
    # *****************
    def _add_value(self, value, name, rel_tol, abs_tol, db=None, err_name=None):
        # We only check floats and integers
        if db == None:
            db = self.db

        if err_name == None:
            err_name = name


        value = numpy.atleast_1d(value).flatten()
        assert(value.size == 1)

        value = value[0]
        if self.train:
            db[name] = value
        else:
            self.assert_allclose(value, db[name], err_name, rel_tol, abs_tol)


    def assert_allclose(self, actual, reference, name, rel_tol, abs_tol):
        msg = "Failed value for: {}".format(name)
        numpy.testing.assert_allclose(actual, reference, rtol=rel_tol, atol=abs_tol, err_msg=msg)
        

    def _add_values(self, values, *args, **kwargs):
        '''Add values in special value format'''
        values = numpy.atleast_1d(values)
        values = values.flatten()
        for val in values:
            self._add_value(val, *args, **kwargs)

    def _add_dict(self, d, dict_name, rel_tol, abs_tol):
        """Add all values in a dictionary in sorted key order"""
        
        if self.train:
            self.db[dict_name] = {}

        for key in sorted(d.keys()):
            
            # if msg is None:
            #     key_msg = key
            key_msg = dict_name+': '+key


            # if isinstance(d[key],dict):
            #     self._add_dict(d[key], dict_name, rel_tol, abs_tol)
            
            if type(d[key]) == bool:
                self._add_value(int(d[key]), key, rel_tol, abs_tol, db=self.db[dict_name], err_name=key_msg)
            
            else:
                self._add_values(d[key], key, rel_tol, abs_tol, db=self.db[dict_name], err_name=key_msg)