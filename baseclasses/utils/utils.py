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

def printArgs(args):
    """
    Prints the arguments passed to the script.

    Parameters
    ----------
    args : argparse.Namespace
        The object holding the arguments passed to the script from
        args = parser.parse_args()
    """
    args_dict = vars(args)
    longest_key = max(args_dict.keys(), key=len)
    longest_val = max([str(x) for x in args_dict.values()], key=len)
    divider = " : "

    box_width = len(longest_key) + len(longest_val) + len(divider)

    bar = "-" * box_width

    # add title in the middle of the bar to create header
    title = " Arguments "
    header = bar[:(len(bar) - len(title))//2] + title + bar[(len(bar)+len(title))//2:]

    print(header)
    for arg, arg_val in args_dict.items():
        print(f"{arg:{len(longest_key)}}" + divider + f"{arg_val}")
    print(bar)
