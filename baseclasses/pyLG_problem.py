from __future__ import print_function
'''
pyLG_problem

Holds the information to setup a single LG problem.
Right now this is a relatively simple class that computes the load conditions at 
the wheel for the main landing gear and an effective max-g load for further structural
computation. Nothing in this computation can be a design variable right now because
the beam model setup in TACS has no provision for changing the load as a design variable.
We will assume a fixed aircraft mass and LG characteristics. The output load can change as a
function of the LG geometry if necessary.

Copyright (c) 2019 by Dr. Charles A. Mader 
All rights reserved. Not to be used for commercial purposes.
Revision: 1.0   $Date: 12/02/2019 21:00$


Developers:
-----------
- Dr. Charles A. Mader (CM)

History
-------
	v. 1.0 - Initial Class Creation (CM, 2019)

'''

import sys, numpy, copy
import warnings
#from pygeo import geo_utils

class Error(Exception):
    """
    Format the error message in a box to make it clear this
    was a expliclty raised exception.
    """
    def __init__(self, message):
        msg = '\n+'+'-'*78+'+'+'\n' + '| LGProblem Error: '
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


class LGProblem(object):
    '''
    Landing Gear Problem Object:

    This Landing Gear Problem Object should contain all of the information
    required to estimate the Landing Loads imparted on a wing by the LG during
    Landing and ground operations.

    Parameters
    ----------
    
    name : str
        A name for the configuration
 
    evalFuncs : iteratble object containing strings
        The names of the functions the user wants evaluated for this weight 
        problem
    '''

    def __init__(self, name,  **kwargs):
        """
        Initialize the mission problem
        """
        self.name=name
        #self.units = units.lower()

        # These are the parameters that can be simply set directly in
        # the class.
        paras = set(('aircraftMass', 'tireEff', 'tireDef', 'shockEff', 'shockDef',
                     'weightCondition','loadCaseType'))

        self.g = 9.81 #(m/s)
        self.nMainGear = 2
        # By default everything is None
        for para in paras:
            setattr(self, para, None)

        # Any matching key from kwargs that is in 'paras'
        for key in kwargs:
            if key in paras:
                setattr(self, key, kwargs[key])
                
        # for key in paras:
        #     print(key,getattr(self,key))

        if self.weightCondition.lower()=='mtow':
            self.V_vert=3.048 #m/s or 10 fps
        elif self.weightCondition.lower()=='mlw':
            self.V_vert=1.83  # m/s or 6 fps
        else:
            print('Unrecognized weightCondition:',self.weightCondition)

        self.name+='_'+self.loadCaseType+'_'+self.weightCondition
        
        # Check for function list:
        self.evalFuncs = set()
        if 'evalFuncs' in kwargs:
            self.evalFuncs = set(kwargs['evalFuncs'])
           

    def _computeLGForces(self):
        # These equations are from Aircraft Loading and Structural Layout by Denis Howe

        
        
        f_stat = self.aircraftMass * self.g/self.nMainGear

        g_load =  self.V_vert**2 /(self.nMainGear * self.g * \
                                  (self.tireEff * self.tireDef + self.shockEff * self.shockDef))
        
        # f_dyn =  self.aircraftMass * self.V_vert**2 /\
        #          (4.0 * (self.tireEff * self.tireDef + self.shockEff * self.shockDef))

        f_dyn = (1.0/self.nMainGear)*g_load*self.aircraftMass * self.g


        return f_stat,f_dyn,g_load

    def getLoadFactor(self):
        '''
        return the load factor for this load case
        '''
        f_stat,f_dyn,g_load =self._computeLGForces()
        if self.loadCaseType.lower()=='braking':
            loadFactor = 1.0
        elif self.loadCaseType.lower()=='landing':
            loadFactor = g_load
        else:
             print('Unrecognized loadCaseType:',self.loadCaseType) 


        return loadFactor

    def getLoadCaseArrays(self):

        f_stat,f_dyn,g_load =self._computeLGForces()
        
        if self.loadCaseType.lower()=='braking':
            nCondition = 2
            if self.weightCondition.lower()=='mlw':
                fVert = numpy.zeros(nCondition)
                fVert[0] = 0.6 * f_stat
                fVert[1] = 0.6 * f_stat

                fDrag = numpy.zeros(nCondition)
                fDrag[0] = 0.48 * f_stat
                fDrag[1] = -0.33 * f_stat

                fSide = numpy.zeros(nCondition)

            elif self.weightCondition.lower()=='mtow':
                fVert = numpy.zeros(nCondition)
                fVert[0] = 0.5 * f_stat
                fVert[1] = 0.5 * f_stat

                fDrag = numpy.zeros(nCondition)
                fDrag[0] = 0.4 * f_stat
                fDrag[1] = -0.275 * f_stat

                fSide = numpy.zeros(nCondition)

            else:
                print('Unrecognized weightCondition:',self.weightCondition)
                
        elif self.loadCaseType.lower()=='landing':
            nCondition = 5
            fVert = numpy.zeros(nCondition)
            fVert[0] = f_dyn
            fVert[1] = 0.75 * f_dyn
            fVert[2] = 0.75 * f_dyn
            fVert[3] = 0.5 * f_dyn
            fVert[4] = 0.5 * f_dyn
            
            fDrag = numpy.zeros(nCondition)
            fDrag[0] = 0.25 * f_dyn
            fDrag[1] = 0.4 * f_dyn
            fDrag[2] = 0.4 * f_dyn
            fDrag[3] = 0.0
            fDrag[4] = 0.0
                                            
            # sign convention here is that negative is inboard facing
            fSide = numpy.zeros(nCondition)
            fSide[0] = 0
            fSide[1] = -0.25 * f_dyn
            fSide[2] =  0.25 * f_dyn
            fSide[3] = -0.4 * f_dyn
            fSide[4] =  0.3 * f_dyn
            
        else:
             print('Unrecognized loadCaseType:',self.loadCaseType)




        return fVert,fDrag,fSide
             
