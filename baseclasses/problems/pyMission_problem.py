"""
pyMission_problem

Holds the Segment, Profile and Problem classes for the mission solvers.
"""

import sys
import numpy
import copy

from .ICAOAtmosphere import ICAOAtmosphere
from .FluidProperties import FluidProperties
from ..utils import Error


class MissionProblem:
    """
    Mission Problem Object:

    This mission problem object should contain all of the information required
    to analyze a single mission. A mission problem is made of profiles. All
    profiles in a given mission problem must use consistent units.

    Parameters
    ----------

    name : str
        A name for the mission

    evalFuncs : iteratble object containing strings
        The names of the functions the user wants evaluated for this mission
        problem
    """

    def __init__(self, name, **kwargs):
        """
        Initialize the mission problem
        """
        self.name = name

        self.missionProfiles = []
        self.missionSegments = []
        self.funcNames = {}
        self.currentDVs = {}
        self.solveFailed = False

        # Check for function list:
        self.evalFuncs = set()
        if "evalFuncs" in kwargs:
            self.evalFuncs = set(kwargs["evalFuncs"])

        self.segCounter = 1
        self.solutionCounter = 0

        self.states = None

    def addProfile(self, profiles):
        """
        Append a mission profile to the list. update the internal
        segment indices to correspond
        """

        # Check if profile is of type MissionProfile or list, otherwise raise Error
        if type(profiles) == MissionProfile:
            profiles = [profiles]
        elif type(profiles) == list:
            pass
        else:
            raise Error("addProfile() takes in either a list of or a single MissionProfile")

        # Add the profiles to missionProfiles and segments to missionSegments
        for prof in profiles:
            # Check for consistent units
            if len(self.missionProfiles) == 0:
                self.englishUnits = prof.englishUnits
            elif prof.englishUnits != self.englishUnits:
                raise Error("Units are not consistent across all profiles.")

            self.missionProfiles.append(prof)
            for seg in prof.segments:
                self.segCounter += 1
                self.missionSegments.extend([seg])

            for dvName in prof.dvList:
                self.currentDVs[dvName] = prof.dvList[dvName].value
            # end

        return

    def addVariablesPyOpt(self, pyOptProb):
        """
        Add the current set of variables to the optProb object.

        Parameters
        ----------
        optProb : pyOpt_optimization class
            Optimization problem definition to which variables are added
        """

        for profile in self.missionProfiles:
            for dvName in profile.dvList:
                dv = profile.dvList[dvName]
                pyOptProb.addVar(dvName, "c", scale=dv.scale, value=dv.value, lower=dv.lower, upper=dv.upper)
                self.currentDVs[dvName] = dv.value

        return pyOptProb

    def checkForProfileDVs(self):
        """
        Check if design variables have been added to this mission.
        """
        for profile in self.missionProfiles:
            if profile.dvList:
                return True

        return False

    def setDesignVars(self, missionDVs):
        """
        Pass the DVs to each of the profiles and have the profiles set the DVs

        Parameters
        ----------
        missionDVs : dict
            Dictionary of variables which may or may not contain the
            design variable names this object needs
        """
        # Update the set of design variable values being used
        for dv in self.currentDVs:
            if dv in missionDVs:
                self.currentDVs[dv] = missionDVs[dv]

        for profile in self.missionProfiles:
            profile.setDesignVars(missionDVs)

    def evalDVSens(self, stepSize=1e-20):
        """
        Evaluate the sensitivity of each of the 4 segment parameters
        (Mach, Alt) with respect to the design variables
        """

        dvSens = {}

        # Perturbate each of the DV with complex step
        for dvName in self.currentDVs:
            tmpDV = {dvName: self.currentDVs[dvName] + stepSize * 1j}
            profSens = []
            for profile in self.missionProfiles:
                profile.setDesignVars(tmpDV)
                profSens.extend(profile.getSegmentParameters())
                profile.setDesignVars(self.currentDVs)

            # Replace the NaNs with 0
            profSens = numpy.array(profSens)
            indNaNs = numpy.isnan(profSens)
            profSens[indNaNs] = 0.0

            profSens = profSens.imag / stepSize
            dvSens[dvName] = profSens

        return dvSens

    def getAltitudeCons(self, CAS, mach, alt):
        """
        Solve for the altitude at which CAS=mach
        """

        if type(CAS) == str and CAS in self.currentDVs:
            CAS = self.currentDVs[CAS]
        if type(mach) == str and mach in self.currentDVs:
            mach = self.currentDVs[mach]
        if type(alt) == str and alt in self.currentDVs:
            alt = self.currentDVs[alt]

        seg = self.missionSegments[0]
        altIntercept = seg._solveMachCASIntercept(CAS, mach)

        return alt - altIntercept

    def getAltitudeConsSens(self, CAS, mach, alt, stepSize=1e-20):
        """
        Solve for the altitude sensitivity at which CAS=mach
        """

        seg = self.missionSegments[0]
        altSens = {}

        if type(CAS) == str and CAS in self.currentDVs:
            CASVal = self.currentDVs[CAS]
            dAltdCAS = seg._solveMachCASIntercept(CASVal + stepSize * 1j, mach)
            altSens[CAS] = -dAltdCAS.imag / stepSize

        if type(mach) == str and mach in self.currentDVs:
            machVal = self.currentDVs[mach]
            dAltdMach = seg._solveMachCASIntercept(CAS, machVal + stepSize * 1j)
            altSens[mach] = -dAltdMach.imag / stepSize

        if type(alt) == str and alt in self.currentDVs:
            altSens[alt] = 1.0

        return altSens

    def getNSeg(self):
        """
        return the number of segments in the mission
        """

        return self.segCounter - 1

    def getSegments(self):
        """
        return a list of the segments in the mission in order
        """

        return self.missionSegments

    def setUnits(self, module):
        """
        Set the units and the gravity constant for this mission.
        """
        module.mission_parameters.englishUnits = self.englishUnits
        if self.englishUnits:
            module.mission_parameters.g = 32.2  # ft/s/s
        else:
            module.mission_parameters.g = 9.80665  # ft/s/s

    def __str__(self):
        """
        Return a string representation of the profiles within this mission
        """

        segCount = 1
        string = "MISSION PROBLEM: %s \n" % self.name
        for i in range(len(self.missionProfiles)):
            # profTag = 'P%02d'%i
            string += self.missionProfiles[i].__str__(segCount)
            segCount += len(self.missionProfiles[i].segments)

        return string


