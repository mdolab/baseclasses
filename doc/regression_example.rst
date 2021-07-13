.. _regression_example:

Regression Testing Example
--------------------------

:class:`baseclasses.BaseRegTest.BaseRegTest` provides a framework for creating regression tests.
It stores data in a JSON file format during *training* and compares test results against this stored data during *testing*.
Here, we will go through a short example of how to integrate this into Pythons's ``unittest`` framework, specifically when used with ``testflo``.

In this example, a regression test for a function called ``sampling.polynomial`` will be created.
This function returns a ``numpy`` array of values that are spaced between a start and end point according to a polynomial distribution.
The test function is structured as follows:

.. code-block:: python

    class TestSampling(unittest.TestCase):
        def test_polynomial(self, train=False):
            ref_file = os.path.join(baseDir, "ref/test_polynomial.ref")
            with BaseRegTest(ref_file, train=train) as handler:
                s = sampling.polynomial(0, 1, 100)
                handler.root_add_val("test_polynomial - Sample from Polynomial:", s, tol=1e-10)

The key difference from a typical unit test is the optional ``train`` flag.
When this flag is false then :meth:`baseclasses.BaseRegTest.BaseRegTest.root_add_val` will check the reference file for the value associated with the given key and compare it to the array ``s``.
When train is set to true, :meth:`root_add_val<baseclasses.BaseRegTest.BaseRegTest.root_add_val>` will instead store the current value of ``s`` in the reference file with the given key.
The ``with`` keyword is used to make sure that during training mode, the reference file is updated correctly at the end.

To quickly make the reference data for multiple regression tests we can create a corresponding train function:

.. code-block:: python

    def train_polynomial(self, train=True):
        test_polynomial(self, train=train)

Then, when running ``testflo`` we can specify to run all of the training functions using the ``-m`` flag.

.. code-block:: bash

  testflo -m train_*

Normally, when ``testflo`` is run, it looks for all functions that begin with ``test_``.
The ``-m`` flag allows us to specify a different prefix.
In this case, by using the ``train_`` prefix on all of the training functions we can run them all at once with the above command. 
Once the reference files are created, just calling ``testflo`` will run all the regression tests.
