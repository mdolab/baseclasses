from collections.abc import MutableMapping, MutableSet
from typing import Any, Dict, Optional
from pprint import pformat


class CaseInsensitiveDict(MutableMapping):
    """
    Python dictionary where the keys are case-insensitive.
    Note that this assumes the keys are strings, and indeed will fail if you try to
    create an instance where keys are not strings.
    All common Python dictionary operations are supported, and additional operations
    can be added easily.
    In order to preserve capitalization on key initialization, the implementation relies on storing
    a dictionary of mappings, which are used to check any new keys against existing keys and compare them
    in a case-insensitive fashion.

    Attributes
    ----------
    data : dict
        The equivalent case-sensitive dictionary. This stores the actual values.
    map : dict
        Dictionary of mappings between the lowercase representation and the initial capitalization.

    Warnings
    --------
    This container preserves the initial capitalization, such that
    any operation which operates on an existing entry will not modify it.
    This means that for example :meth:`__setitem__()` will NOT update the original capitalization.
    """

    def __init__(self, *args, **kwargs):
        self.data: dict = dict(*args, **kwargs)
        if not all([isinstance(i, str) for i in self.data]):
            raise TypeError("All keys must be strings!")
        self.map: Dict[str, str] = {k.lower(): k for k in self.data.keys()}

    def _getKey(self, key: str, raiseError=False):
        """
        This function checks if the input key already exists.
        Note that this check is case insensitive

        Parameters
        ----------
        key : str
            the key to check
        raiseError : bool
            if true, raise KeyError if ``key`` is not found.

        Returns
        -------
        str, None
            Returns the original key if it exists. Otherwise returns None.

        Raises
        ------
        KeyError
            If ``raiseError`` and key is not found.
        """
        if key.lower() in self.map:
            return self.map[key.lower()]
        else:
            if raiseError:
                raise KeyError(f"Key '{key}' not found.")
            return None

    def __setitem__(self, key: str, value: Any):
        if not isinstance(key, str):
            raise TypeError("All keys must be strings.")
        existingKey = self._getKey(key)
        if existingKey:
            key = existingKey
        self.data[key] = value
        self.map[key.lower()] = key

    def __getitem__(self, key: str) -> Any:
        existingKey = self._getKey(key, raiseError=True)
        return self.data[existingKey]

    def __delitem__(self, key: str):
        existingKey = self._getKey(key, raiseError=True)
        self.map.pop(existingKey.lower())
        self.data.pop(existingKey)

    def __iter__(self):
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def __eq__(self, other) -> bool:
        """We convert both to regular dict, and compare their lower case values"""
        selfLower = {k.lower(): v for k, v in self.items()}
        otherLower = {k.lower(): v for k, v in other.items()}
        return selfLower.__eq__(otherLower)

    def __repr__(self):
        return pformat(self.data)


class CaseInsensitiveSet(MutableSet):
    """
    Python set where the elements are case-insensitive.
    Note that this assumes the elements are strings, and indeed will fail if you try to
    create an instance where elements are not strings.
    All common Python set operations are supported, and additional operations
    can be added easily.
    In order to preserve capitalization on key initialization, the implementation relies on storing
    a dictionary of mappings which are used to check any new keys against existing keys and compare them
    in a case-insensitive fashion.

    Attributes
    ----------
    data : set
        The equivalent case-sensitive set.
    map : dict
        Dictionary of mappings between the lowercase representation and the initial capitalization.

    Warnings
    --------
    This container preserves the initial capitalization, such that
    any operation which operates on an existing entry will not modify it.
    This means that :meth:`add()` and :meth:`update()` will NOT update the original capitalization.
    """

    def __init__(self, *args, **kwargs):
        self.data: set = set(*args, **kwargs)
        if not all([isinstance(i, str) for i in self.data]):
            raise TypeError("All items must be strings!")
        self.map: Dict[str, str] = {k.lower(): k for k in list(self)}

    def _getItem(self, item: str) -> Optional[str]:
        """
        This function checks if the input item already exists.
        Note that this check is case insensitive

        Parameters
        ----------
        item : str
            the item to check

        Returns
        -------
        str, None
            Returns the original item if it exists. Otherwise returns None.
        """
        if item in self:
            return self.map[item.lower()]
        else:
            return None

    def add(self, item: str):
        if not isinstance(item, str):
            raise TypeError("All keys must be strings.")
        existingItem = self._getItem(item)
        # don't do anything if it exists
        if not existingItem:
            self.map[item.lower()] = item
            self.data.add(item)

    def __contains__(self, item) -> bool:
        if not isinstance(item, str):
            raise TypeError("All keys must be strings.")
        return item.lower() in self.map.keys()

    def __eq__(self, other) -> bool:
        """We convert both to regular set, and compare their lower case values"""
        if not all([isinstance(i, str) for i in other]):
            raise TypeError("All items must be strings!")
        a = {s.lower() for s in list(self)}
        b = {o.lower() for o in list(other)}
        return a.__eq__(b)

    def __len__(self) -> int:
        return len(self.data)

    def __iter__(self):
        return iter(self.data)

    def discard(self, item: str):
        existingItem = self._getItem(item)
        if existingItem:
            self.map.pop(existingItem.lower())
            self.data.discard(existingItem)

    def union(self, d):
        # make a copy of this object
        new_set = CaseInsensitiveSet(self.data)
        for item in d:
            existingItem = new_set._getItem(item)
            if not existingItem:
                new_set.add(item)
        return new_set

    def update(self, d):
        """Just call :meth:`add()` iteratively"""
        for item in d:
            self.add(item)

    def issubset(self, other) -> bool:
        """We convert both to regular set, and compare their lower case values"""
        lowerSelf = {s.lower() for s in self}
        lowerOther = {s.lower() for s in other}
        return lowerSelf.issubset(lowerOther)

    def __repr__(self):
        return pformat(self.data)
