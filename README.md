# baseclasses
![PyPI](https://img.shields.io/pypi/v/mdolab-baseclasses)
[![Build Status](https://travis-ci.com/mdolab/baseclasses.svg?branch=master)](https://travis-ci.com/mdolab/baseclasses)
[![Documentation Status](https://readthedocs.com/projects/mdolab-baseclasses/badge/?version=latest)](https://mdolab-baseclasses.readthedocs-hosted.com/?badge=latest)

`baseclasses` contains, well, base classes that are used together with the rest of MDO Lab tools.
It includes the various `problems` to be defined by the user in order to perform certain analyses, such as
- `AeroProblem`
- `StructProblem`
- `AeroStructProblem`

It also contains some class definitions shared by various solvers, such as `AeroSolver`.
Finally, it also contains a class, `BaseRegTest`, which is used as part of the testing toolchain.
