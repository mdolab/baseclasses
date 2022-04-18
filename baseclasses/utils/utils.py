"""
Helper methods for supporting python3 and python2 at the same time
"""
import sys
from pprint import pformat


def getPy3SafeString(string):
    """Accepts a string and makes sure it's converted to unicode for python 3.6 and above"""

    if string is None:
        return None

    # python 3.6 compatibility requires that we force things into a binary string
    #       representation for the dictioanry key because the stuff coming out of f2py is binary-strings
    if sys.version_info >= (3, 6) and isinstance(string, bytes):
        return string.decode("utf-8")

    return string


def pp(obj, comm=None, flush=True):
    """
    Parallel safe printing routine. This method prints ``obj`` (via pprint) on the root proc of ``self.comm`` if it exists. Otherwise it will just print ``obj``.

    Parameters
    ----------
    obj : object
        Any Python object to be printed
    comm : MPI comm
        The MPI comm object on this processor
    flush : bool
        If True, the stream will be flushed.
    """
    if (comm is None) or (comm is not None and comm.rank == 0):
        # use normal print for string so there's no quotes
        if isinstance(obj, str):
            print(obj, flush=flush)
        # use pprint for everything else
        else:
            # we use pformat to get the string and then call print manually, that way we can flush if we need to
            pprint_str = pformat(obj)
            print(pprint_str, flush=flush)
