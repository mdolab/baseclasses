from setuptools import setup, find_packages
import os
import re

__version__ = re.findall(
    r"""__version__ = ["']+([0-9\.]*)["']+""",
    open("baseclasses/__init__.py").read(),
)[0]

this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="mdolab-baseclasses",
    version=__version__,
    description="base classes that are used together with the rest of MDO Lab tools.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="",
    author_email="",
    url="https://github.com/mdolab/baseclasses",
    license="Apache License Version 2.0",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.16",
    ],
    classifiers=[
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering",
        "Programming Language :: Python",
    ],
)
