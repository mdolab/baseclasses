"""
pyAero_solver

Holds the Python Aerodynamic Analysis Classes (base).
"""

# =============================================================================
# Standard Python modules
# =============================================================================
import numpy

# =============================================================================
# Extension modules
# =============================================================================
from .BaseSolver import BaseSolver
from ..utils import CaseInsensitiveDict, Error

# =============================================================================
# AeroSolver Class
# =============================================================================


class AeroSolver(BaseSolver):

    """
    Abstract Class for Aerodynamic Solver Object
    """

    def __init__(
        self,
        name,
        category,
        defaultOptions={},
        options={},
        immutableOptions=set(),
        deprecatedOptions={},
        comm=None,
        informs={},
    ):

        """
        AeroSolver Class Initialization
        """
        # Setup option info
        super().__init__(
            name,
            category=category,
            defaultOptions=defaultOptions,
            options=options,
            immutableOptions=immutableOptions,
            deprecatedOptions=deprecatedOptions,
            comm=comm,
            informs=informs,
        )
        self.families = CaseInsensitiveDict()
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
        for iProc in range(len(faceSizes)):

            connCounter = 0
            for iFace in range(len(faceSizes[iProc])):
                # Get the number of nodes on this face
                faceSize = faceSizes[iProc][iFace]
                faceNodes = conn[iProc][connCounter : connCounter + faceSize]

                # Start by getting the centerpoint
                ptSum = [0, 0, 0]
                for i in range(faceSize):
                    # idx = ptCounter+i
                    idx = faceNodes[i]
                    ptSum += pts[iProc][idx]

                avgPt = ptSum / faceSize

                # Now go around the face and add a triangle for each adjacent pair
                # of points. This assumes an ordered connectivity from the
                # meshwarping
                for i in range(faceSize):
                    idx = faceNodes[i]
                    p0.append(avgPt)
                    v1.append(pts[iProc][idx] - avgPt)
                    if i < (faceSize - 1):
                        idxp1 = faceNodes[i + 1]
                        v2.append(pts[iProc][idxp1] - avgPt)
                    else:
                        # wrap back to the first point for the last element
                        idx0 = faceNodes[0]
                        v2.append(pts[iProc][idx0] - avgPt)

                # Now increment the connectivity
                connCounter += faceSize

        return [p0, v1, v2]

    def writeTriangulatedSurfaceTecplot(self, fileName, groupName=None, **kwargs):
        """
        Write the triangulated surface mesh from the solver in tecplot.

        Parameters
        ----------
        fileName : str
            File name for tecplot file. Should have a .dat extension.

        groupName : str
            Set of boundaries to include in the surface.
        """
        [p0, v1, v2] = self.getTriangulatedMeshSurface(groupName, **kwargs)
        if self.comm.rank == 0:
            f = open(fileName, "w")
            f.write('TITLE = "%s Surface Mesh"\n' % self.name)
            f.write('VARIABLES = "CoordinateX" "CoordinateY" "CoordinateZ"\n')
            f.write("Zone T=%s\n" % ("surf"))
            f.write("Nodes = %d, Elements = %d ZONETYPE=FETRIANGLE\n" % (len(p0) * 3, len(p0)))
            f.write("DATAPACKING=POINT\n")
            for i in range(len(p0)):
                points = []
                points.append(p0[i])
                points.append(p0[i] + v1[i])
                points.append(p0[i] + v2[i])
                for i in range(len(points)):
                    f.write(f"{points[i][0]:f} {points[i][1]:f} {points[i][2]:f}\n")

            for i in range(len(p0)):
                f.write("%d %d %d\n" % (3 * i + 1, 3 * i + 2, 3 * i + 3))

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
        directly in multiPointSparse. For direct interface with pyOptSparse
        the fail flag needs to be returned separately from the funcs.

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
        if "fail" in funcs:
            funcs["fail"] = funcs["fail"] or failFlag
        else:
            funcs["fail"] = failFlag

    def checkAdjointFailure(self, aeroProblem, funcsSens):
        """Take in a an aeroProblem and check for adjoint failure, Then append the
        fail flag in funcsSens. Information regarding whether or not the
        last analysis with the aeroProblem was sucessful is
        included. This information is included as "funcsSens['fail']". If
        the 'fail' entry already exits in the dictionary the following
        operation is performed:

        funcsSens['fail'] = funcsSens['fail'] or <did this problem fail>

        In other words, if any one problem fails, the funcsSens['fail']
        entry will be True. This information can then be used
        directly in multiPointSparse. For direct interface with pyOptSparse
        the fail flag needs to be returned separately from the funcs.

        Parameters
        ----------
        aeroProblem : pyAero_problem class
            The aerodynamic problem to to get the solution for

        funcsSens : dict
            Dictionary into which the functions are saved.

        """
        self.setAeroProblem(aeroProblem)
        # We also add the fail flag into the funcs dictionary. If fail
        # is already there, we just logically 'or' what was
        # there. Otherwise we add a new entry.
        failFlag = self.curAP.adjointFailed
        if "fail" in funcsSens:
            funcsSens["fail"] = funcsSens["fail"] or failFlag
        else:
            funcsSens["fail"] = failFlag

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
            raise Error(
                "The specified groupName '%s' already exists in the " "cgns file or has already been added." % groupName
            )

        # We can actually allow for nested groups. That is, an entry
        # in families may already be a group added in a previous call.
        indices = []
        for fam in families:
            if fam not in self.families:
                raise Error(
                    "The specified family '%s' for group '%s', does "
                    "not exist in the cgns file or has "
                    "not already been added. The current list of "
                    "families (original and grouped) is: %s" % (fam, groupName, repr(self.families.keys()))
                )

            indices.extend(self.families[fam])

        # It is very important that the list of families is sorted
        # becuase in fortran we always use a binary search to check if
        # a famID is in the list.
        self.families[groupName] = sorted(numpy.unique(indices))

    def getSurfaceCoordinates(self, group_name):
        """
        Return the set of surface coordinates cooresponding to a
        Particular group name
        """

        pass

    def getInitialSurfaceCoordinates(self, groupName=None):
        """"""
        if groupName is None:
            groupName = self.allWallsGroup

        if self.mesh is not None:
            if self.DVGeo is not None:
                # if we have a geometry object, return the undeflected
                # shape generated directly from the design variables
                ptSetName = self.getPointSetName(self.curAP.name)
                self.setSurfaceCoordinates(self.DVGeo.update(ptSetName, config=self.curAP.name), self.designFamilyGroup)
                self.updateGeometryInfo()
                return self.getSurfaceCoordinates(groupName)
            else:
                # otherwise, the initial mesh is the undeflected mesh, so
                # return that
                coords = self.mapVector(self.coords0, self.allFamilies, groupName)

                return coords

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
            raise Error("Cannot set new surface coordinate locations without a mesh" "warping object present.")

        # First get the surface coordinates of the meshFamily in case
        # the groupName is a subset, those values will remain unchanged.

        meshSurfCoords = self.getSurfaceCoordinates(self.meshFamilyGroup)
        meshSurfCoords = self.mapVector(coordinates, groupName, self.meshFamilyGroup, meshSurfCoords)

        self.mesh.setSurfaceCoordinates(meshSurfCoords)

    def getForces(self, group_name):
        """
        Return the set of forces at the locations defined by
        getSurfaceCoordinates
        """

        pass

    def globalNKPreCon(self, in_vec):
        """
        Precondition the residual in in_vec for a coupled
        Newton-Krylov Method
        """

        pass

    def totalSurfaceDerivative(self, objective):
        """
        Return the total derivative of the objective at surface
        coordinates
        """

        pass

    def totalAeroDerivative(self, objective):
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

    def setStates(self, states):
        """Set the states on this processor."""

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

    def solveAdjoint(self, objective, *args, **kwargs):
        """
        Solve the adjoint problem for the desired objective functions.

        objectives - List of objective functions

        """
        pass

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

        if groupName not in self.families:
            raise Error(
                "'%s' is not a family in the CGNS file or has not been added"
                " as a combination of families" % groupName
            )

        return self.families[groupName]
