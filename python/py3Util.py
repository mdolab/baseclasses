"""
Helper methods for supporting python3 and python2 at the same time
"""

import sys

def getPy3BString(string): 
    '''Accepts a <string> and converts it into the py2 
       compatible binary format and forces it to lower case
    '''

    if string is None: 
        return None

    # python 3.6 compatibility requires that we force things into a binary string 
    #       representation for the dictioanry key because the stuff coming out of f2py is binary-strings
    if sys.version_info >= (3,6) and isinstance(string, str):
            return  bytes(string.lower(), encoding='utf-8') 

    return string.lower()


def getPy3BStringList(stringIter): 
    '''Accepts a list of <string> or dict of <string> keys and converts 
       it into a list of strings in the appropriate binary format. 
    '''

    # python 3.6 compatibility requires that we force things into a binary string 
    #       representation for the dictioanry key because the stuff coming out of f2py is binary-strings
    if sys.version_info >= (3,6): 

        bStringList = []
        for string in stringIter: 
            bStringList.append(getPy3BString(string))
        stringIter = bStringList
    return stringIter