class MissionProfile:
    """
    Mission Profile Object:

    This Mission Profile Object contain an ordered set of segments that
    make up a single subsection of a mission. Start and end points of each
    segment in the profile are required to be continuous.

    """

    def __init__(self, name, englishUnits=False):
        """
        Initialize the mission profile
        """

        self.name = name
        self.englishUnits = englishUnits

        self.segments = []
        self.dvList = {}

        self.firstSegSet = False

    def addSegments(self, segments):
        """
        Take in a list of segments and append it to the the current list.
        Check for consistency while we are at it.
        """

        # Check if profile is of type MissionProfile or list, otherwise raise Error
        if type(segments) == MissionSegment:
            segments = [segments]
        elif type(segments) == list:
            pass
        else:
            raise Error("addSegments() takes in either a list or a single MissionSegment")

        nSeg_Before = len(self.segments)
        self.segments.extend(segments)

        # Loop over each *new* segment in search for DVs
        for i in range(len(segments)):
            seg = segments[i]
            seg.setUnitSystem(self.englishUnits)
            seg.setDefaults(self.englishUnits)
            segID = i + nSeg_Before

            # Loop over the DVs in the segment, if any
            for dvName in seg.dvList:
                dvObj = seg.dvList[dvName]
                if dvObj.userDef:
                    # Variable name should remain unchanged
                    if dvName in self.dvList:
                        raise Error(
                            "User-defined design variable name "
                            + f"{dvName} has already been added"
                            + " to this profile."
                        )
                    dvNameGlobal = dvName
                else:
                    # Prepend profile name and segment ID
                    dvNameGlobal = f"{self.name}_seg{segID}_{dvName}"
                # Save a reference of the DV object and set its segment ID
                self.dvList[dvNameGlobal] = seg.dvList[dvName]
                self.dvList[dvNameGlobal].setSegmentID(segID)

            # Propagate the segment inputs from one to next
            # except don't propagate from last (i=-1) to first (i=0) segment
            if i > 0 and seg.propagateInputs:
                for var in segments[i - 1].segInputs:
                    if "final" in var:
                        newVar = var.replace("final", "init")
                        seg.segInputs.add(newVar)
            seg.determineInputs()

        self._checkStateConsistancy()

    def setDesignVars(self, missionDVs):
        """
        Set the variables for this mission profile

        Parameters
        ----------
        missionDVs : dict
            Dictionary of variables which may or may not contain the
            design variable names this object needs
        """

        for dvName in missionDVs:
            # Only concern about the DVs that are in this profile
            if dvName in self.dvList:
                dvObj = self.dvList[dvName]
                dvVal = missionDVs[dvName]
                dvType = dvObj.type  # String: 'Mach', 'Alt', 'TAS', 'CAS'
                segID = dvObj.segID
                isInitVal = dvObj.isInitVal
                # Update the segment for which the DV object belongs to
                seg = self.segments[segID]
                updatePrev, updateNext = seg.setParameters(dvVal, dvType, isInitVal)

                # Update any PREVIOUS segments that depends on this DV
                while updatePrev and segID > 0:
                    segID -= 1
                    seg = self.segments[segID]
                    updatePrev, tmp = seg.setParameters(dvVal, dvType, isInitVal=False)

                # Update any FOLLOWING segments that depends on this DV
                segID = dvObj.segID
                while updateNext and segID < len(self.segments) - 1:
                    segID += 1
                    seg = self.segments[segID]
                    tmp, updateNext = seg.setParameters(dvVal, dvType, isInitVal=True)

        # After setting all the design variables, update the remaining segment states
        for seg in self.segments:
            seg.propagateParameters()

        self._checkStateConsistancy()

    def getSegmentParameters(self):
        """
        Get the 4 segment parameters from each of the segment it owns
        Order is [M1, h1, M2, h2]
        """

        nSeg = len(self.segments)

        segParameters = numpy.zeros(4 * nSeg, dtype="D")
        for i in range(nSeg):
            seg = self.segments[i]
            segParameters[4 * i] = seg.initMach
            segParameters[4 * i + 1] = seg.initAlt
            segParameters[4 * i + 2] = seg.finalMach
            segParameters[4 * i + 3] = seg.finalAlt
            # segParameters[8*i  ] = seg.initMach
            # segParameters[8*i+1] = seg.initAlt
            # segParameters[8*i+2] = seg.initCAS
            # segParameters[8*i+3] = seg.initTAS
            # segParameters[8*i+4] = seg.finalMach
            # segParameters[8*i+5] = seg.finalAlt
            # segParameters[8*i+6] = seg.finalCAS
            # segParameters[8*i+7] = seg.finalTAS

        return segParameters

    def _checkStateConsistancy(self):
        # loop over the segments.
        # if it is a fuel fraction segment, skip
        # otherwise check if its initial parameters match the final parameters
        # from the previous segment, if not raise an error
        # if they don't exist, copy.
        for i in range(len(self.segments)):
            seg = self.segments[i]
            if seg.propagateInputs is False:
                # Segment is a fuel fraction segment nothing needs to be done
                pass
            else:
                if not self.firstSegSet:
                    seg.isFirstStateSeg = True
                    self.firstSegSet = True
                # end
                if seg.isFirstStateSeg:
                    # this is the first segment.
                    # Need to have at least the start alt and V or M
                    if seg.initAlt is None:
                        raise Error(
                            "%s: Initial altitude must be\
                                     specified for the first non fuel fraction\
                                     segment in the profile"
                            % (self.name)
                        )
                    # end

                    if (seg.initMach is None) and (seg.initCAS is None) and (seg.initTAS is None):
                        raise Error(
                            "%s: One of initCAS,initTAS or initMach needs to be\
                                     specified for the first non fuelfraction\
                                     segment in the profile"
                            % (self.name)
                        )
                    # end

                    # Determine the remaining segment parameters (Alt, Mach, CAS, TAS)
                    seg.propagateParameters()

                else:
                    prevSeg = self.segments[i - 1]
                    refAlt = prevSeg.finalAlt
                    refCAS = prevSeg.finalCAS
                    refTAS = prevSeg.finalTAS
                    refMach = prevSeg.finalMach
                    TASi = seg.initTAS
                    CASi = seg.initCAS
                    Mi = seg.initMach
                    Alti = seg.initAlt
                    if CASi is not None:
                        if not CASi == refCAS:
                            raise Error(
                                "%s: Specified initCAS \
                                          inconsistent with\
                                          previous finalCAS: %f, %f \
                                          "
                                % (seg.phase, CASi, refCAS)
                            )
                        # end
                    else:
                        seg.initCAS = refCAS
                    # end
                    if TASi is not None:
                        if not TASi == refTAS:
                            raise Error(
                                "%s: Specified initTAS \
                                          inconsistent with\
                                          previous finalTAS: %f, %f \
                                          "
                                % (seg.phase, TASi, refTAS)
                            )
                        # end
                    else:
                        seg.initTAS = refTAS
                    # end
                    if Alti is not None:
                        if not Alti == refAlt:
                            raise Error(
                                "%s: Specified initAlt \
                                         inconsistent with\
                                         previous finalAlt"
                                % (seg.phase)
                            )
                        # end
                    else:
                        seg.initAlt = refAlt
                    # end
                    if Mi is not None:
                        if not Mi == refMach:
                            raise Error(
                                "%s: Specified initMach \
                                          inconsistent with\
                                          previous finalMach"
                                % (seg.phase)
                            )
                        # end
                    else:
                        seg.initMach = refMach
                    # end

                    # Determine the remaining segment parameters (Alt, Mach, CAS, TAS)
                    seg.propagateParameters()
                # end
            # end
        # end

    def __str__(self, segStartNum=0):
        """
        Return a string representation of the segments within this profile
        """

        string = "MISSION PROFILE: %s \n" % self.name
        for i in range(len(self.segments)):
            # segTag = '%sS%02d'%(idTag,i)
            string += self.segments[i].__str__(segStartNum + i)

        return string


