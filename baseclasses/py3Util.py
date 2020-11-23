"""
Helper methods for supporting python3 and python2 at the same time
"""

import sys


def getPy3SafeString(string):
    """Accepts a <string> and makes sure its converted to unicode for python 3.6 and above"""

    if string is None:
        return None

    # python 3.6 compatibility requires that we force things into a binary string
    #       representation for the dictioanry key because the stuff coming out of f2py is binary-strings
    if sys.version_info >= (3, 6) and isinstance(string, bytes):
        return string.decode("utf-8")

    return string
