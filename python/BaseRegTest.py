from __future__ import print_function
from mpi4py import MPI
import pickle
import numpy

class BaseRegTest(object):

    def __init__(self, ref_file, train=False, comm=None):
        self.ref_file = ref_file
        self.train = train

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
                file_handle.writelines('%20.13e\n' % val for val in self.db)

    # *****************
    # Public functions
    # *****************

    def root_print(self, s):
        if self.rank == 0:
            print(s)

    # Add values from root only
    def root_add_val(self, values, rel_tol=1e-12, abs_tol=1e-12):
        """Add values but only on the root proc"""
        if self.rank == 0:
            self._add_values(values, rel_tol, abs_tol)

    def root_add_dict(self, d, rel_tol=1e-12, abs_tol=1e-12):
        """Only write from the root proc"""
        if self.rank == 0:
            self._add_dict(d, rel_tol, abs_tol)

    # Add values from all processors
    def par_add_val(self, values, rel_tol=1e-12, abs_tol=1e-12):
        """Add value(values) from parallel process in sorted order"""
        values = self.comm.gather(values)
        if self.rank == 0:
            for i in xrange(len(values)):
                print ('Value(s) on processor: %d'%i)
                self._add_values(values[i], rel_tol, abs_tol)

    def par_add_sum(self, values, rel_tol=1e-12, abs_tol=1e-12):
        """Add the sum of sum of the values from all processors."""
        reducedSum = self.comm.reduce(numpy.sum(values))
        if self.rank == 0:
            self._add_value(reducedSum, rel_tol, abs_tol)

    def par_add_norm(self, values, rel_tol=1e-12, abs_tol=1e-12):
        """Add the norm across values from all processors."""
        reducedSum = self.comm.reduce(numpy.sum(values**2))
        if self.rank == 0:
            self._add_value(numpy.sqrt(reducedSum), rel_tol, abs_tol)

    # *****************
    # Private functions
    # *****************
    def _add_value(self, value, rel_tol=1e-12, abs_tol=1e-12):
        # We only check floats and integers
        value = numpy.atleast_1d(value).flatten()
        assert(len(value) == 1)
        value = value[0]
        if self.train:
            self.db.append(value)
        else:
            self._check_value(value, self.db[self.counter], rel_tol, abs_tol)

        self.counter += 1

    def _check_value(self, val1, val2, rel_tol, abs_tol):
        rel_err = 0
        if val2 != 0:
            rel_err = abs((val1-val2)/val2)
        else:
            rel_err = abs((val1-val2)/(val2 + 1e-16))

        abs_err = abs(val1-val2)

        assert(abs_err < abs_tol or rel_err < rel_tol)

    def _add_values(self, values, rel_tol=1e-12, abs_tol=1e-12):
        '''Add values in special value format'''
        values = numpy.atleast_1d(values)
        values = values.flatten()
        for val in values:
            self._add_value(val, rel_tol, abs_tol)

    def _add_dict(self, d, rel_tol=1e-12, abs_tol=1e-12):
        """Add all values in a dictionary in sorted key order"""
        for key in sorted(d.keys()):
            print ('Dictionary Key: %s'%key)
            if isinstance(d[key],dict):
                self._add_dict(d[key], rel_tol, abs_tol)
            elif type(d[key]) == bool:
                self._add_value(int(d[key]), rel_tol, abs_tol)
            else:
                self._add_values(d[key], rel_tol, abs_tol)