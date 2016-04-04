#!/usr/local/bin/python
"""
pyAero_solver

Holds the Python Aerodynamic Analysis Classes (base and inherited).

Copyright (c) 2008 by Dr. Ruben E. Perez
All rights reserved. Not to be used for commercial purposes.
Revision: 1.1   $Date: 21/05/2008 21:00$


Developers:
-----------
- Dr. Ruben E. Perez (RP)

History
-------
    v. 1.0    - Initial Class Creation (RP, 2008)
"""

# =============================================================================
# Standard Python modules
# =============================================================================
import os, sys
import pdb

# =============================================================================
# External Python modules
# =============================================================================
#import external

# =============================================================================
# Extension modules
# =============================================================================
from pyAero_problem import AeroProblem

# =============================================================================
# Misc Definitions
# =============================================================================

class CaseInsensitiveDict(dict):
    def __setitem__(self, key, value):
        super(CaseInsensitiveDict, self).__setitem__(key.lower(), value)

    def __getitem__(self, key):
        return super(CaseInsensitiveDict, self).__getitem__(key.lower())

class Error(Exception):
    """
    Format the error message in a box to make it clear this
    was a expliclty raised exception.
    """
    def __init__(self, message):
        msg = '\n+'+'-'*78+'+'+'\n' + '| AeroSolver Error: '
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

class AeroSolver(object):
    
    """
    Abstract Class for Aerodynamic Solver Object
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
        
        # Initialize Options
        for key in self.defaultOptions:
            self.setOption(key, self.defaultOptions[key][1])

        koptions = kwargs.pop('options', CaseInsensitiveDict())
        for key in koptions:
            self.setOption(key, koptions[key])
      
        
    def resetFlow(self):
        """
        Reset the flow to a uniform state
        """
        
        pass


    def getSurfaceCoordinates(self,group_name):
        """
        Return the set of surface coordinates cooresponding to a
        Particular group name
        """
        
        pass


    def setSurfaceCoordinates(self,group_name,coordinates):
        """
        Set the set of surface coordinates cooresponding to a
        Particular group name
        """
        
        pass

    def getForces(self,group_name):
        """
        Return the set of forces at the locations defined by 
        getSurfaceCoordinates
        """
        
        pass


    def globalNKPreCon(self,in_vec):
        """
        Precondition the residual in in_vec for a coupled 
        Newton-Krylov Method
        """

        pass

    def totalSurfaceDerivative(self,objective):
        """
        Return the total derivative of the objective at surface
        coordinates
        """

        pass


    def totalAeroDerivative(self,objective):
        """
        Return the total derivative of the objective with respect 
        to aerodynamic-only variables
        """

        pass


    def getResNorms(self):
        """
        Return the inital,starting and final residual norms for 
        the solver
        """
        
        pass


    def getStateSize(self):
        """
        Return the number of degrees of freedom (states) that are
        on this processor
        """

        pass


    def getStates(self):
        """
        Return the states on this processor.
        """

        pass


    def setStates(self,states):
        """ Set the states on this processor."""

        pass

    def getResidual(self):
        """
        Return the reisudals on this processor.
        """

        pass


    def getSolution(self):
        """
        Retrieve the solution dictionary from the solver
        """
        
        pass

    def solveAdjoint(self,objective, *args, **kwargs):
        """
        Solve the adjoint problem for the desired objective functions.

        objectives - List of objective functions
    
        """
        pass
            
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
                self.name,  name))

        # Now we know the option exists, lets check if the type is ok:
        if type(value) == self.defaultOptions[name][0]:
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

