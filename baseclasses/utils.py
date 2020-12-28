class CaseInsensitiveDict(dict):
    """
    Python dictionary where the keys are case-insensitive.
    Note that this assumes the keys are strings, and indeed will fail if you try to
    create an instance where keys are not strings.
    All common Python dictionary operations are supported, and additional operations
    can be added easily.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # convert keys to lower case
        for k in list(self.keys()):
            v = super().pop(k)
            self.__setitem__(k, v)

    def __setitem__(self, key, value):
        super().__setitem__(key.lower(), value)

    def __getitem__(self, key):
        return super().__getitem__(key.lower())

    def __contains__(self, key):
        return super().__contains__(key.lower())

    def __delitem__(self, key):
        super().__delitem__(key.lower())

    def pop(self, key, *args, **kwargs):
        super().pop(key.lower(), *args, **kwargs)

    def get(self, key, *args, **kwargs):
        return super().get(key.lower(), *args, **kwargs)


class CaseInsensitiveSet(set):
    """
    Python set where the elements are case-insensitive.
    Note that this assumes the elements are strings, and indeed will fail if you try to
    create an instance where elements are not strings.
    All common Python set operations are supported, and additional operations
    can be added easily.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # convert entries to lowe case
        for k in self:
            super().remove(k)
            self.add(k)

    def add(self, item):
        super().add(item.lower())

    def __contains__(self, item):
        return super().__contains__(item.lower())


class Error(Exception):
    """
    Format the error message in a box to make it clear this
    was a expliclty raised exception.
    """

    def __init__(self, message):
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
        print(msg)
        super().__init__()
