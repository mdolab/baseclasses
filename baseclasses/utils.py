from collections.abc import MutableMapping, MutableSet
from typing import Any, Dict, Optional


class CaseInsensitiveDict(MutableMapping):
    """
    Python dictionary where the keys are case-insensitive.
    Note that this assumes the keys are strings, and indeed will fail if you try to
    create an instance where keys are not strings.
    All common Python dictionary operations are supported, and additional operations
    can be added easily.
    In order to preserve capitalization on key initialization, the implementation relies on storing
    a dictionary of mappings between the lowercase representation and the initial capitalization,
    which is stored in self.map.
    By looking up in these mappings, we can check any new keys against existing keys and compare them
    in a case-insensitive fashion.
    """

    def __init__(self, *args, **kwargs):
        self.data: dict = dict(*args, **kwargs)
        if not all([isinstance(i, str) for i in self.data]):
            raise ValueError("All keys must be strings!")
        self.map: Dict[str, str] = {k.lower(): k for k in self.data.keys()}

    def _getKey(self, key: str):
        """
        This function checks if the input key already exists.
        Note that this check is case insensitive

        Parameters
        ----------
        key : str
            the key to check

        Returns
        -------
        str, None
            Returns the original key if it exists. Otherwise returns None.
        """
        if key.lower() in self.map:
            return self.map[key.lower()]
        else:
            return None

    def __setitem__(self, key: str, value: Any):
        existingKey = self._getKey(key)
        if existingKey:
            key = existingKey
        self.data[key] = value
        self.map[key.lower()] = key

    def __getitem__(self, key: str) -> Any:
        existingKey = self._getKey(key)
        return self.data[existingKey]

    def __delitem__(self, key: str):
        existingKey = self._getKey(key)
        if existingKey:
            self.map.pop(existingKey.lower())
            self.data.pop(existingKey)

    def __iter__(self):
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data.keys())

    def __eq__(self, other) -> bool:
        selfLower = {k.lower(): v for k, v in self.items()}
        otherLower = {k.lower(): v for k, v in other.items()}
        return selfLower.__eq__(otherLower)


class CaseInsensitiveSet(MutableSet):
    """
    Python set where the elements are case-insensitive.
    Note that this assumes the elements are strings, and indeed will fail if you try to
    create an instance where elements are not strings.
    All common Python set operations are supported, and additional operations
    can be added easily.
    In order to preserve capitalization on key initialization, the implementation relies on storing
    a dictionary of mappings between the lowercase representation and the initial capitalization,
    which is stored in self.map.
    By looking up in these mappings, we can check any new keys against existing keys and compare them
    in a case-insensitive fashion.
    """

    def __init__(self, *args, **kwargs):
        self.data: set = set(*args, **kwargs)
        if not all([isinstance(i, str) for i in self.data]):
            raise ValueError("All items must be strings!")
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
        if item.lower() in self.map:
            return self.map[item.lower()]
        else:
            return None

    def add(self, item: str):
        existingItem = self._getItem(item)
        if existingItem:
            item = existingItem
        else:
            self.map[item.lower()] = item
            self.data.add(item)

    def __contains__(self, item) -> bool:
        return item.lower() in self.map.keys()

    def __eq__(self, other) -> bool:
        """We convert both to regular set, and compare their lower case values"""
        a = set([s.lower() for s in list(self)])
        b = set([o.lower() for o in list(other)])
        return a.__eq__(b)

    def __len__(self) -> int:
        return len(self.data)

    def __iter__(self):
        return iter(self.data)

    def discard(self, item: str):
        existingItem = self._getItem(item)
        if existingItem:
            item = existingItem
            self.map.pop(item.lower())
            self.data.discard(item)

    def union(self, d):
        new_set = CaseInsensitiveSet(self.data)
        for k in d:
            existingItem = new_set._getItem(k)
            if existingItem:
                item = existingItem
            else:
                item = k
            new_set.add(item)
        return new_set

    def update(self, d):
        for item in d:
            self.add(item)

    def issubset(self, other) -> bool:
        lowerSelf = set([s.lower() for s in self])
        lowerOther = set([s.lower() for s in other])
        return lowerSelf.issubset(lowerOther)


class Error(Exception):
    """
    Format the error message in a box to make it clear this
    was a explicitly raised exception.
    """

    def __init__(self, message):
        self.message = message
        msg = "\n+" + "-" * 78 + "+" + "\n" + "| Error: "
        i = 8
        for word in message.split():
            if len(word) + i + 1 > 78:  # Finish line and start new one
                msg += " " * (78 - i) + "|\n| " + word + " "
                i = 1 + len(word) + 1
            else:
                msg += word + " "
                i += len(word) + 1
        msg += " " * (78 - i) + "|\n" + "+" + "-" * 78 + "+" + "\n"
        super().__init__(msg)
