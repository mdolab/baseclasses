from __future__ import print_function
from mpi4py import MPI
import pickle
import numpy
import os

class BaseRegTest(object):

    def __init__(self, ref_file, train=False, comm=None):
        self.ref_file = ref_file
        self.train = train
        if not self.train:
            # We need to check here that the reference file exists, otherwise
            # it will hang when it tries to open it on the root proc.
            assert(os.path.isfile(self.ref_file))

        if comm is not None:
            self.comm = comm
        else:
            self.comm = MPI.COMM_WORLD

        self.rank = self.comm.rank
        if self.rank == 0:
            self.counter = 0

            if self.train:
                self.db = []
            else:
                # with open(self.ref_file, 'rb') as file_handle:
                #     self.db = pickle.load(file_handle)
                with open(self.ref_file, 'r') as file_handle:
                    self.db = [float(val.rstrip()) for val in file_handle.readlines()]
        else:
            self.counter = None
            self.db = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.save()

    def save(self):
        if self.rank == 0 and self.train:
            # with open(self.ref_file, 'wb') as file_handle:
            #     pickle.dump(self.db, file_handle)
            with open(self.ref_file, 'w') as file_handle:
                file_handle.writelines('%23.16e\n' % val for val in self.db)

    # *****************
    # Public functions
    # *****************

    def root_print(self, s):
        if self.rank == 0:
            print(s)

    # Add values from root only
    def root_add_val(self, values, rel_tol=1e-12, abs_tol=1e-12, msg=None):
        """Add values but only on the root proc"""
        if self.rank == 0:
            self._add_values(values, rel_tol, abs_tol, msg)

    def root_add_dict(self, d, rel_tol=1e-12, abs_tol=1e-12, msg=None):
        """Only write from the root proc"""
        if self.rank == 0:
            self._add_dict(d, rel_tol, abs_tol, msg)

    # Add values from all processors
    def par_add_val(self, values, rel_tol=1e-12, abs_tol=1e-12, msg=None):
        """Add value(values) from parallel process in sorted order"""
        values = self.comm.gather(values)
        if self.rank == 0:
            for i in range(len(values)):
                print ('Value(s) on processor: %d'%i)
                self._add_values(values[i], rel_tol, abs_tol, msg)

    def par_add_sum(self, values, rel_tol=1e-12, abs_tol=1e-12, msg=None):
        """Add the sum of sum of the values from all processors."""
        reducedSum = self.comm.reduce(numpy.sum(values))
        if self.rank == 0:
            self._add_value(reducedSum, rel_tol, abs_tol, msg)

    def par_add_norm(self, values, rel_tol=1e-12, abs_tol=1e-12, msg=None):
        """Add the norm across values from all processors."""
        reducedSum = self.comm.reduce(numpy.sum(values**2))
        if self.rank == 0:
            self._add_value(numpy.sqrt(reducedSum), rel_tol, abs_tol, msg)

    # *****************
    # Private functions
    # *****************
    def _add_value(self, value, rel_tol, abs_tol, msg):
        # We only check floats and integers
        value = numpy.atleast_1d(value).flatten()
        assert(value.size == 1)
        value = value[0]
        if self.train:
            self.db.append(value)
        else:
            self._check_value(value, self.db[self.counter], rel_tol, abs_tol, msg)

        self.counter += 1

    def _check_value(self, actual, reference, rel_tol, abs_tol, msg):

        if msg is None:
            msg = "N/A"
        msg = "Failed value for: {}".format(msg)
        numpy.testing.assert_allclose(actual, reference, rtol=rel_tol, atol=abs_tol, err_msg=msg)
        

    def _add_values(self, values, rel_tol, abs_tol, msg):
        '''Add values in special value format'''
        values = numpy.atleast_1d(values)
        values = values.flatten()
        for val in values:
            self._add_value(val, rel_tol, abs_tol, msg)

    def _add_dict(self, d, rel_tol, abs_tol, msg):
        """Add all values in a dictionary in sorted key order"""
        for key in sorted(d.keys()):
            if msg is None:
                key_msg = key
            else:
                key_msg = msg+': '+key
            if isinstance(d[key],dict):
                self._add_dict(d[key], rel_tol, abs_tol,key_msg)
            elif type(d[key]) == bool:
                self._add_value(int(d[key]), rel_tol, abs_tol, key_msg)
            else:
                self._add_values(d[key], rel_tol, abs_tol, key_msg)                