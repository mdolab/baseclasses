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

To install, first clone the repo, then go into the root directory and type::

   pip install .

For stability we recommend cloning or checking out a tagged release.

The classes that the user will interact with are:

.. toctree::
   :maxdepth: 2

   pyAero_problem
   pyStruct_problem
   pyAeroStruct_problem
   pyMission_problem
   pyWeight_problem

The remainder of the documentation for the solver base classes can be
found on the full API documentation page:

.. toctree::
   :maxdepth: 1

   API
