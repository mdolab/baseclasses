from __future__ import print_function
try:
    from mpi4py import MPI
except:
    print('Warning: unable to find mpi4py. Parallel regression tests will cause errors')
import pickle
import numpy
import os
import pprint

class BaseRegTest(object):

    def __init__(self, ref , train=False, comm=None, check_arch=False):
        # self.ref_file = ref_file

        self.setRef(ref)
        self.train = train
        # if not self.train:
        #     # We need to check here that the reference file exists, otherwise
        #     # it will hang when it tries to open it on the root proc.
        #     assert(os.path.isfile(self.ref_file))

        if comm is not None:
            self.comm = comm
        else:
            self.comm = MPI.COMM_WORLD

        self.rank = self.comm.rank
        # if self.rank == 0:
        #     self.counter = 0

        #     if self.train:
        #         self.db = []
        #     else:
        #         # with open(self.ref_file, 'rb') as file_handle:
        #         #     self.db = pickle.load(file_handle)
        #         with open(self.ref_file, 'r') as file_handle:
        #             self.db = [float(val.rstrip()) for val in file_handle.readlines()]
        # else:
        #     self.counter = None
        #     self.db = None


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

    # def save(self):
    #     if self.rank == 0 and self.train:
    #         # with open(self.ref_file, 'wb') as file_handle:
    #         #     pickle.dump(self.db, file_handle)

    #         with open(self.ref_file, 'w') as file_handle:
    #             file_handle.writelines('%23.16e\n' % val for val in self.db)
    
    #         with open(output_file, 'w') as fid:
    #             ref_str = pprint.pformat(ref)
    #             fid.write('from numpy import array\n\n')
    #             fid.write( 'ref = ' + ref_str )



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
        

    def _add_values(self, values, name, rel_tol, abs_tol, db=None, err_name=None):
        '''Add values in special value format'''
        # values = numpy.atleast_1d(values)
        # values = values.flatten()
        # for val in values:
        #     self._add_value(val, *args, **kwargs)

        if db == None:
            db = self.db

        if err_name == None:
            err_name = name

        if self.train:
            db[name] = values
        else:
            self.assert_allclose(values, db[name], err_name, rel_tol, abs_tol)


    def _add_dict(self, d, dict_name, rel_tol, abs_tol, db=None, err_name=None):
        """Add all values in a dictionary in sorted key order"""
        
        if self.train:
            self.db[dict_name] = {}

        if db == None:
            db = self.db



        for key in sorted(d.keys()):
            print(dict_name, key)
            # if msg is None:
            #     key_msg = key
            if err_name:
                key_msg = err_name+ ':' + dict_name+': '+key
            else:
                key_msg = dict_name+': '+key

            # if isinstance(d[key],dict):
            #     self._add_dict(d[key], dict_name, rel_tol, abs_tol)
            if type(d[key]) == bool:
                self._add_value(int(d[key]), key, rel_tol, abs_tol, db=db[dict_name], err_name=key_msg)
            if isinstance(d[key], dict):
                # do some good ol' fashion recursion 
                self._add_dict(d[key], key, rel_tol, abs_tol, db=db[dict_name], err_name=dict_name)
            else:
                self._add_values(d[key], key, rel_tol, abs_tol, db=db[dict_name], err_name=key_msg)


    # *****************
    # Static helper method
    # *****************

    @staticmethod
    def setLocalPaths(baseDir, sys_path):
        """added the necessary paths to the version of the files within the same 
        repo"""
        repoDir = baseDir.split('/tests/')[0]
        sys_path.append(repoDir)

        testDir = baseDir.split('/reg_tests/')[0]
        regTestDir = testDir + '/reg_tests'
        sys_path.append(regTestDir)

    @staticmethod
    def getLocalDirPaths(baseDir):
        """Returns the paths to the reference files and input and outputs based on the 
        directory of the file (baseDir)"""
        refDir = baseDir.replace('reg_tests','reg_tests/refs')

        testDir = baseDir.split('/reg_tests')[0]
        inputDir = os.path.join(testDir,'input_files')
        outputDir = os.path.join(testDir,'output_files')

        return refDir, inputDir, outputDir
