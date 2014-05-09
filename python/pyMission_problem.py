'''
pyMission_problem

Holds the Segment, Profile and Problem classes for the mission solvers.

Copyright (c) 2014 by Dr. Charles A. Mader and Dr. Gaetan Kenway
All rights reserved. Not to be used for commercial purposes.
Revision: 1.0   $Date: 10/03/2014 21:00$


Developers:
-----------
- Dr. Charles A. Mader (CM)
- Dr. Gaetan Kenway (GK)

History
-------
	v. 1.0 - Initial Class Creation (CM,GK, 2014)

'''
import numpy,copy
import warnings
from ICAOAtmosphere import ICAOAtmosphere 

class Error(Exception):
    """
    Format the error message in a box to make it clear this
    was a expliclty raised exception.
    """
    def __init__(self, message):
        msg = '\n+'+'-'*78+'+'+'\n' + '| MissionProblem Error: '
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

class MissionProblem(object):
    '''
    Mission Problem Object:

    This Mission Problem Object should contain all of the information required
    to analyze a single mission.

    Parameters
    ----------
    
    name : str
        A name for the mission
    
    evalFuncs : iteratble object containing strings
        The names of the functions the user wants evaluated for this mission 
        problem
    
    '''
    def __init__(self,name, **kwargs):
        """
        Initialize the mission problem
        """
        self.name=name
        
        self.profiles = []
        self.missionSegments = []
        self.funcNames = {}

        # Check for function list:
        self.evalFuncs = set()
        if 'evalFuncs' in kwargs:
            self.evalFuncs = set(kwargs['evalFuncs'])
            
        self.segCounter = 1

    def addProfile(self,profile):
        '''
        append a mission profile to the list. update the internal
        segment indices to correspond
        '''
        
        for seg in profile.segments:
            self.segCounter+=1
            self.missionSegments.extend([seg])
        # end
        
        self.profiles.append(profile)

        
        return
    
    def getNSeg(self):
        '''
        return the number of segments in the mission
        '''
        return self.segCounter-1

    def getSegments(self):
        '''
        return a list of the segments in the mission in order
        '''
        return self.missionSegments

class MissionProfile(object):
    '''
    Mission Profile Object:
    
    This Mission Profile Object contain an ordered set of segments that 
    make up a single subsection of a mission. Start and end points of each
    segment in the profile are required to be continuous.

    '''
    
    def __init__(self,name):
        '''
        Initialize the mission profile
        '''
        self.name = name

        self.segments= []
        
        self.firstSegSet=False

    def addSegments(self,segments):
        '''
        Take in a list of segments and append it to the the current list.
        Check for consistency while we are at it.
        '''
        self.segments.extend(segments)
        
        self._checkStateConsistancy()

    def _checkStateConsistancy(self):
        # loop over the segments.
        # if it is a fuel fraction segment, skip
        # otherwise check if its initial parameters match the final parameters
        # from the previous segment, if not raise an error
        # if they don't exist, copy.
        for i in range(len(self.segments)):
            seg = self.segments[i]
            if getattr(seg, 'fuelFraction') is not None:
                # Segment is a fuel fraction segment nothing needs to be done
                #print getattr(seg, 'phase')
                pass
            else:
                if not self.firstSegSet:
                    setattr(seg,'isFirstStateSeg',True)
                    self.firstSegSet=True
                # end
                if seg.isFirstStateSeg:
                    # this is the first segment. 
                    # Need to have at least the start alt and V or M
                    if (getattr(seg,'initAlt') is None):
                        raise Error('%s: Initial altitude must be\
                                     specified for the first non fuel fraction\
                                     segment in the profile'%(self.name))
                    # end

                    if (getattr(seg,'initMach') is None) and\
                            (getattr(seg,'initCAS') is None) and\
                              (getattr(seg,'initTAS') is None):
                        raise Error('%s: One of initCAS,initTAS or initMach needs to be\
                                     specified for the first non fuelfraction\
                                     segment in the profile'%(self.name))
                    # end
                    
                    # Synchronize
                    #seg._printSegStates()
                    seg._syncMachVAndAlt(endPoint='start')
                    # calculate final
                    #seg._printSegStates()
                    seg._propagateStateValues()
                    # synchronize the states at the end of the segment
                    #seg._printSegStates()
                    seg._syncMachVAndAlt(endPoint='end')
                    
                else:
                    prevSeg = self.segments[i-1]
                    refAlt = getattr(prevSeg,'finalAlt')
                    refCAS = getattr(prevSeg,'finalCAS')
                    refTAS = getattr(prevSeg,'finalTAS')
                    refMach = getattr(prevSeg,'finalMach')
                    TASi = getattr(seg,'initTAS')
                    CASi = getattr(seg,'initCAS')
                    Mi = getattr(seg,'initMach')
                    Alti = getattr(seg,'initAlt')
                    if not CASi is None:
                        if not CASi==refCAS:
                             raise Error('%s: Specified initCAS \
                                          inconsistent with\
                                          previous finalCAS: %f, %f \
                                          '%(seg.phase,CASi,refCAS))
                        # end
                    else:
                        setattr(seg,'initCAS',refCAS)
                    # end
                    if not TASi is None:
                        if not TASi==refTAS:
                             raise Error('%s: Specified initTAS \
                                          inconsistent with\
                                          previous finalTAS: %f, %f \
                                          '%(seg.phase,TASi,refTAS))
                        # end
                    else:
                        setattr(seg,'initTAS',refTAS)
                    # end
                    if not Alti is None:
                        if not Alti==refAlt:
                             raise Error('%s: Specified initAlt \
                                         inconsistent with\
                                         previous finalAlt'%(seg.phase))
                        # end
                    else:
                        setattr(seg,'initAlt',refAlt)
                    # end
                    if not Mi is None:
                        if not Mi==refMach:
                             raise Error('%s: Specified initMach \
                                          inconsistent with\
                                          previous finalMach'%(seg.phase))
                        # end
                    else:
                        setattr(seg,'initMach',refMach)
                    # end
                        
                    # syncronize the states at the start of the segment
                    #seg._printSegStates()
                    seg._syncMachVAndAlt(endPoint='start')

                    # calculate final
                    #seg._printSegStates()
                    seg._propagateStateValues()
                    #seg._printSegStates()

                    # synchronize the states at the end of the segment
                    seg._syncMachVAndAlt(endPoint='end')
                    #seg._printSegStates()
                # end
            # end
        # end
                    

