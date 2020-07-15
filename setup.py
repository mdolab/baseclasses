from setuptools import setup
import re

__version__ = re.findall(
    r"""__version__ = ["']+([0-9\.]*)["']+""",
    open('baseclasses/__init__.py').read(),
)[0]

setup(name='baseclasses',
      version=__version__,
      description="baseclasses contains base classes that are used together with the rest of MDO lab tools.",
      long_description="""
      baseclasses contains, well, base classes that are used together with the rest of MDO lab tools. It includes the various problems to be defined by the user in order to perform some analyses, such as

          AeroProblem
          StructProblem
          AeroStructProblem

      It also contains some class definitions shared by various solvers, such as AeroSolver. Finally, it also contains a class, BaseRegTest, which is used as part of the testing toolchain.
      """,
      long_description_content_type="text/markdown",
      keywords='optimization shape-optimization multi-disciplinary',
      author='',
      author_email='',
      url='https://github.com/mdolab/baseclasses',
      license='Apache License Version 2.0',
      packages=[
          'baseclasses',
      ],
      classifiers=[
        "Operating System :: OS Independent",
        "Programming Language :: Python"]
      )

