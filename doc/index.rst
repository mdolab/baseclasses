.. baseClasses documentation master file, created by
   sphinx-quickstart on Sat Dec  7 13:50:49 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. _baseClasses:

===========
baseClasses
===========


The ``baseClasses`` repository contains common definitions for
aerodynamic, structural and aerostructural solvers, as well as classes
defining standard ways of describing aerodynamic, structural and
aerostructural problems for use in those classes.

----------
Installing
----------

The package may be installed by pip from PyPI, as::

   pip install mdolab-baseclassees

Or by Conda from the ``conda-forge`` channel, as::

   conda install -c conda-forge mdolab-baseclasses

Or from source, by cloning the repo and then running (from the repo root)::

   pip install .



.. toctree::
   :maxdepth: 1
   :caption: Problem Classes

   pyAero_problem
   pyStruct_problem
   pyAeroStruct_problem
   pyMission_problem
   pyWeight_problem


.. toctree::
   :maxdepth: 1
   :caption: Solver Classes

   BaseSolver
   pyAero_solver

.. toctree::
   :maxdepth: 1
   :caption: Testing Classes

   BaseRegTest