class MissionSegment(object):
    '''
    Mission Segment Object:
    
    This is the basic building block of the mission solver.

    Parameters:
    -----------

    phase : str
        Segment type selector valid options include

    R : float
        The gas constant. By defalut we use air. R=287.05

    englishUnits : bool
        Flag to use all English units: pounds, feet, Rankine etc. 
    '''
    def __init__(self, phase , **kwargs):

        # have to have a phase type
        self.phase = phase

        # Check if we have english units:
        self.englishUnits = False
        if 'englishUnits' in kwargs:
            self.englishUnits = kwargs['englishUnits']
           
        # create an internal instance of the atmosphere to use
        self.atm = ICAOAtmosphere(englishUnits=self.englishUnits)

             # Check if 'R' is given....if not we assume air
        if 'R' in kwargs:
            self.R = kwargs['R']
        else:
            if self.englishUnits:
                self.R = 1716.493 
            else:
                self.R = 287.870

        # Check if 'gamma' is given....if not we assume air
        if 'gamma' in kwargs:
            self.gamma = kwargs['gamma']
        else:
            self.gamma = 1.4

        # These are the parameters that can be simply set directly in
        # the class. 
        
        paras =set(('initMach','initAlt','initCAS','initTAS',
                    'finalMach','finalAlt','finalCAS',
                    'finalTAS','fuelFraction','segTime',
                    'rangeFraction','engType'))
        
        # By default everything is None
        for para in paras:
            setattr(self, para, None)

        # Any matching key from kwargs that is in 'paras'
        for key in kwargs:
            if key in paras:
                setattr(self, key, kwargs[key])

        # identify the possible design variables based on what parameters
        # have been set 
        varFuncs =['initMach','initAlt','initTAS','initCAS',
                   'finalMach','finalAlt','finalCAS','finalTAS']

        self.possibleDVs = set()
        for var in varFuncs:
            if getattr(self, var) is not None:
                self.possibleDVs.add(var)
                
        # Storage of DVs
        self.DVs = {}
        self.DVNames = {}

        self.isFirstStateSeg=False
        
        return
        
    def _syncMachVAndAlt(self,endPoint='start'):
        # get speed of sound at initial point
        if endPoint.lower()=='start':
            CAS = getattr(self,'initCAS') 
            TAS = getattr(self,'initTAS') 
            M = getattr(self,'initMach')
            h = getattr(self,'initAlt')
            CASTag = 'initCAS'
            TASTag = 'initTAS'
            machTag = 'initMach'
            altTag = 'initAlt'
        elif endPoint.lower()=='end':
            TAS = getattr(self,'finalTAS') 
            CAS = getattr(self,'finalCAS') 
            M = getattr(self,'finalMach')
            h = getattr(self,'finalAlt')
            CASTag = 'finalCAS'
            TASTag = 'finalTAS'
            machTag = 'finalMach'
            altTag = 'finalAlt'
        else:
            # invalid endpoint
            raise Error('%s: _syncMachAndV, invalid endPoint:\
                         %s'%(self.phase,endPoint))
        # end
        if h is None:
            # initial altitude is missing calculate from M and V
            h = self._solveMachCASIntercept(CAS, M)
            setattr(self,altTag,h)
        # end
        a = self._getSoundSpeed(h)
        P,T,Rho = self._getPTRho(h)
       
        if not (CAS is None and TAS is None):
            if CAS is None:
                CAS = self._TAS2CAS(TAS,h)
                setattr(self,CASTag,CAS)
            elif TAS is None:
                TAS= self._CAS2TAS(CAS,h)
                setattr(self,TASTag,TAS)
            # end
            MCalc = TAS/a
            if not M is None:
                if not abs(MCalc-M)<1e-11:
                    raise Error('%s: _syncMachAndV, Specified V \
                                 inconsistent with specified M: \
                                 %f %f %s'%(self.phase, M, MCalc, 
                                            endPoint))
                # end
            else:
                setattr(self,machTag,MCalc)
            # end
        else:
            TAS = M*a
            CAS = self._TAS2CAS(TAS,h)
            setattr(self,TASTag,TAS)
            setattr(self,CASTag,CAS)
        # end

    def _propagateStateValues(self):
        '''
        Set the final V,M,h base on initial values and segType.
        '''
        if self.phase.lower() == 'acceleratedcruise' or \
               self.phase.lower() == 'deceleratedcruise' :
            setattr(self,'finalAlt',getattr(self,'initAlt'))
        elif self.phase.lower() == 'cvelclimb':
            # we require that Vi,hi and Mf are specified
            # calculate hf from Vi and Mf
            setattr(self,'finalCAS',getattr(self,'initCAS'))
            
            #solve for h given M and V
            CAS = getattr(self,'finalCAS')
            M = getattr(self,'finalMach')
            finalAlt = self._solveMachCASIntercept(CAS, M)
            TAS = self._CAS2TAS(CAS,finalAlt)
            setattr(self,'finalAlt',finalAlt)
            setattr(self,'finalTAS',TAS)
        elif self.phase.lower() == 'cmachclimb':
            # we require that Mi,hg and Vi are specified
            # calculate hi from Vi and Mf
            CAS = getattr(self,'initCAS')
            M = getattr(self,'initMach')
            setattr(self,'finalMach',M)
            initAlt = self._solveMachCASIntercept(CAS, M)
            setattr(self,'initAlt',initAlt)
            TAS = self._CAS2TAS(CAS,initAlt)
            setattr(self,'initTAS',TAS)
        elif self.phase.lower() == 'cruise' or \
                self.phase.lower() == 'loiter':
            # take everything from init and copy to final
            CAS = getattr(self,'initCAS')
            TAS = getattr(self,'initTAS')
            M = getattr(self,'initMach')
            Alt = getattr(self,'initAlt')
            setattr(self,'finalCAS',CAS)
            setattr(self,'finalTAS',TAS)
            setattr(self,'finalMach',M)
            setattr(self,'finalAlt',Alt)
        elif self.phase.lower() == 'cmachdescent':
            # use final CAS and init Mach (copied to final Mach) 
            # to calculate the intersection altitude of the M and
            # CAS values
            CAS = getattr(self,'finalCAS')
            M = getattr(self,'initMach')
            setattr(self,'finalMach',M)
            finalAlt = self._solveMachCASIntercept(CAS, M)
            setattr(self,'finalAlt',finalAlt)
            TAS = self._CAS2TAS(CAS,finalAlt)
            setattr(self,'finalTAS',TAS)
        elif self.phase.lower() == 'cveldescent':
            # copy CAS directly, then compute TAS and M from CAS
            # and h
            CAS = getattr(self,'initCAS')
            setattr(self,'finalCAS',CAS)
            finalAlt = getattr(self,'finalAlt')
            TAS = self._CAS2TAS(CAS,finalAlt)
            a = self._getSoundSpeed(finalAlt)
            M = TAS/a
            setattr(self,'finalTAS',TAS)
            setattr(self,'finalMach',M)
        # end

    def _getSoundSpeed(self,alt):
        '''
        compute the speed of sound at this altitude
        '''
        # evaluate the atmosphere model
        P,T = self.atm(alt)      
        a = numpy.sqrt(self.gamma*self.R*T)

        return copy.copy(a)

    def _getPTRho(self,alt):
        '''
        compute the pressure at this altitude
        '''
        # evaluate the atmosphere model
        P,T = self.atm(alt) 
        rho = P/(self.R*T)

        return P,T,rho
 
    def _printSegStates(self):
        '''
        Print the initial and final states for this segment
        '''
        print '------------'
        print 'Segment : %s'%(self.phase)
        print 'Init: CAS: %s, TAS: %s, M: %s, h: %s'%(self.initCAS, self.initTAS, self.initMach,
                                           self.initAlt)
        print 'Final: CAS: %s, TAS: %s, M: %s, h: %s'%(self.finalCAS, self.finalTAS, self.finalMach,
                                           self.finalAlt)
        print '------------'

    def _solveMachCASIntercept(self, CAS, mach, initAlt=3048.):
        # TAS: True Air speed
        # CAS: Calibrated air speed
        
        # Simple Newton's method to solve for the altitude at which
        # TAS=mach 

        alt = initAlt
        dAlt = 1e+1

        res = 1.0
        while abs(res) > 1e-12:
            a = self._getSoundSpeed(alt)
            TAS = self._CAS2TAS(CAS,alt)
            M = TAS/a
            res = M - mach
            #print 'At %.2fm, %.1fCAS = M%.3f' % (alt, CAS, M)
            a = self._getSoundSpeed(alt+dAlt)
            TAS = self._CAS2TAS(CAS,alt+dAlt)
            M2 = TAS/a
            res2 = M2 - mach
            df = (res2 - res) / dAlt
            if abs(res/df) <1000.:
                alt -=  res/df
            else:
                alt -= (1.0/2.0)* res/df
            # end

        return alt

    def _TAS2CAS(self,TAS,h):
        # get sea level properties
        a0 = self._getSoundSpeed(0)                   
        P0,T0,rho0 = self._getPTRho(0)

        # get the properties at the current altitude
        a = self._getSoundSpeed(h)
        P,T,rho = self._getPTRho(h)

        # compute the ratios at for the static atmospheric states
        PRatio = P/P0
        TRatio = T/T0
        RhoRatio = rho/rho0

        # Convert the TAS to EAS
        EAS = TAS * numpy.sqrt(RhoRatio)

        # Evaluate the current M based on TAS
        M = TAS/a

        # Evaluate the Calibrated air speed, CAS
        term1 = (1.0/8.0)*(1-PRatio)*M**2
        term2 = (3.0/640.0)*(1-10*PRatio+9*PRatio**2)*M**4
        ECTerm = 1+term1+term2
        CAS = EAS * ECTerm

        return CAS

    def _CAS2TAS(self,CAS,h):
        # TAS: True air speed

        a0 = self._getSoundSpeed(0)                   
        P0,T0,rho0 = self._getPTRho(0)

        a = self._getSoundSpeed(h)
        P,T,rho = self._getPTRho(h)

        PRatio = P/P0
        TRatio = T/T0
        RhoRatio = rho/rho0

        # Source: http://williams.best.vwh.net/avform.htm#Intro
        # Differential pressure: Units of CAS and a0 must be consistent
        DP = P0 * ((1 + 0.2*(CAS/a0)**2)**(7./2.) - 1)   # impact pressure                                                            
        
        M = numpy.sqrt(5 * ((DP/P + 1)**(2./7.) - 1))

        if M > 1:
            raise Error('_CAS2TAS: The current mission class is\
                         limited to subsonic missions: %f %f'%(M,CAS))
            # M_diff = 1.0
            # while M_diff > 1e-4:
            #     # computing Mach number in a supersonic compressible flow by using the
            #     # Rayleigh Supersonic Pitot equation using parameters for air
            #     M_new = 0.88128485 * numpy.sqrt((DP/P + 1) * (1 - 1/(7*M**2))**2.5)
            #     M_diff = abs(M_new - M)
            #     M = M_new

        TAS = M * a

        return TAS

    def setMissionData(self, module, segTypeDict, engTypeDict, idx, nIntervals,segIdx):
        '''
        set the data for the current segment in the fortran module
        '''
        h1 = getattr(self,'initAlt')
        if h1 == None:
            h1 = 0.0
        h2 = getattr(self,'finalAlt')
        if h2 == None:
            h2 = 0.0
        M1 = getattr(self,'initMach')
        if M1 == None:
            M1 = 0.0
        M2 = getattr(self,'finalMach')
        if M2 == None:
            M2 = 0.0
        V1 = getattr(self,'initCAS')
        if V1 == None:
            V1 = 0.0
        V2 = getattr(self,'finalCAS')
        if V2 == None:
            V2 = 0.0
        deltaTime = getattr(self,'segTime')
        if deltaTime == None:
            deltaTime = 0.0
        # end
        fuelFraction = getattr(self,'fuelFraction')
        if fuelFraction == None:
            fuelFraction = 0.0
        # end
            
        rangeFraction = getattr(self,'rangeFraction')
        if rangeFraction == None:
            rangeFraction = 1.0
        # end

        segTypeID = segTypeDict[getattr(self,'phase')]

        # Get the engine type and ensure the engine type is defined in engTypeDict
        if self.engType not in engTypeDict and self.engType != None:
            raise Error('engType %s defined in segment %s not defined in engTypeDict'%
                        (self.engType, self.phase))
        if self.engType == None:
            self.engType = 'None'
        engTypeID = engTypeDict[getattr(self,'engType')]
       
        #print 'mission segment input',idx,segIdx, h1, h2, M1, M2, V1, V2,deltaTime,fuelFraction,segType,nIntervals
        module.setmissionsegmentdata(idx,segIdx, h1, h2, M1, M2, V1, V2,
                                     deltaTime,fuelFraction,rangeFraction,
                                     segTypeID,engTypeID,nIntervals)


    def addDV(self, key, value=None, lower=None, upper=None, scale=1.0,
              name=None, offset=0.0):
        """
        Add one of the class attributes as a mission design
        variable. Typical variables are mach or velocity and altitude
        An error will be given if the requested DV is not allowed to
        be added .
      

        Parameters
        ----------
        key : str
            Name of variable to add. See above for possible ones

        value : float. Default is None
            Initial value for variable. If not given, current value
            of the attribute will be used.

        lower : float. Default is None
            Optimization lower bound. Default is unbonded.

        upper : float. Default is None
            Optimization upper bound. Default is unbounded.

        scale : float. Default is 1.0
            Set scaling parameter for the optimization to use.

        name : str. Default is None
            Overwrite the name of this variable. This is typically
            only used when the user wishes to have multiple
            aeroProblems to explictly use the same design variable.

        offset : float. Default is 0.0

            Specify a specific (constant!) offset of the value used,
            as compared to the actual design variable. This is most
            often used when a single aerodynamic variable is used to
            change multiple aeroProblems. For example. if you have
            three aeroProblems for a multiPoint analysis, and you want
            mach numbers of 0.84, 0.85 and 0.86, but want want only to
            change the center one, and have the other two slave, we
            would do this::

              >>> ap1.addDV('mach',...,name='centerMach', offet=-0.01)
              >>> ap2.addDV('mach',...,name='centerMach', offet= 0.00)
              >>> ap3.addDV('mach',...,name='centerMach', offet=+0.01)

            The result is a single design variable driving three
            different mach numbers. 
            
        Examples
        --------
        >>> # Add initMach variable with typical bounds
        >>> seg.addDV('initMach', value=0.75, lower=0.0, upper=1.0, scale=1.0)
        """

        # First check if we are allowed to add the DV:
        if key not in self.possibleDVs:
            raise Error('The DV \'%s\' could not be added. Potential DVs MUST\
            be specified when the missionSegment class is created. \
            For example, if you want initMach as a design variable \
            (...,alpha=value, ...) must\
            be given. The list of possible DVs are: %s.'% (
                            key, repr(self.possibleDVs)))

        if name is None:
            dvName = key + '_%s'% self.phase
        else:
            dvName = name

        if value is None:
            value = getattr(self, key)
         
        self.DVs[dvName] = segmentDV(key, value, lower, upper, scale, offset)
        self.DVNames[key] = dvName

class segmentDV(object):
    """
    A container storing information regarding an 'aerodynamic' variable.
    """
    
    def __init__(self, key, value, lower, upper, scale, offset):
        self.key = key
        self.value = value
        self.lower = lower
        self.upper = upper
        self.scale = scale
        self.offset = offset

