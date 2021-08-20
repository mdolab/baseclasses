# baseclasses
[![PyPI](https://img.shields.io/pypi/v/mdolab-baseclasses)](https://pypi.org/project/mdolab-baseclasses/)
[![conda](https://img.shields.io/conda/v/conda-forge/mdolab-baseclasses)](https://anaconda.org/conda-forge/mdolab-baseclasses)
[![Build Status](https://dev.azure.com/mdolab/Public/_apis/build/status/mdolab.baseclasses?repoName=mdolab%2Fbaseclasses&branchName=master)](https://dev.azure.com/mdolab/Public/_build/latest?definitionId=31&repoName=mdolab%2Fbaseclasses&branchName=master)
[![Documentation Status](https://readthedocs.com/projects/mdolab-baseclasses/badge/?version=latest)](https://mdolab-baseclasses.readthedocs-hosted.com/?badge=latest)
[![codecov](https://codecov.io/gh/mdolab/baseclasses/branch/master/graph/badge.svg?token=L4B85135LS)](https://codecov.io/gh/mdolab/baseclasses)

`baseclasses` contains, well, base classes that are used together with the rest of MDO Lab tools.
It includes the various `problems` to be defined by the user in order to perform certain analyses, such as
- `AeroProblem`
- `StructProblem`
- `AeroStructProblem`

It also contains some class definitions shared by various solvers, such as `AeroSolver`.
Finally, it also contains a class, `BaseRegTest`, which is used as part of the testing toolchain.
