import tempfile
import unittest
from itertools import product
from pathlib import Path
from typing import List, Tuple

import numpy as np
import numpy.typing as npt

from baseclasses.utils import TecplotFEZone, TecplotOrderedZone, readTecplot, writeTecplot


def createBrickGrid(nx: int, ny: int, nz: int) -> Tuple[npt.ArrayLike, npt.ArrayLike]:
    # Create node coordinates
    x = np.linspace(0, 1, nx + 1)
    y = np.linspace(0, 1, ny + 1)
    z = np.linspace(0, 1, nz + 1)
    xx, yy, zz = np.meshgrid(x, y, z)
    nodes = np.column_stack((xx.flatten(), yy.flatten(), zz.flatten()))

    # Create element connectivity
    connectivity = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                # Get the eight corners of the hexahedron
                n0 = i + j * (nx + 1) + k * (nx + 1) * (ny + 1)
                n1 = n0 + 1
                n2 = n1 + (nx + 1)
                n3 = n2 - 1
                n4 = n0 + (nx + 1) * (ny + 1)
                n5 = n4 + 1
                n6 = n5 + (nx + 1)
                n7 = n6 - 1

                connectivity.append([n0, n1, n2, n3, n4, n5, n6, n7])

    connectivity = np.array(connectivity)

    return nodes, connectivity


def createTetGrid(nx: int, ny: int, nz: int) -> Tuple[npt.ArrayLike, npt.ArrayLike]:
    # Create node coordinates
    x = np.linspace(0, 1, nx + 1)
    y = np.linspace(0, 1, ny + 1)
    z = np.linspace(0, 1, nz + 1)
    xx, yy, zz = np.meshgrid(x, y, z)
    nodes = np.column_stack((xx.flatten(), yy.flatten(), zz.flatten()))

    # Create element connectivity
    connectivity = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                # Get the eight corners of the hexahedron
                n0 = i + j * (nx + 1) + k * (nx + 1) * (ny + 1)
                n1 = n0 + 1
                n2 = n1 + (nx + 1)
                n3 = n2 - 1
                n4 = n0 + (nx + 1) * (ny + 1)
                n5 = n4 + 1
                n6 = n5 + (nx + 1)
                n7 = n6 - 1

                # Basic subdivision (always add these)
                connectivity.extend(
                    [
                        [n0, n1, n3, n7],
                        [n0, n1, n4, n7],
                        [n1, n2, n3, n7],
                        [n1, n2, n6, n7],
                        [n1, n4, n5, n7],
                        [n1, n5, n6, n7],
                    ]
                )

                # Additional tetrahedra for boundary faces
                if i == 0:
                    connectivity.append([n0, n3, n4, n7])
                if i == nx - 1:
                    connectivity.append([n1, n2, n5, n6])
                if j == 0:
                    connectivity.append([n0, n1, n4, n5])
                if j == ny - 1:
                    connectivity.append([n2, n3, n6, n7])
                if k == 0:
                    connectivity.append([n0, n1, n2, n3])
                if k == nz - 1:
                    connectivity.append([n4, n5, n6, n7])

    connectivity = np.array(connectivity)

    return nodes, connectivity


# Create a finite element mesh with connectivity
def createQuadGrid(nx: int, ny: int) -> Tuple[npt.ArrayLike, npt.ArrayLike]:
    # Create node coordinates
    x = np.linspace(0, 1, nx + 1)
    y = np.linspace(0, 1, ny + 1)
    xx, yy = np.meshgrid(x, y)
    nodes = np.column_stack((xx.flatten(), yy.flatten()))

    # Create element connectivity
    connectivity = []
    for j in range(ny):
        for i in range(nx):
            n1 = i + j * (nx + 1)
            n2 = n1 + 1
            n3 = n2 + nx + 1
            n4 = n3 - 1
            connectivity.append([n1, n2, n3, n4])

    connectivity = np.array(connectivity)

    return nodes, connectivity


