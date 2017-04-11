from __future__ import print_function
'''
pyMission_solver

Holds the Python Mission Analysis Base Classes.

Copyright (c) 2012 by Dr. Charles A. Mader
All rights reserved. Not to be used for commercial purposes.
Revision: 1.0   $Date: 01/06/2012 15:00$


Developers:
-----------
- Dr. Charles A. Mader (CAM)

History
-------
    v. 1.0    - Initial Class Creation (CAM, 2012)
'''

__version__ = '$Revision: $'

'''
ToDo:
    - 
'''

# =============================================================================
# Standard Python modules
# =============================================================================
import os, sys

# =============================================================================
# AeroSolver Class
# =============================================================================
class MissionSolver(object):
    
    '''
    Abstract Class for Structural Solver Object
    '''
    
    def __init__(self, name, category=None, def_options=None, informs=None, *args, **kwargs):
        
        '''
        StructSolver Class Initialization
        
        Documentation last updated:  
        '''
        
        # 
        self.name = name
        self.category = category
        self.options = {}
        self.options['defaults'] = def_options
        self.informs = informs
        
        # Initialize Options
        def_keys = def_options.keys()
        for key in def_keys:
            self.options[key] = def_options[key]
        #end
        koptions = kwargs.pop('options',{})
        kopt_keys = koptions.keys()
        for key in kopt_keys:
            self.setOption(key,koptions[key])
        #end
        
        
    def __solve__(self, *args, **kwargs):
        
        '''
        Run Analyzer (Analyzer Specific Routine)
        
        Documentation last updated: 
        '''
        
        pass
        
        
    def __call__(self,  *args, **kwargs):
        
        '''
        Run Analyzer (Calling Routine)
        
        Documentation last updated: 
        '''
        
        
        # Checks
        
        # Solve Analysis Problem
        fail = self.__solve__(*args, **kwargs)
        
        return fail
        
    def setOption(self, name, value):
        
        '''
        Set Optimizer Option Value (Calling Routine)
        
        Keyword arguments:
        -----------------
        name -> STRING: Option Name
        value -> SCALAR or BOOLEAN: Option Value
        
        Documentation last updated:  May. 21, 2008 - Ruben E. Perez
        '''
        
        # 
        def_options = self.options['defaults']
        if def_options.has_key(name):
            if (type(value) == def_options[name][0]):
                self.options[name] = [type(value),value]
            else:
                raise IOError('Incorrect ' + repr(name) + ' value type', type(value))
            #end
        else:
            print('%s is not a valid option name'%(name))
            raise IOError('Not a valid option name')
        #end
               
        
    def getOption(self, name):
        
        '''
        Get Optimizer Option Value (Calling Routine)
        
        Keyword arguments:
        -----------------
        name -> STRING: Option Name
        
        Documentation last updated:  May. 21, 2008 - Ruben E. Perez
        '''
        
        # 
        def_options = self.options['defaults']
        if def_options.has_key(name):
            return self.options[name][1]
        else:    
            raise IOError(repr(name) + ' is not a valid option name')
        #end
        
        # 
        


#==============================================================================
# Mission Solver Instantiation Test
#==============================================================================
if __name__ == '__main__':
    
    print('Testing MissionSolver instantiation...')
    
    # Test Optimizer
    azr = MissionSolver('Test')
    dir(azr)

