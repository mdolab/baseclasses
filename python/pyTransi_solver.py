#!/usr/local/bin/python
"""
pyAero_solver

Holds the Python Aerodynamic Analysis Classes (base).

Copyright (c) 2012 by Charles A. Mader and Gaetan K.W. Kenway
All rights reserved. Not to be used for commercial purposes.
Revision: 2.0   $Date: 24/08/2016 21:00$


Developers:
-----------
- Ruben E. Perez (RP)
- Dr. Charles A. Mader (CM)
- Dr. Gaetan K.W. Kenway (GK)

History
-------
    v. 1.0    - Initial Class Creation (RP, 2008)
    v. 2.0    - Major addition of functionality to the base class (CM,2016)
"""

# =============================================================================
# Standard Python modules
# =============================================================================
import os, sys
import pdb
import numpy
from pprint import pprint as pp
# =============================================================================
# External Python modules
# =============================================================================
#import external

# =============================================================================
# Extension modules
# =============================================================================
from pyTransi_problem import TransiProblem

# =============================================================================
# Misc Definitions
# =============================================================================

class CaseInsensitiveDict(dict):
    def __setitem__(self, key, value):
        super(CaseInsensitiveDict, self).__setitem__(key.lower(), value)

    def __getitem__(self, key):
        return super(CaseInsensitiveDict, self).__getitem__(key.lower())

    def __contains__(self, key):
        return super(CaseInsensitiveDict, self).__contains__(key.lower())

class Error(Exception):
    """
    Format the error message in a box to make it clear this
    was a expliclty raised exception.
    """
    def __init__(self, message):
        msg = '\n+'+'-'*78+'+'+'\n' + '| TransiSolver Error: '
        i = 19
        for word in message.split():
            if len(word) + i + 1 > 78: # Finish line and start new one
                msg += ' '*(78-i)+'|\n| ' + word + ' '
                i = 1 + len(word)+1
            else:
                msg += word + ' '
                i += len(word)+1
        msg += ' '*(78-i) + '|\n' + '+'+'-'*78+'+'+'\n'
        print(msg)
        Exception.__init__(self)


# =============================================================================
# AeroSolver Class
# =============================================================================

class TransiSolver(object):
    
    """
    Abstract Class for Tranisition Solver Object
    """
    
    def __init__(self, name, category={}, def_options={}, informs={}, *args, **kwargs):
        
        """
        AeroSolver Class Initialization
        
        Documentation last updated:  May. 21, 2008 - Ruben E. Perez
        """
        
        # 
        self.name = name
        self.category = category
        self.options = CaseInsensitiveDict()
        self.defaultOptions = def_options
        self.informs = informs
        self.solverCreated = False
        self.families = CaseInsensitiveDict()
        #print(self.defaultOptions)
        #print(self.options)
        #print **kwargs
        # Initialize Options

        for key in self.defaultOptions:
            print(key)
            self.setOption(key, self.defaultOptions[key][1])

        koptions = kwargs.pop('options', CaseInsensitiveDict())
        #print(koptions)
        #print koptions
        #print self.options
        for key in koptions:
            #print (koptions[key])
            self.setOption(key, koptions[key])
            #print self.setOption
        self.solverCreated = True
        self._updateGeomInfo = False
        #print self.options
        #print 'defaultOptions'
        #print self.defaultOptions
        
    def setOption(self, name, value):
        """
        Default implementation of setOption()

        Parameters
        ----------
        name : str
           Name of option to set. Not case sensitive
        value : varries
           Value to set. Type is checked for consistency. 
        
        """
        name = name.lower()
        try: 
            self.defaultOptions[name]
        except KeyError:
            Error("Option \'%-30s\' is not a valid %s option."%(
                name,  self.name))

        # Make sure we are not trying to change an immutable option if
        # we are not allowed to.
        #if self.solverCreated and name in self.imOptions:
        #    raise Error("Option '%-35s' cannot be modified after the solver "
        #                "is created."%name)

        # Now we know the option exists, lets check if the type is ok:
        if isinstance(value, self.defaultOptions[name][0]):
            # Just set:
            self.options[name] = [type(value), value]
        else:
            raise Error("Datatype for Option %-35s was not valid \n "
                        "Expected data type is %-47s \n "
                        "Received data type is %-47s"% (
                            name, self.defaultOptions[name][0], type(value)))
                    
    def getOption(self, name):
        """
        Default implementation of getOption()

        Parameters
        ----------
        name : str
           Name of option to get. Not case sensitive

        Returns
        -------
        value : varries
           Return the curent value of the option.         
        """

        if name.lower() in self.defaultOptions:
            return self.options[name.lower()][1]
        else:
            raise Error('%s is not a valid option name.'% name)

    def printCurrentOptions(self):

        """
        Prints a nicely formatted dictionary of all the current solver
        options to the stdout on the root processor"""
        if self.comm.rank == 0:
            print('+---------------------------------------+')
            print('|          All %s Options:            |'%self.name)
            print('+---------------------------------------+')
            # Need to assemble a temporary dictionary
            tmpDict = {}
            for key in self.options:
                tmpDict[key] = self.getOption(key)
            pp(tmpDict)

    def printModifiedOptions(self):

        """
        Prints a nicely formatted dictionary of all the current solver
        options that have been modified from the defaults to the root
        processor"""
        if self.comm.rank == 0:
            print('+---------------------------------------+')
            print('|      All Modified %s Options:       |'%self.name)
            print('+---------------------------------------+')
            # Need to assemble a temporary dictionary
            tmpDict = {}
            for key in self.options:
                if self.getOption(key) != self.defaultOptions[key][1]:
                    tmpDict[key] = self.getOption(key)
            pp(tmpDict)



        