def createTriGrid(nx: int, ny: int) -> Tuple[npt.ArrayLike, npt.ArrayLike]:
    # Create node coordinates
    x = np.linspace(0, 1, nx + 1)
    y = np.linspace(0, 1, ny + 1)
    xx, yy = np.meshgrid(x, y)
    nodes = np.column_stack((xx.flatten(), yy.flatten()))

    # Create element connectivity
    connectivity = []
    for j in range(ny):
        for i in range(nx):
            n1 = i + j * (nx + 1)
            n2 = n1 + 1
            n3 = n2 + nx + 1
            connectivity.append([n1, n2, n3])

            n1 = i + j * (nx + 1)
            n2 = n1 + nx + 1
            n3 = n2 + 1
            connectivity.append([n1, n2, n3])

    connectivity = np.array(connectivity)

    return nodes, connectivity


def createLineSegGrid(nx: int) -> Tuple[npt.ArrayLike, npt.ArrayLike]:
    # Create node coordinates
    x = np.linspace(0, 1, nx + 1)
    nodes = np.column_stack((x, x**2))

    # Create element connectivity
    connectivity = np.column_stack((np.arange(nx), np.arange(1, nx + 1)))

    return nodes, connectivity


class TestTecplotIO(unittest.TestCase):
    N_PROCS = 1

    def setUp(self):
        np.random.seed(123)

        thisDir = Path(__file__).parent
        self.externalFileAscii = thisDir / "input" / "airfoil_000_slices.dat"
        self.externalFileBinary = thisDir / "input" / "airfoil_000_surf.plt"

    def assertOrderedZonesEqual(self, zones1: List[TecplotOrderedZone], zones2: List[TecplotOrderedZone]):
        self.assertEqual(len(zones1), len(zones2))
        for zone1, zone2 in zip(zones1, zones2):
            self.assertEqual(zone1.name, zone2.name)
            self.assertEqual(zone1.shape, zone2.shape)
            self.assertListEqual(zone1.variables, zone2.variables)
            self.assertEqual(zone1.iMax, zone2.iMax)
            self.assertEqual(zone1.jMax, zone2.jMax)
            self.assertEqual(zone1.kMax, zone2.kMax)
            self.assertEqual(zone1.solutionTime, zone2.solutionTime)
            self.assertEqual(zone1.strandID, zone2.strandID)

    def assertFEZonesEqual(self, zones1: List[TecplotFEZone], zones2: List[TecplotFEZone]):
        self.assertEqual(len(zones1), len(zones2))
        for zone1, zone2 in zip(zones1, zones2):
            self.assertEqual(zone1.name, zone2.name)
            self.assertEqual(zone1.shape, zone2.shape)
            self.assertListEqual(zone1.variables, zone2.variables)
            self.assertEqual(zone1.nElements, zone2.nElements)
            self.assertEqual(zone1.nNodes, zone2.nNodes)
            self.assertEqual(zone1.solutionTime, zone2.solutionTime)
            self.assertEqual(zone1.strandID, zone2.strandID)
            self.assertEqual(zone1.tetrahedral, zone2.tetrahedral)

    def test_orderedZone(self):
        # Create a 3D grid of shape (nx, ny, nz, 3)
        nx, ny, nz = 10, 10, 10
        X = np.random.rand(nx, ny, nz)
        Y = np.random.rand(nx, ny, nz)
        Z = np.random.rand(nx, ny, nz)

        # Create a Tecplot zone
        zone = TecplotOrderedZone("Grid", {"X": X, "Y": Y, "Z": Z})

        self.assertEqual(zone.name, "Grid")
        self.assertEqual(zone.shape, (nx, ny, nz))
        self.assertEqual(len(zone.variables), 3)
        self.assertListEqual(zone.variables, ["X", "Y", "Z"])
        self.assertEqual(zone.iMax, nx)
        self.assertEqual(zone.jMax, ny)
        self.assertEqual(zone.kMax, nz)
        self.assertEqual(zone.solutionTime, 0.0)
        self.assertEqual(zone.strandID, -1)

    def test_FEZone(self):
        # Create a quad grid
        nx, ny = 10, 10
        nodes, connectivity = createQuadGrid(nx, ny)

        solutionTime = 10.0
        strandID = 4
        # Create a Tecplot zone with Quad elements
        zone = TecplotFEZone(
            "QuadGrid", {"X": nodes[:, 0], "Y": nodes[:, 1]}, connectivity, solutionTime=solutionTime, strandID=strandID
        )

        self.assertEqual(zone.name, "QuadGrid")
        self.assertEqual(zone.shape, ((nx + 1) * (ny + 1),))
        self.assertEqual(len(zone.variables), 2)
        self.assertListEqual(zone.variables, ["X", "Y"])
        self.assertEqual(zone.nElements, connectivity.shape[0])
        self.assertEqual(zone.nNodes, (nx + 1) * (ny + 1))
        self.assertEqual(zone.solutionTime, solutionTime)
        self.assertEqual(zone.strandID, strandID)

        nx, ny, nz = 10, 10, 10
        nodes, connectivity = createTetGrid(nx, ny, nz)

        # Create a Tecplot zone with Tet elements
        zone = TecplotFEZone(
            "TetGrid",
            {"X": nodes[:, 0], "Y": nodes[:, 1], "Z": nodes[:, 2]},
            connectivity,
            solutionTime=solutionTime,
            strandID=strandID,
            tetrahedral=True,
        )

        self.assertEqual(zone.name, "TetGrid")
        self.assertEqual(zone.shape, ((nx + 1) * (ny + 1) * (nz + 1),))
        self.assertEqual(len(zone.variables), 3)
        self.assertListEqual(zone.variables, ["X", "Y", "Z"])
        self.assertEqual(zone.nElements, connectivity.shape[0])
        self.assertEqual(zone.nNodes, (nx + 1) * (ny + 1) * (nz + 1))
        self.assertEqual(zone.solutionTime, solutionTime)
        self.assertEqual(zone.strandID, strandID)

    def test_ASCIIReadWriteOrderedZones(self):
        zones: List[TecplotOrderedZone] = []

        X = np.random.rand(10)
        Y = np.random.rand(10)
        Z = np.random.rand(10)
        zone = TecplotOrderedZone("Grid", {"X": X, "Y": Y, "Z": Z})
        zones.append(zone)

        X = np.random.rand(10, 10)
        Y = np.random.rand(10, 10)
        Z = np.random.rand(10, 10)
        zone = TecplotOrderedZone("Grid", {"X": X, "Y": Y, "Z": Z})
        zones.append(zone)

        X = np.random.rand(10, 10)
        Y = np.random.rand(10, 10)
        Z = np.random.rand(10, 10)
        zone = TecplotOrderedZone("Grid", {"X": X, "Y": Y, "Z": Z})
        zones.append(zone)

        X = np.random.rand(10, 10, 10)
        Y = np.random.rand(10, 10, 10)
        Z = np.random.rand(10, 10, 10)
        zone = TecplotOrderedZone("Grid", {"X": X, "Y": Y, "Z": Z})
        zones.append(zone)

        title = "ASCII ORDERED ZONES TEST"
        with tempfile.NamedTemporaryFile(suffix=".dat", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, datapacking="POINT", precision="SINGLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertOrderedZonesEqual(zones, zonesRead)

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, datapacking="BLOCK", precision="SINGLEs")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertOrderedZonesEqual(zones, zonesRead)

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, datapacking="POINT", precision="DOUBLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertOrderedZonesEqual(zones, zonesRead)

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, datapacking="BLOCK", precision="DOUBLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

    def test_BinaryReadWriteOrderedZones(self):
        zones: List[TecplotOrderedZone] = []

        X = np.random.rand(10)
        Y = np.random.rand(10)
        Z = np.random.rand(10)
        zone = TecplotOrderedZone("Grid", {"X": X, "Y": Y, "Z": Z})
        zones.append(zone)

        X = np.random.rand(10, 10)
        Y = np.random.rand(10, 10)
        Z = np.random.rand(10, 10)
        zone = TecplotOrderedZone("Grid", {"X": X, "Y": Y, "Z": Z})
        zones.append(zone)

        X = np.random.rand(10, 10)
        Y = np.random.rand(10, 10)
        Z = np.random.rand(10, 10)
        zone = TecplotOrderedZone("Grid", {"X": X, "Y": Y, "Z": Z})
        zones.append(zone)

        X = np.random.rand(10, 10, 10)
        Y = np.random.rand(10, 10, 10)
        Z = np.random.rand(10, 10, 10)
        zone = TecplotOrderedZone("Grid", {"X": X, "Y": Y, "Z": Z})
        zones.append(zone)

        title = "BINARY ORDERED ZONES TEST"
        with tempfile.NamedTemporaryFile(suffix=".plt", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, precision="SINGLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertOrderedZonesEqual(zones, zonesRead)

        with tempfile.NamedTemporaryFile(suffix=".plt", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, precision="DOUBLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertOrderedZonesEqual(zones, zonesRead)

    def test_ASCIIReadWriteFELineSegZones(self):
        zones: List[TecplotFEZone] = []

        for nx in range(2, 10):
            nodes, connectivity = createLineSegGrid(nx)
            zone = TecplotFEZone(f"LineSegGrid_{nx}", {"X": nodes[:, 0], "Y": nodes[:, 1]}, connectivity)
            zones.append(zone)

        title = "ASCII FELINESEG ZONES TEST"
        with tempfile.NamedTemporaryFile(suffix=".dat", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, datapacking="POINT", precision="SINGLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, datapacking="BLOCK", precision="SINGLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, datapacking="POINT", precision="DOUBLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, datapacking="BLOCK", precision="DOUBLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

    def test_BinaryReadWriteFELineSegZones(self):
        zones: List[TecplotFEZone] = []

        for nx in range(2, 10):
            nodes, connectivity = createLineSegGrid(nx)
            zone = TecplotFEZone(f"LineSegGrid_{nx}", {"X": nodes[:, 0], "Y": nodes[:, 1]}, connectivity)
            zones.append(zone)

        title = "BINARY FELINESEG ZONES TEST"
        with tempfile.NamedTemporaryFile(suffix=".plt", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, precision="SINGLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

        with tempfile.NamedTemporaryFile(suffix=".plt", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, precision="DOUBLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

    def test_ASCIIReadWriteFETriZones(self):
        zones: List[TecplotFEZone] = []
        dims = product(range(2, 10), range(2, 10))

        for nx, ny in dims:
            nodes, connectivity = createTriGrid(nx, ny)
            zone = TecplotFEZone(f"TriGrid_{nx}", {"X": nodes[:, 0], "Y": nodes[:, 1]}, connectivity)
            zones.append(zone)

        title = "ASCII FETRIANGLE ZONES TEST"
        with tempfile.NamedTemporaryFile(suffix=".dat", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, datapacking="POINT", precision="SINGLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, datapacking="BLOCK", precision="SINGLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, datapacking="POINT", precision="DOUBLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, datapacking="BLOCK", precision="DOUBLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

    def test_BinaryReadWriteFETriZones(self):
        zones: List[TecplotFEZone] = []
        dims = product(range(2, 10), range(2, 10))

        for nx, ny in dims:
            nodes, connectivity = createTriGrid(nx, ny)
            zone = TecplotFEZone(f"TriGrid_{nx}", {"X": nodes[:, 0], "Y": nodes[:, 1]}, connectivity)
            zones.append(zone)

        title = "BINARY FETRIANGLE ZONES TEST"
        with tempfile.NamedTemporaryFile(suffix=".plt", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, precision="SINGLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

        with tempfile.NamedTemporaryFile(suffix=".plt", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, precision="DOUBLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

    def test_ASCIIReadWriteFEQuadZones(self):
        zones: List[TecplotFEZone] = []
        dims = product(range(2, 10), range(2, 10))

        for nx, ny in dims:
            nodes, connectivity = createQuadGrid(nx, ny)
            zone = TecplotFEZone(f"QuadGrid_{nx}", {"X": nodes[:, 0], "Y": nodes[:, 1]}, connectivity)
            zones.append(zone)

        title = "ASCII FEQUADRILATERAL ZONES TEST"
        with tempfile.NamedTemporaryFile(suffix=".dat", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, datapacking="POINT", precision="SINGLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, datapacking="BLOCK", precision="SINGLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, datapacking="POINT", precision="DOUBLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, datapacking="BLOCK", precision="DOUBLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

    def test_BinaryReadWriteFEQuadZones(self):
        zones: List[TecplotFEZone] = []
        dims = product(range(2, 10), range(2, 10))

        for nx, ny in dims:
            nodes, connectivity = createQuadGrid(nx, ny)
            zone = TecplotFEZone(f"QuadGrid_{nx}", {"X": nodes[:, 0], "Y": nodes[:, 1]}, connectivity)
            zones.append(zone)

        title = "BINARY FEQUADRILATERAL ZONES TEST"
        with tempfile.NamedTemporaryFile(suffix=".plt", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, precision="SINGLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

        with tempfile.NamedTemporaryFile(suffix=".plt", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, precision="DOUBLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

    def test_ASCIIReadWriteFETetZones(self):
        zones: List[TecplotFEZone] = []
        npts = 5
        dims = product(range(2, npts), range(2, npts), range(2, npts))

        for nx, ny, nz in dims:
            nodes, connectivity = createTetGrid(nx, ny, nz)
            zone = TecplotFEZone(
                f"TetGrid_{nx}", {"X": nodes[:, 0], "Y": nodes[:, 1], "Z": nodes[:, 2]}, connectivity, tetrahedral=True
            )
            zones.append(zone)

        title = "ASCII FETETRAHEDRAL ZONES TEST"
        with tempfile.NamedTemporaryFile(suffix=".dat", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, datapacking="POINT", precision="SINGLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, datapacking="BLOCK", precision="SINGLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, datapacking="POINT", precision="DOUBLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, datapacking="BLOCK", precision="DOUBLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

    def test_BinaryReadWriteFETetZones(self):
        zones: List[TecplotFEZone] = []
        npts = 5
        dims = product(range(2, npts), range(2, npts), range(2, npts))

        for nx, ny, nz in dims:
            nodes, connectivity = createTetGrid(nx, ny, nz)
            zone = TecplotFEZone(
                f"TetGrid_{nx}", {"X": nodes[:, 0], "Y": nodes[:, 1], "Z": nodes[:, 2]}, connectivity, tetrahedral=True
            )
            zones.append(zone)

        title = "BINARY FETETRAHEDRAL ZONES TEST"
        with tempfile.NamedTemporaryFile(suffix=".plt", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, precision="SINGLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

        with tempfile.NamedTemporaryFile(suffix=".plt", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, precision="DOUBLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

    def test_ASCIIReadWriteFEBrickZones(self):
        zones: List[TecplotFEZone] = []
        npts = 5
        dims = product(range(2, npts), range(2, npts), range(2, npts))

        for nx, ny, nz in dims:
            nodes, connectivity = createBrickGrid(nx, ny, nz)
            zone = TecplotFEZone(
                f"BrickGrid_{nx}", {"X": nodes[:, 0], "Y": nodes[:, 1], "Z": nodes[:, 2]}, connectivity
            )
            zones.append(zone)

        title = "ASCII FEBRICK ZONES TEST"
        with tempfile.NamedTemporaryFile(suffix=".dat", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, datapacking="POINT", precision="SINGLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, datapacking="BLOCK", precision="SINGLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, datapacking="POINT", precision="DOUBLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, datapacking="BLOCK", precision="DOUBLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

    def test_BinaryReadWriteFEBrickZones(self):
        zones: List[TecplotFEZone] = []
        npts = 5
        dims = product(range(2, npts), range(2, npts), range(2, npts))

        for nx, ny, nz in dims:
            nodes, connectivity = createBrickGrid(nx, ny, nz)
            zone = TecplotFEZone(
                f"BrickGrid_{nx}", {"X": nodes[:, 0], "Y": nodes[:, 1], "Z": nodes[:, 2]}, connectivity
            )
            zones.append(zone)

        title = "BINARY FEBRICK ZONES TEST"
        with tempfile.NamedTemporaryFile(suffix=".plt", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, precision="SINGLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

        with tempfile.NamedTemporaryFile(suffix=".plt", delete=True) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, precision="DOUBLE")
            titleRead, zonesRead = readTecplot(tmpfile.name)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

    def test_ASCIIReadWriteExternal(self):
        try:
            title, zones = readTecplot(self.externalFileAscii)
        except FileNotFoundError:
            self.fail(f"Reading external ASCII file {self.externalFileAscii} failed.")

    def test_BinaryReadWriteExternal(self):
        try:
            title, zones = readTecplot(self.externalFileBinary)
        except FileNotFoundError:
            self.fail(f"Reading external binary file {self.externalFileBinary} failed.")
