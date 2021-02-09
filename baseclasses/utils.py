import copy


class CaseInsensitiveDict(dict):
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
        super().__init__(*args, **kwargs)
        self._updateMap()

    def _updateMap(self):
        """
        This function updates self.map based on self.keys().
        """
        self.map = {k.lower(): k for k in self.keys()}

    def _getKey(self, key):
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

    def __setitem__(self, key, value):
        existingKey = self._getKey(key)
        if existingKey:
            key = existingKey
        else:
            self.map[key.lower()] = key
        super().__setitem__(key, value)

    def __getitem__(self, key):
        existingKey = self._getKey(key)
        if existingKey:
            key = existingKey
        return super().__getitem__(key)

    def __contains__(self, key):
        return key.lower() in self.map.keys()

    def __delitem__(self, key):
        existingKey = self._getKey(key)
        if existingKey:
            key = existingKey
            self.map.pop(key.lower())
        super().__delitem__(key)

    def pop(self, key, *args, **kwargs):
        existingKey = self._getKey(key)
        if existingKey:
            key = existingKey
            self.map.pop(key.lower())
        super().pop(key, *args, **kwargs)

    def get(self, key, *args, **kwargs):
        existingKey = self._getKey(key)
        if existingKey:
            key = existingKey
        return super().get(key, *args, **kwargs)

    def update(self, d, *args, **kwargs):
        if not isinstance(d, CaseInsensitiveDict):
            super().update(d, *args, **kwargs)
        else:
            # we need to first remove duplicate entries
            # make a copy to avoid modifying d
            d_copy = copy.copy(d)
            for k in list(d_copy.keys()):
                if k.lower() in self.map:
                    d_copy.pop(k)
            super().update(d_copy, *args, **kwargs)
        self._updateMap()

    def __new__(self, *args, **kwargs):
        """
        This is a custom __new__ implementation. All it does is set self.map to an empty dictionary.
        This is here so the class instance can be pickled, and therefore used by mpi4py for bcast etc.
        """
        self.map = {}
        return super().__new__(self)

    def __eq__(self, other):
        selfLower = {k.lower(): v for k, v in self.items()}
        otherLower = {k.lower(): v for k, v in other.items()}
        return selfLower.__eq__(otherLower)


class CaseInsensitiveSet(set):
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
        super().__init__(*args, **kwargs)
        self._updateMap()

    def _updateMap(self):
        self.map = {k.lower(): k for k in list(self)}

    def _getItem(self, item):
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

    def _getKeys(self):
        """
        This function returns the original, capitalized keys.
        The lower-case keys can be accessed via self.map.keys().
        Note that the equivalent method for dict is built in using set(self.keys()).

        Returns
        -------
        set
            the set of keys with original capitalization
        """
        s = set()
        for k, v in self.map.items():
            s.add(v)
        return s

    def add(self, item):
        existingItem = self._getItem(item)
        if existingItem:
            item = existingItem
        else:
            self.map[item.lower()] = item
        super().add(item)

    def update(self, d, *args, **kwargs):
        if not isinstance(d, CaseInsensitiveSet):
            super().update(d, *args, **kwargs)
        else:
            # we need to first remove duplicate entries
            # make a copy to avoid modifying d
            d_copy = copy.copy(d)
            for k in d_copy._getKeys():
                if k.lower() in self.map:
                    d_copy.remove(k)
            super().update(d_copy, *args, **kwargs)
        self._updateMap()

    def union(self, d, *args, **kwargs):
        r = super().union(d, *args, **kwargs)
        self._updateMap()
        return CaseInsensitiveSet(r)

    def issubset(self, other):
        lowerSelf = set([s.lower() for s in self])
        lowerOther = set([s.lower() for s in other])
        return lowerSelf.issubset(lowerOther)

    def remove(self, item):
        existingItem = self._getItem(item)
        if existingItem:
            item = existingItem
            self.map.pop(item.lower())
        super().remove(item)

    def __contains__(self, item):
        return item.lower() in self.map.keys()

    def __eq__(self, other):
        a = set([s.lower() for s in list(self)])
        b = set([o.lower() for o in list(other)])
        return a.__eq__(b)


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