class MissionSegment:
    """
    Mission Segment Object:

    This is the basic building block of the mission solver.

    Parameters
    ----------
    phase : str
        Segment type selector valid options include

    """

    def __init__(self, phase, **kwargs):

        # have to have a phase type
        self.phase = phase

        # These are the parameters that can be simply set directly in the class.
        paras = {
            "initMach",
            "initAlt",
            "initCAS",
            "initTAS",
            "finalMach",
            "finalAlt",
            "finalCAS",
            "finalTAS",
            "fuelFraction",
            "rangeFraction",
            "segTime",
            "engType",
            "throttle",
            "nIntervals",
            "residualclimbrate",
            "descentrate",
            "climbtdratio",
            "descenttdratio",
        }

        # By default everything is None
        for para in paras:
            setattr(self, para, None)

        # Set default number of intervals
        self.nIntervals = 4

        # Any matching key from kwargs that is in 'paras'
        for key in kwargs:
            if key in paras:
                setattr(self, key, kwargs[key])

        # identify the possible design variables based on what parameters
        # have been set
        varFuncs = ["initMach", "initAlt", "initTAS", "initCAS", "finalMach", "finalAlt", "finalCAS", "finalTAS"]

        self.possibleDVs = set()
        self.segInputs = set()
        for var in varFuncs:
            if getattr(self, var) is not None:
                self.possibleDVs.add(var)
                self.segInputs.add(var)

        # propagateInputs should be true for everything
        # except fuelFraction and fixedThrottle segments
        self.propagateInputs = True
        if self.fuelFraction is not None or self.throttle is not None:
            self.propagateInputs = False

        # Storage of DVs
        self.dvList = {}

        if self.phase.lower() in ["cvelclimb", "cveldescent"]:
            self.constMachDV = False
            self.constVelDV = True
            self.constAltDV = False
        elif self.phase.lower() in ["cmachclimb", "cmachdescent"]:
            self.constMachDV = True
            self.constVelDV = False
            self.constAltDV = False
        elif self.phase.lower() in ["cruise", "loiter"]:
            self.constMachDV = True
            self.constVelDV = True
            self.constAltDV = True
        elif self.phase.lower() in ["acceleratedcruise", "deceleratedcruise"]:
            self.constMachDV = False
            self.constVelDV = False
            self.constAltDV = True
        else:
            self.constMachDV = False
            self.constVelDV = False
            self.constAltDV = False

        self.isFirstStateSeg = False

        return

    def setUnitSystem(self, englishUnits):
        self.atm = ICAOAtmosphere(englishUnits=englishUnits)
        fluidProps = FluidProperties(englishUnits=englishUnits)
        self.R = fluidProps.R
        self.gamma = fluidProps.gamma

    def setDefaults(self, englishUnits):
        # Set default climb/descent rates and td ratios
        if self.residualclimbrate is None:
            if englishUnits:
                self.residualclimbrate = 300.0 / 60.0
            else:
                self.residualclimbrate = 300.0 / 60.0 * 0.3048

        if self.descentrate is None:
            if englishUnits:
                self.descentrate = -2000.0 / 60.0
            else:
                self.descentrate = -2000.0 / 60.0 * 0.3048

        if self.climbtdratio is None:
            self.climbtdratio = 1.1

        if self.descenttdratio is None:
            self.descenttdratio = 0.5

    def determineInputs(self):
        """
        Determine which of the four parameters (h, M, CAS, TAS) are inputs,
        which can be updated directly by the DV. For each end, there should
        be two inputs. At this point, the two beginning inputs should already
        be determined during initalization or by the MissionProfile.
        """

        # Check there are two inputs for the segment start
        count = 0
        for var in self.segInputs:
            if "init" in var:
                count += 1
        if count < 2 and self.fuelFraction is None:
            raise Error(
                "%s: There does not appear to be two inputs at the \
                         start of this segment"
                % self.phase
            )
        elif count > 2 and self.fuelFraction is None:
            raise Error(
                "%s: There appears to be more than two inputs at the \
                         start of this segment, may not be consistent"
                % self.phase
            )

        # If there are two inputs for the segment end, done;
        # otherwise determine based on start
        count = 0
        for var in self.segInputs:
            if "final" in var:
                count += 1
        if count == 2:
            return
        elif count > 2:
            raise Error(
                "%s: There appears to be more than two inputs at the \
                         start of this segment, may not be consistent"
                % self.phase
            )
        else:
            # For any segment with constant Mach, CAS, or altitude...
            if "cmach" in self.phase.lower():
                self.segInputs.add("finalMach")
            elif "cvel" in self.phase.lower():
                self.segInputs.add("finalCAS")
            elif "cruise" in self.phase.lower() or self.phase.lower() == "loiter":
                self.segInputs.add("finalAlt")

            # For cruise segments, copy the initial speeds to final
            if self.phase.lower() == "cruise" or self.phase.lower() == "loiter":
                if "initMach" in self.segInputs:
                    self.segInputs.add("finalMach")
                elif "initCAS" in self.segInputs:
                    self.segInputs.add("finalCAS")
                elif "initTAS" in self.segInputs:
                    self.segInputs.add("finalTAS")

            # # For set throttle segment types
            # if self.throttle != None:
            #     if 'finalMach' not in self.segInputs and 'initMach' in self.segInputs:
            #         self.segInputs.add('finalMach')
            #     if 'finalAlt' not in self.segInputs and 'initAlt' in self.segInputs:
            #         self.segInputs.add('finalAlt')
            #     if 'finalCAS' not in self.segInputs and 'initCAS' in self.segInputs:
            #         self.segInputs.add('finalCAS')
            #     if 'finalTAS' not in self.segInputs and 'initTAS' in self.segInputs:
            #         self.segInputs.add('finalTAS')

    """
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
            # Specified either (h,CAS) or (h,TAS)
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
            # Specified (M,h)
            TAS = M*a
            CAS = self._TAS2CAS(TAS,h)
            setattr(self,TASTag,TAS)
            setattr(self,CASTag,CAS)
        # end
    """

    def propagateParameters(self):
        """
        Set the final V,M,h base on initial values and segType.
        """

        if self.propagateInputs is False:
            # A FuelFraction type segment, nothing to propagate
            return

        elif self.phase.lower() in ["cruise", "loiter"]:
            # Given M, CAS, or TAS, calculate the other two speeds
            self._calculateSpeed(endPoint="start")

            # take everything from init and copy to final
            self.finalAlt = self.initAlt
            self.finalCAS = self.initCAS
            self.finalTAS = self.initTAS
            self.finalMach = self.initMach

        elif self.phase.lower() in ["acceleratedcruise", "deceleratedcruise"]:
            self.finalAlt = self.initAlt
            self._calculateSpeed(endPoint="start")
            self._calculateSpeed(endPoint="end")

        elif self.phase.lower() in ["cvelclimb", "cveldescent"]:
            # Requires either (v, hi, hf), (v, hi, Mf), or (v, Mi, hf)
            self.finalCAS = self.initCAS

            if {"initCAS", "initAlt", "finalAlt"}.issubset(self.segInputs):
                # (v, hi, hf): Solve for the TAS and then for Mach
                self._calculateSpeed(endPoint="start")
                self._calculateSpeed(endPoint="end")

            elif {"initCAS", "initAlt", "finalMach"}.issubset(self.segInputs):
                # (v, hi, Mf): Solve for finalAlt and then TAS
                self.finalAlt = self._solveMachCASIntercept(self.initCAS, self.finalMach)
                self.finalTAS = self._CAS2TAS(self.finalCAS, self.finalAlt)
                self.initTAS = self._CAS2TAS(self.initCAS, self.initAlt)
                a = self._getSoundSpeed(self.initAlt)
                self.initMach = self.initTAS / a

            elif {"initCAS", "initMach", "finalAlt"}.issubset(self.segInputs):
                # (v, Mi, hf): Solve for initAlt and then TAS
                self.initAlt = self._solveMachCASIntercept(self.initCAS, self.initMach)
                self.initTAS = self._CAS2TAS(self.initCAS, self.initAlt)
                self.finalTAS = self._CAS2TAS(self.finalCAS, self.finalAlt)
                a = self._getSoundSpeed(self.finalAlt)
                self.finalMach = self.finalTAS / a

            else:
                raise Error("%s", self.phase)

        elif self.phase.lower() in ["cmachclimb", "cmachdescent"]:
            # Requires either (M, hi, hf), (M, vi, hf), or (M, hi, vf)
            self.finalMach = self.initMach

            if {"initMach", "initAlt", "finalAlt"}.issubset(self.segInputs):
                # (M, hi, hf): Solve for the TAS and then CAS
                self._calculateSpeed(endPoint="start")
                self._calculateSpeed(endPoint="end")

            elif {"initMach", "initCAS", "finalAlt"}.issubset(self.segInputs):
                # (M, vi, hf): Solve for initAlt and then initTAS, finalTAS then finalCAS
                self.initAlt = self._solveMachCASIntercept(self.initCAS, self.initMach)
                self.initTAS = self._CAS2TAS(self.initCAS, self.initAlt)
                a = self._getSoundSpeed(self.finalAlt)
                self.finalTAS = self.finalMach * a
                self.finalCAS = self._TAS2CAS(self.finalTAS, self.finalAlt)

            elif {"initMach", "initAlt", "finalCAS"}.issubset(self.segInputs):
                # (M, hi, vf): Solve for finalAlt and then finalTAS, initTAS then initCAS
                self.finalAlt = self._solveMachCASIntercept(self.finalCAS, self.finalMach)
                self.finalTAS = self._CAS2TAS(self.finalCAS, self.finalAlt)
                a = self._getSoundSpeed(self.initAlt)
                self.initTAS = self.initMach * a
                self.initCAS = self._TAS2CAS(self.initTAS, self.initAlt)

            else:
                raise Error("%s", self.phase)

        else:
            self._calculateSpeed(endPoint="start")
            self._calculateSpeed(endPoint="end")

        """
        elif self.phase.lower() in ['cvelclimb','climb_cvel']:
            # we require that Vi,hi and Mf are specified
            # calculate hf from Vi and Mf
            self.finalCAS = self.initCAS

            #solve for h given M and V
            CAS = getattr(self,'finalCAS')
            M = getattr(self,'finalMach')
            finalAlt = self._solveMachCASIntercept(CAS, M)
            TAS = self._CAS2TAS(CAS,finalAlt)
            setattr(self,'finalAlt',finalAlt)
            setattr(self,'finalTAS',TAS)
        elif self.phase.lower() in ['cmachclimb','climb_cmach']:
            # we require that Mi,hg and Vi are specified
            # calculate hi from Vi and Mf
            CAS = getattr(self,'initCAS')
            M = getattr(self,'initMach')
            setattr(self,'finalMach',M)
            initAlt = self._solveMachCASIntercept(CAS, M)
            setattr(self,'initAlt',initAlt)
            TAS = self._CAS2TAS(CAS,initAlt)
            setattr(self,'initTAS',TAS)

        elif self.phase.lower() in ['cmachdescent','descent_cmach']:
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
        elif self.phase.lower() in ['cveldescent','descent_cvel']:
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
        """

    def _calculateSpeed(self, endPoint="start"):
        """
        This assumes that the altitude and one of three speeds
        (CAS, TAS, or Mach) are given, and calculates the other two speeds.
        """

        if endPoint.lower() == "start":
            CASTag = "initCAS"
            TASTag = "initTAS"
            machTag = "initMach"
            altTag = "initAlt"
        elif endPoint.lower() == "end":
            CASTag = "finalCAS"
            TASTag = "finalTAS"
            machTag = "finalMach"
            altTag = "finalAlt"
        else:
            # invalid endpoint
            raise Error(
                "%s: _calculateSpeed, invalid endPoint:\
                         %s"
                % (self.phase, endPoint)
            )

        CAS = getattr(self, CASTag)
        TAS = getattr(self, TASTag)
        mach = getattr(self, machTag)
        alt = getattr(self, altTag)

        # Given M, CAS, or TAS, calculate the other two speeds
        if alt is None:
            sys.exit(0)
        a = self._getSoundSpeed(alt)
        if CASTag in self.segInputs:
            TAS = self._CAS2TAS(CAS, alt)
            mach = TAS / a
        elif TASTag in self.segInputs:
            CAS = self._TAS2CAS(TAS, alt)
            mach = TAS / a
        elif machTag in self.segInputs:
            TAS = mach * a
            CAS = self._TAS2CAS(TAS, alt)

        setattr(self, CASTag, CAS)
        setattr(self, TASTag, TAS)
        setattr(self, machTag, mach)
        setattr(self, altTag, alt)

    def _getSoundSpeed(self, alt):
        """
        compute the speed of sound at this altitude
        """
        # evaluate the atmosphere model
        P, T = self.atm(alt)
        a = numpy.sqrt(self.gamma * self.R * T)

        return copy.copy(a)

    def _getPTRho(self, alt):
        """
        compute the pressure at this altitude
        """
        # evaluate the atmosphere model
        P, T = self.atm(alt)
        rho = P / (self.R * T)

        return P, T, rho

    def _solveMachCASIntercept(self, CAS, mach, initAlt=3048.0):
        # TAS: True Air speed
        # CAS: Calibrated air speed

        # Simple Newton's method to solve for the altitude at which
        # CAS=mach

        alt = initAlt
        dAlt = 1e1

        res = 1.0
        while abs(res) > 1e-12:
            a = self._getSoundSpeed(alt)
            TAS = self._CAS2TAS(CAS, alt)
            M = TAS / a
            res = M - mach
            a = self._getSoundSpeed(alt + dAlt)
            TAS = self._CAS2TAS(CAS, alt + dAlt)
            M2 = TAS / a
            res2 = M2 - mach
            df = (res2 - res) / dAlt
            if abs(res / df) < 1000.0:
                alt -= res / df
            else:
                alt -= (1.0 / 2.0) * res / df
            # end

        return alt

    def _TAS2CAS(self, TAS, h):
        # get sea level properties
        P0, T0, rho0 = self._getPTRho(0)

        # get the properties at the current altitude
        a = self._getSoundSpeed(h)
        P, T, rho = self._getPTRho(h)

        # compute the ratios at for the static atmospheric states
        PRatio = P / P0
        RhoRatio = rho / rho0

        # Convert the TAS to EAS
        EAS = TAS * numpy.sqrt(RhoRatio)

        # Evaluate the current M based on TAS
        M = TAS / a

        # Evaluate the Calibrated air speed, CAS
        term1 = (1.0 / 8.0) * (1 - PRatio) * M ** 2
        term2 = (3.0 / 640.0) * (1 - 10 * PRatio + 9 * PRatio ** 2) * M ** 4
        ECTerm = 1 + term1 + term2
        CAS = EAS * ECTerm

        return CAS

    def _CAS2TAS(self, CAS, h):
        # TAS: True air speed

        a0 = self._getSoundSpeed(0)
        P0, T0, rho0 = self._getPTRho(0)

        a = self._getSoundSpeed(h)
        P, T, rho = self._getPTRho(h)

        # Source: http://williams.best.vwh.net/avform.htm#Intro
        # Differential pressure: Units of CAS and a0 must be consistent
        DP = P0 * ((1 + 0.2 * (CAS / a0) ** 2) ** (7.0 / 2.0) - 1)  # impact pressure

        M = numpy.sqrt(5 * ((DP / P + 1) ** (2.0 / 7.0) - 1))

        if M > 1:
            raise Error(
                "%s_CAS2TAS: The current mission class is\
                         limited to subsonic missions: %f %f"
                % (self.phase, M, CAS)
            )
            # M_diff = 1.0
            # while M_diff > 1e-4:
            #     # computing Mach number in a supersonic compressible flow by using the
            #     # Rayleigh Supersonic Pitot equation using parameters for air
            #     M_new = 0.88128485 * numpy.sqrt((DP/P + 1) * (1 - 1/(7*M**2))**2.5)
            #     M_diff = abs(M_new - M)
            #     M = M_new

        TAS = M * a

        return TAS

    def setMissionData(self, module, segTypeDict, engTypeDict, idx, segIdx):
        """
        set the data for the current segment in the fortran module
        """
        h1 = self.initAlt
        if h1 is None:
            h1 = 0.0
        h2 = self.finalAlt
        if h2 is None:
            h2 = 0.0
        M1 = self.initMach
        if M1 is None:
            M1 = 0.0
        M2 = self.finalMach
        if M2 is None:
            M2 = 0.0
        deltaTime = self.segTime
        if deltaTime is None:
            deltaTime = 0.0
        # end

        rangeFraction = self.rangeFraction
        if rangeFraction is None:
            rangeFraction = 1.0
        # end

        # Get the fuel-fraction, if provided, then segment is a generic fuel fraction type
        fuelFraction = self.fuelFraction
        throttle = self.throttle
        if fuelFraction is None and throttle is None:
            segTypeID = segTypeDict[self.phase.lower()]
            fuelFraction = 0.0
            throttle = 0.0
        elif fuelFraction is not None:
            segTypeID = segTypeDict["fuelFraction"]
            throttle = 0.0
        elif throttle is not None:
            segTypeID = segTypeDict["fixedThrottle"]
            fuelFraction = 0.0
        # end

        # Get the engine type and ensure the engine type is defined in engTypeDict
        if self.engType not in engTypeDict and self.engType is not None:
            raise Error(f"engType {self.engType} defined in segment {self.phase} not defined in engTypeDict")
        if self.engType is None:
            self.engType = "None"
        engTypeID = engTypeDict[self.engType]

        module.setmissionsegmentdata(
            idx,
            segIdx,
            h1,
            h2,
            M1,
            M2,
            deltaTime,
            fuelFraction,
            throttle,
            rangeFraction,
            segTypeID,
            engTypeID,
            self.nIntervals,
            self.residualclimbrate,
            self.descentrate,
            self.climbtdratio,
            self.descenttdratio,
        )

    def addDV(self, paramKey, lower=-1e20, upper=1e20, scale=1.0, name=None):
        """
        Add one of the class attributes as a mission design
        variable. Typical variables are mach or velocity and altitude
        An error will be given if the requested DV is not allowed to
        be added .


        Parameters
        ----------
        dvName : str
            Name used by the optimizer for this variables.

        paramKey : str
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

        Examples
        --------
        >>> # Add initMach variable with typical bounds
        >>> seg.addDV('initMach', value=0.75, lower=0.0, upper=1.0, scale=1.0)
        """

        # First check if we are allowed to add the DV:
        if paramKey not in self.possibleDVs:
            raise Error(
                "The DV '%s' could not be added. Potential DVs MUST\
            be specified when the missionSegment class is created. \
            For example, if you want initMach as a design variable \
            (...,initMach=value, ...) must\
            be given. The list of possible DVs are: %s."
                % (paramKey, repr(self.possibleDVs))
            )

        if name is None:
            dvName = paramKey
            userDef = False
        else:
            dvName = name
            userDef = True

        value = getattr(self, paramKey)
        # Remove 'init' or 'final' from paramKey and set to dvType
        dvType = paramKey.replace("init", "").replace("final", "")
        if "init" in paramKey:
            isInitVal = True
        elif "final" in paramKey:
            isInitVal = False

        self.dvList[dvName] = SegmentDV(dvType, isInitVal, value, lower, upper, scale, userDef)

    def setParameters(self, value, paramType, isInitVal):
        """
        Design variable handling, where 'initMach' will be of paramType='Mach'
        and isInitVal=True, and the finalMach will be automatically adjusted if needed.
        Also determines if the previous or next segment will be affect as well
        """

        # Determine whether the following or previous segment needs to be updated
        if isInitVal:
            key = "init" + paramType
            updatePrev = True
            if paramType == "Mach":
                updateNext = self.constMachDV
            elif paramType == "Alt":
                updateNext = self.constAltDV
            elif paramType == "CAS" or paramType == "TAS":
                updateNext = self.constVelDV
        else:
            key = "final" + paramType
            updateNext = True
            if paramType == "Mach":
                updatePrev = self.constMachDV
            elif paramType == "Alt":
                updatePrev = self.constAltDV
            elif paramType == "CAS" or paramType == "TAS":
                updatePrev = self.constVelDV

        # Update the value in the current segment
        setattr(self, key, value)

        # If this segment has a constant value, update the init/final value
        if isInitVal and updateNext:
            key = "final" + paramType
            setattr(self, key, value)
        elif (not isInitVal) and updatePrev:
            key = "init" + paramType
            setattr(self, key, value)

        return updatePrev, updateNext

    def __str__(self, segNum=None):
        """
        Return a string representation of the states in this segment
        """

        # if len(idTag) > 0:
        #     idTag = '  ---  %s'%idTag
        if segNum is None:
            idTag = ""
        else:
            idTag = "%02d:" % segNum

        # Putting the states into an array automatically convert Nones to nans
        states = numpy.zeros([2, 4])
        states[0, :] = [self.initAlt, self.initMach, self.initCAS, self.initTAS]
        states[1, :] = [self.finalAlt, self.finalMach, self.finalCAS, self.finalTAS]
        if self.fuelFraction is None:
            fuelFrac = self.fuelFraction
        else:
            fuelFrac = numpy.nan

        string = f"{idTag:>3} {self.phase:>18}  "
        string += "{:>8}  {:>8}  {:>8}  {:>8}  {:>8} \n".format("Alt", "Mach", "CAS", "TAS", "FuelFrac")
        string += "{:>22}  {:8.2f}  {:8.6f}  {:8.4f}  {:8.4f}  {:8.4f} \n".format(
            "",
            states[0, 0],
            states[0, 1],
            states[0, 2],
            states[0, 3],
            fuelFrac,
        )
        string += "{:>22}  {:8.2f}  {:8.6f}  {:8.4f}  {:8.4f} \n".format(
            "", states[1, 0], states[1, 1], states[1, 2], states[1, 3]
        )

        return string


class SegmentDV:
    """
    A container storing information regarding a mission profile variable.
    """

    def __init__(self, dvType, isInitVal, value, lower, upper, scale=1.0, userDef=False):

        self.type = dvType  # String: 'Mach', 'Alt', 'TAS', 'CAS'
        self.isInitVal = isInitVal  # Boolean:
        self.value = value
        self.lower = lower
        self.upper = upper
        self.scale = scale
        self.userDef = userDef

        self.segID = -1  # The segment ID this DV obj was initalized
        # self.offset = offset

    def setSegmentID(self, ID):
        """
        Set the segment ID in which this DV belongs to within the profile
        """

        self.segID = ID
