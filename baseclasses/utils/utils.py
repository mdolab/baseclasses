"""
Helper methods for supporting python3 and python2 at the same time
"""
import re
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


class ParseStringFormat(object):
    def __init__(self, fmt):
        """
        Parses the following string format:

            [align][sign][width][grouping_option][.precision][type]

        Note that ``fmt`` must be a valid format string and it should verified before using the parse.

        Parameters
        ----------
        fmt : str
            String format string, e.g., ``fmt = "{:^10}"``
        """

        # Initialize
        self._align = None
        self._sign = None
        self._zero = None
        self._width = None
        self._precision = None
        self._grouping_option = None
        self._ftype = None

        # Only get the content between the first {} and get rid of :
        fmt = fmt[fmt.find("{") + 1 : fmt.find("}")][1:]

        # Check for align characters. There can only be one for a valid string.
        align = re.search("[<>=^]", fmt)
        if align:
            self._align = align[0]

        # Check for sign characters. There can only be one for a valid string.
        sign = re.search("[+ -]", fmt)
        if sign:
            self._sign = sign[0]

        # Get width and precision
        for i, item in enumerate(re.findall("[0-9]+", fmt)):
            if i == 0:
                self._width = int(item)
            if i == 1:
                self._precision = int(item)

        # Check for grouping options
        gOption = re.search("[_,]", fmt)
        if gOption:
            self._grouping_option = gOption[0]

        # Get the formatting type
        ftype = re.search("[bcdeEfFgGnosxX%]", fmt)
        if ftype:
            self._ftype = ftype[0]

    @property
    def align(self):
        return self._align

    @property
    def sign(self):
        return self._sign

    @property
    def width(self):
        return self._width

    @property
    def precision(self):
        return self._precision

    @property
    def grouping_option(self):
        return self._grouping_option

    @property
    def ftype(self):
        return self._ftype
