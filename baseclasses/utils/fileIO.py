import numpy as np
import pickle
from collections import OrderedDict
import json
from sqlitedict import SqliteDict
from .containers import CaseInsensitiveDict, CaseInsensitiveSet


def writeJSON(fname, obj):
    """
    Write a dictionary to a reference JSON file.
    This includes a custom NumPy encoder to reliably write NumPy arrays to JSON, which can then be read back via :meth:`readJSON`.

    Parameters
    ----------
    file_name : str
        The file name
    ref : dict
        The dictionary
    """

    class MyEncoder(json.JSONEncoder):
        """
        Custom encoder class for Numpy arrays and CaseInsensitiveDict
        """

        def default(self, o):
            """
            If input object is an ndarray it will be converted into a dict
            holding dtype, shape and the data, base64 encoded.
            """
            if isinstance(o, np.ndarray):
                if o.flags["C_CONTIGUOUS"]:
                    pass
                else:
                    o = np.ascontiguousarray(o)
                    assert o.flags["C_CONTIGUOUS"]
                if o.size == 1:
                    return o.item()
                else:
                    return dict(__ndarray__=o.tolist(), dtype=str(o.dtype), shape=o.shape)
            elif isinstance(o, np.integer):
                return dict(__ndarray__=int(o), dtype=str(o.dtype), shape=o.shape)
            elif isinstance(o, np.floating):
                return dict(__ndarray__=float(o), dtype=str(o.dtype), shape=o.shape)
            elif isinstance(o, CaseInsensitiveDict):
                return dict(o)
            elif isinstance(o, CaseInsensitiveSet):
                return set(o)

            # Let the base class default method raise the TypeError
            super().default(o)

    with open(fname, "w") as json_file:
        json.dump(obj, json_file, sort_keys=True, indent=4, separators=(",", ": "), cls=MyEncoder)


def readJSON(fname):
    """
    Reads a JSON file and return the contents as a dictionary.
    This includes a custom NumPy reader to retrieve NumPy arrays, matching the :meth:`writeJSON` function.

    Parameters
    ----------
    file_name : str
        The file name


    References
    ----------
    This is based on `this stack overflow answer <https://stackoverflow.com/questions/3488934/simplejson-and-numpy-array/24375113#24375113>`_
    """

    def json_numpy_obj_hook(dct):
        """Decodes a previously encoded numpy ndarray with proper shape and dtype.

        :param dct: (dict) json encoded ndarray
        :return: (ndarray) if input was an encoded ndarray
        """
        if isinstance(dct, dict) and "__ndarray__" in dct:
            data = dct["__ndarray__"]
            return np.array(data, dct["dtype"]).reshape(dct["shape"])
        return dct

    with open(fname) as json_file:
        data = json.load(json_file, object_hook=json_numpy_obj_hook)

    return data
