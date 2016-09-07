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
from pyAero_problem import AeroProblem

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
        self.solverCreated = False
        self.families = CaseInsensitiveDict()

        # Initialize Options
        for key in self.defaultOptions:
            self.setOption(key, self.defaultOptions[key][1])

        koptions = kwargs.pop('options', CaseInsensitiveDict())
        for key in koptions:
            self.setOption(key, koptions[key])

        self.solverCreated = True
        self._updateGeomInfo = False

    def setMesh(self, mesh):
        """
        Set the mesh object to the aero_solver to do geometric deformations

        Parameters
        ----------
        mesh : MBMesh or USMesh object
            The mesh object for doing the warping
        """

        # Store a reference to the mesh
        self.mesh = mesh

        # Setup External Warping with volume indices
        meshInd = self.getSolverMeshIndices()
        self.mesh.setExternalMeshIndices(meshInd)

        # Set the surface the user has supplied:
        conn, faceSizes = self.getSurfaceConnectivity(self.meshFamilyGroup)
        pts = self.getSurfaceCoordinates(self.meshFamilyGroup)
        self.mesh.setSurfaceDefinition(pts, conn, faceSizes)


    def setDVGeo(self, DVGeo):
        """
        Set the DVGeometry object that will manipulate 'geometry' in
        this object. Note that <SOLVER> does not **strictly** need a
        DVGeometry object, but if optimization with geometric
        changes is desired, then it is required.

        Parameters
        ----------
        dvGeo : A DVGeometry object.
            Object responsible for manipulating the constraints that
            this object is responsible for.

        Examples
        --------
        >>> CFDsolver = <SOLVER>(comm=comm, options=CFDoptions)
        >>> CFDsolver.setDVGeo(DVGeo)
        """

        self.DVGeo = DVGeo

    def getTriangulatedMeshSurface(self, groupName=None, **kwargs):
        """
        This function returns a trianguled verision of the surface
        mesh on all processors. The intent is to use this for doing
        constraints in DVConstraints.

        Returns
        -------
        surf : list
           List of points and vectors describing the surface. This may
           be passed directly to DVConstraint setSurface() function.
        """

        if groupName is None:
            groupName = self.allWallsGroup

        # Obtain the points and connectivity for the specified
        # groupName
        pts = self.comm.allgather(self.getSurfaceCoordinates(groupName, **kwargs))
        conn, faceSizes = self.getSurfaceConnectivity(groupName)
        conn = numpy.array(conn).flatten()
        conn = self.comm.allgather(conn)
        faceSizes = self.comm.allgather(faceSizes)
      
        # Triangle info...point and two vectors
        p0 = []
        v1 = []
        v2 = []

        # loop over the faces
        for iProc in xrange(len(faceSizes)):

            connCounter=0
            for iFace in xrange(len(faceSizes[iProc])):
                # Get the number of nodes on this face
                faceSize = faceSizes[iProc][iFace]
                faceNodes = conn[iProc][connCounter:connCounter+faceSize]
                
                # Start by getting the centerpoint
                ptSum= [0, 0, 0]
                for i in xrange(faceSize):
                    #idx = ptCounter+i
                    idx = faceNodes[i]
                    ptSum+=pts[iProc][idx]

                avgPt = ptSum/faceSize

                # Now go around the face and add a triangle for each adjacent pair
                # of points. This assumes an ordered connectivity from the
                # meshwarping
                for i in xrange(faceSize):
                    idx = faceNodes[i]
                    p0.append(avgPt)
                    v1.append(pts[iProc][idx]-avgPt)
                    if(i<(faceSize-1)):
                        idxp1 = faceNodes[i+1]
                        v2.append(pts[iProc][idxp1]-avgPt)
                    else:
                        # wrap back to the first point for the last element
                        idx0 = faceNodes[0]
                        v2.append(pts[iProc][idx0]-avgPt)

                # Now increment the connectivity
                connCounter+=faceSize


        return [p0, v1, v2]

    def writeTriangulatedSurfaceTecplot(self,fileName,groupName=None, **kwargs):
        '''
        Write the triangulated surface mesh from the solver in tecplot. 

        Parameters
        ----------
        fileName : str
            File name for tecplot file. Should have a .dat extension. 

        groupName : str
            Set of boundaries to include in the surface.
        '''
        [p0, v1, v2] = self.getTriangulatedMeshSurface(groupName, **kwargs)
        if self.comm.rank==0:
            f = open(fileName, 'w')
            f.write("TITLE = \"%s Surface Mesh\"\n"%self.name)
            f.write("VARIABLES = \"CoordinateX\" \"CoordinateY\" \"CoordinateZ\"\n")
            f.write('Zone T=%s\n'%('surf'))
            f.write('Nodes = %d, Elements = %d ZONETYPE=FETRIANGLE\n'% (
                len(p0)*3, len(p0)))
            f.write('DATAPACKING=POINT\n')
            for i in range(len(p0)):
                points = []
                points.append(p0[i])
                points.append(p0[i]+v1[i])
                points.append(p0[i]+v2[i])
                for i in range(len(points)):
                    f.write('%f %f %f\n'% (points[i][0], points[i][1],points[i][2]))

            for i in range(len(p0)):
                f.write('%d %d %d\n'% (3*i+1, 3*i+2,3*i+3))

            f.close()
        

    def checkSolutionFailure(self, aeroProblem, funcs):
        """Take in a an aeroProblem and check for failure. Then append the
        fail flag in funcs. Information regarding whether or not the
        last analysis with the aeroProblem was sucessful is
        included. This information is included as "funcs['fail']". If
        the 'fail' entry already exits in the dictionary the following
        operation is performed:

        funcs['fail'] = funcs['fail'] or <did this problem fail>

        In other words, if any one problem fails, the funcs['fail']
        entry will be True. This information can then be used
        directly in the pyOptSparse.

        Parameters
        ----------
        aeroProblem : pyAero_problem class
            The aerodynamic problem to to get the solution for

        funcs : dict
            Dictionary into which the functions are saved.

        """
        self.setAeroProblem(aeroProblem)
        # We also add the fail flag into the funcs dictionary. If fail
        # is already there, we just logically 'or' what was
        # there. Otherwise we add a new entry.
        failFlag = self.curAP.solveFailed or self.curAP.fatalFail
        if 'fail' in funcs:
            funcs['fail'] = funcs['fail'] or failFlag
        else:
            funcs['fail'] = failFlag

        
    def resetFlow(self):
        """
        Reset the flow to a uniform state
        """
        
        pass

    def addFamilyGroup(self, groupName, families):
        """Add a custom grouping of families called groupName. The groupName
        must be distinct from the existing families. All families must
        in the 'families' list must be present in the CGNS file.

        Parameters
        ----------
        groupName : str
            User-supplied custom name for the family groupings
        families : list
            List of string. Family names to combine into the family group
        """

        # Do some error checking
        if groupName in self.families:
            raise Error("The specified groupName '%s' already exists in the "
                        "cgns file or has already been added."%groupName)

        # We can actually allow for nested groups. That is, an entry
        # in families may already be a group added in a previous call. 

        indices = []
        for fam in families:
            if fam.lower() not in self.families:
                raise Error("The specified family '%s' for group '%s', does "
                            "not exist in the cgns file or has "
                            "not already been added. The current list of "
                            "families (original and grouped) is: %s"%(
                                fam, groupName, repr(self.families.keys())))

            indices.extend(self.families[fam])         

        self.families[groupName] = sorted(numpy.unique(indices))

    def getSurfaceCoordinates(self,group_name):
        """
        Return the set of surface coordinates cooresponding to a
        Particular group name
        """
        
        pass

    def getInitialSurfaceCoordinates(self, groupName=None):
        """

        """
        if groupName is None:
            groupName = self.allWallsGroup

        if self.mesh is not None:
            if self.DVGeo is not None:
                # if we have a geometry object, return the undeflected
                # shape generated directly from the design variables
                ptSetName = self.getPointSetName(self.curAP.name)
                self.setSurfaceCoordinates(
                    self.DVGeo.update(ptSetName, config=self.curAP.name), 
                    self.designFamilyGroup)
                self.updateGeometryInfo()
                return self.getSurfaceCoordinates(groupName)
            else:
                # otherwise, the initial mesh is the undeflected mesh, so
                # return that
                return self.coords0


    def setSurfaceCoordinates(self, coordinates, groupName=None):
        """
        Set the updated surface coordinates for a particular group.

        Parameters
        ----------
        coordinates : numpy array
            Numpy array of size Nx3, where N is the number of coordinates on this processor.
            This array must have the same shape as the array obtained with getSurfaceCoordinates()

        groupName : str
            Name of family or group of families for which to return coordinates for.

        """
        if self.mesh is None:
            return

        if groupName is None:
            groupName = self.allWallsGroup

        self._updateGeomInfo = True
        if self.mesh is None:
            raise Error("Cannot set new surface coordinate locations without a mesh"
                        "warping object present.")

        # First get the surface coordinates of the meshFamily in case
        # the groupName is a subset, those values will remain unchanged.

        meshSurfCoords = self.getSurfaceCoordinates(self.meshFamilyGroup)
        meshSurfCoords = self.mapVector(coordinates, groupName, 
                                        self.meshFamilyGroup, meshSurfCoords)

        self.mesh.setSurfaceCoordinates(meshSurfCoords)

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
                name,  self.name))

        # Make sure we are not trying to change an immutable option if
        # we are not allowed to.
        if self.solverCreated and name in self.imOptions:
            raise Error("Option '%-35s' cannot be modified after the solver "
                        "is created."%name)

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

    def printFamilyList(self):
        """
        Print a nicely formatted dictionary of the family names
        """
        from pprint import pprint
        pprint(self.families)
# --------------------------
# Private Utility functions
# --------------------------

        
    def _getFamilyList(self, groupName):
        
        if groupName is None:
            groupName = self.allFamilies

        if groupName.lower() not in self.families:
            raise Error("'%s' is not a family in the CGNS file or has not been added"
                        " as a combination of families"%groupName)

        return self.families[groupName]

        
