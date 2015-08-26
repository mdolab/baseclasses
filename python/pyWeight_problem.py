'''
pyWeight_problem

Holds the weightProblem class for weightandbalance solvers.

Copyright (c) 2015 by Dr. Charles A. Mader 
All rights reserved. Not to be used for commercial purposes.
Revision: 1.0   $Date: 16/08/2015 21:00$


Developers:
-----------
- Dr. Charles A. Mader (CM)

History
-------
	v. 1.0 - Initial Class Creation (CM, 2015)

'''

import sys, numpy, copy
import warnings


class Error(Exception):
    """
    Format the error message in a box to make it clear this
    was a expliclty raised exception.
    """
    def __init__(self, message):
        msg = '\n+'+'-'*78+'+'+'\n' + '| WeightProblem Error: '
        i = 23
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


class WeightProblem(object):
    '''
    Weight Problem Object:

    This Weight Problem Object should contain all of the information required
    to estimate the weight of a particular component configuration.

    Parameters
    ----------
    
    name : str
        A name for the configuration
    
    evalFuncs : iteratble object containing strings
        The names of the functions the user wants evaluated for this weight 
        problem
    '''

    def __init__(self, name, **kwargs):
        """
        Initialize the mission problem
        """
        self.name=name
        
        self.components = {}
        self.fuelcases = []
        self.funcNames = {}
        self.currentDVs = {}
        self.solveFailed = False

        # Check for function list:
        self.evalFuncs = set()
        if 'evalFuncs' in kwargs:
            self.evalFuncs = set(kwargs['evalFuncs'])
            
    def addComponents(self, components): #*components?
        '''
        Append a list of components to the interal component list
        '''

        # Check if components is of type Component or list, otherwise raise Error
        if type(components) == list:
            pass
        elif type(components) == object:
            components = [components]
        else:
            raise Error('addComponents() takes in either a list of or a single component')

        # Add the components to the internal list
        for comp in components:
            self.components[comp.name]=comp

            for dvName in comp.DVs:
                key = self.name+'_'+dvName
                self.currentDVs[key] = comp.DVs[dvName].value
            # end

        return

    def setDesignVars(self, x):
        """
        Set the variables in the x-dict for this object.

        Parameters
        ----------
        x : dict
            Dictionary of variables which may or may not contain the
            design variable names this object needs
            """
        
        for compKey in self.components.keys():
            comp= self.components[compKey]
            for key in comp.DVs:
                dvName = self.name+'_'+key
                
                if dvName in x:
                    #print key,x[dvName]
                    xTmp = {key:x[dvName]}
                    comp.setDesignVars(xTmp)
                    self.currentDVs[dvName]=x[dvName]
             
        #print 'currentDVs',self.currentDVs

    def addVariablesPyOpt(self, optProb):
        """
        Add the current set of variables to the optProb object.

        Parameters
        ----------
        optProb : pyOpt_optimization class
            Optimization problem definition to which variables are added
            """

        for compKey in self.components.keys():
            comp= self.components[compKey]
            for key in comp.DVs:
                dvName = self.name+'_'+key
                dv = comp.DVs[key]
                if dv.addToPyOpt:
                    optProb.addVar(dvName, 'c', value=dv.value, lower=dv.lower,
                                   upper=dv.upper, scale=dv.scale)



    def addFuelCases(self, cases):
        '''
        Append a list of fuel cases to the weight problem
        '''

        # Check if case is a single entry or a list, otherwise raise Error
        if type(cases) == list:
            pass
        elif type(cases) == object:
            cases = [cases]
        else:
            raise Error('addFuelCases() takes in either a list of or a single fuelcase')
            
        # Add the fuel cases to the problem
        for case in cases:
            self.fuelcases.append(case)

        return

    def _getComponentKeys(self, include=None, exclude=None, 
                          includeType=None, excludeType=None):
        '''
        Get a list of component keys based on inclusion and exclusion

        Parameters
        ----------
        include : list or str
           (Optional) String or list of components to be included in the sum
        exclude : list or str
           (Optional) String or list of components to be excluded in the sum
        includeType : 
           (Optional) String or list of component types to include in the weight keys
        excludeType :
           (Optional) String or list of component types to exclude in the weight keys
        '''

        weightKeys = set(self.components.keys())

        if includeType != None:
            # Specified a list of component types to include
            if type(includeType) == str:
                includeType = [includeType]
            weightKeysTmp = set()
            for key in weightKeys:
                if self.components[key].compType in includeType:
                    weightKeysTmp.add(key)
            weightKeys = weightKeysTmp

        if include != None:
            # Specified a list of compoents to include
            if type(include) == str:
                include = [include]
            include = set(include)
            weightKeys.intersection_update(include)

        if exclude != None:
            # Specified a list of components to exclude
            if type(exclude) == str:
                exclude = [exclude]
            exclude = set(exclude)
            weightKeys.difference_update(exclude)

        if excludeType != None:
            # Specified a list of compoent types to exclude
            if type(excludeType) == str:
                excludeType = [excludeType]
            weightKeysTmp = copy.copy(weightKeys)
            for key in weightKeys:
                if self.components[key].compType in excludeType:
                    weightKeysTmp.remove(key)
            weightKeys = weightKeysTmp

        return weightKeys

    def printComponentData(self):
        '''
        loop over the components and call the owned print function
        '''
        for key in self.components.keys():
            self.components[key].printData()
        # end
        
        return


    def __str__(self):

        self.printComponentData()
        return 'Print statement for WeightAndBalance not implemented'




class FuelCase(object):
    '''
    class to handle individual fuel cases.
    '''
    def __init__(self, name, fuelFraction=.9, reserveFraction = .1):
        '''
        Initialize the fuel case

        Parameters
        ----------
    
        name : str
           A name for the fuel case. 
    
        fuelFraction : float
           Fraction of fuel component volume that contains fuel.

        reserveFraction : float
           Fraction of fuel component volume that contains reserve fuel.
        '''

        self.name=name
        self.fuelFraction = fuelFraction
        self.reserveFraction = reserveFraction
        
        return
