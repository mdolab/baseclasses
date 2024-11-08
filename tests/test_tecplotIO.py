import itertools
import tempfile
import unittest
from itertools import product
from pathlib import Path
from typing import List, Tuple

import numpy as np
import numpy.typing as npt
from parameterized import parameterized

from baseclasses.utils import TecplotFEZone, TecplotOrderedZone, readTecplot, writeTecplot
from baseclasses.utils.tecplotIO import Separator, ZoneType

# --- Save tempfile locally or in a temp directory ---
SAVE_TEMPFILES = False
SAVE_DIR = Path(__file__).parent / "tmp_tecplot" if SAVE_TEMPFILES else None
if SAVE_DIR is not None:
    SAVE_DIR.mkdir(exist_ok=True)

# --- Define test matrices for Ordered and FE Zones ---
TEST_CASES_ORDERED = [
    tc
    for tc in itertools.product(
        [(10,), (100,), (10, 10), (100, 100), (10, 10, 10)],
        ["SINGLE", "DOUBLE"],
        ["POINT", "BLOCK"],
        [".dat", ".plt"],
        [Separator.SPACE, Separator.COMMA, Separator.TAB, Separator.NEWLINE, Separator.CARRIAGE_RETURN],
    )
]
# Add a single stress test case for each datapacking
TEST_CASES_ORDERED.append(((100, 100, 100), "DOUBLE", "BLOCK", ".dat", Separator.SPACE))
TEST_CASES_ORDERED.append(((100, 100, 100), "DOUBLE", "POINT", ".dat", Separator.COMMA))

# filter out cases that use POINT datapacking with binary '.plt' extensions
TEST_CASES_ORDERED = [tc for tc in TEST_CASES_ORDERED if not (tc[2] == "POINT" and tc[3] == ".plt")]

TEST_CASES_FE = [
    tc
    for tc in itertools.product(
        [ZoneType.FELINESEG, ZoneType.FETRIANGLE, ZoneType.FEQUADRILATERAL, ZoneType.FETETRAHEDRON, ZoneType.FEBRICK],
        ["SINGLE", "DOUBLE"],
        ["POINT", "BLOCK"],
        [".dat", ".plt"],
        [Separator.SPACE, Separator.COMMA, Separator.TAB, Separator.NEWLINE, Separator.CARRIAGE_RETURN],
    )
]
# filter out cases that use POINT datapacking with binary '.plt' extensions
TEST_CASES_FE = [tc for tc in TEST_CASES_FE if not (tc[2] == "POINT" and tc[3] == ".plt")]


def createBrickGrid(ni: int, nj: int, nk: int) -> Tuple[npt.NDArray, npt.NDArray]:
    """Create a 3D grid of hexahedral 'brick' elements.

    Parameters
    ----------
    ni : int
        The number of elements in the i-direction.
    nj : int
        The number of elements in the j-direction.
    nk : int
        The number of elements in the k-direction.

    Returns
    -------
    Tuple[npt.NDArray, npt.NDArray]
        A tuple containing the node coordinates and element connectivity.
    """
    x = np.linspace(0, 1, ni)
    y = np.linspace(0, 1, nj)
    z = np.linspace(0, 1, nk)
    x, y, z = np.meshgrid(x, y, z)
    nodal_data = np.column_stack((x.flatten(), y.flatten(), z.flatten()))

    connectivity = []
    for i in range(nk - 1):
        for j in range(nj - 1):
            for k in range(ni - 1):
                index = i * (ni * nj) + j * ni + k
                connectivity.append(
                    [
                        index,
                        index + 1,
                        index + ni + 1,
                        index + ni,
                        index + (ni * nj),
                        index + (ni * nj) + 1,
                        index + (ni * nj) + ni + 1,
                        index + (ni * nj) + ni,
                    ]
                )

    return nodal_data, np.array(connectivity)


def createTetGrid(ni: int, nj: int, nk: int) -> Tuple[npt.NDArray, npt.NDArray]:
    """Create a 3D grid of tetrahedral elements.

    Parameters
    ----------
    ni : int
        The number of elements in the i-direction.
    nj : int
        The number of elements in the j-direction.
    nk : int
        The number of elements in the k-direction.

    Returns
    -------
    Tuple[npt.NDArray, npt.NDArray]
        A tuple containing the node coordinates and element connectivity.
    """
    # Create node coordinates
    x = np.linspace(0, 1, ni + 1)
    y = np.linspace(0, 1, nj + 1)
    z = np.linspace(0, 1, nk + 1)
    xx, yy, zz = np.meshgrid(x, y, z)
    nodes = np.column_stack((xx.flatten(), yy.flatten(), zz.flatten()))

    # Create element connectivity
    connectivity = []
    for k in range(nk):
        for j in range(nj):
            for i in range(ni):
                # Get the eight corners of the hexahedron
                n0 = i + j * (ni + 1) + k * (ni + 1) * (nj + 1)
                n1 = n0 + 1
                n2 = n1 + (ni + 1)
                n3 = n2 - 1
                n4 = n0 + (ni + 1) * (nj + 1)
                n5 = n4 + 1
                n6 = n5 + (ni + 1)
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
                if i == ni - 1:
                    connectivity.append([n1, n2, n5, n6])
                if j == 0:
                    connectivity.append([n0, n1, n4, n5])
                if j == nj - 1:
                    connectivity.append([n2, n3, n6, n7])
                if k == 0:
                    connectivity.append([n0, n1, n2, n3])
                if k == nk - 1:
                    connectivity.append([n4, n5, n6, n7])

    connectivity = np.array(connectivity)

    return nodes, connectivity


# Create a finite element mesh with connectivity
def createQuadGrid(ni: int, nj: int) -> Tuple[npt.NDArray, npt.NDArray]:
    """Create a 2D grid of quadrilateral elements.

    Parameters
    ----------
    ni : int
        The number of elements in the i-direction.
    nj : int
        The number of elements in the j-direction.

    Returns
    -------
    Tuple[npt.NDArray, npt.NDArray]
        A tuple containing the node coordinates and element connectivity.
    """
    # Create node coordinates
    x = np.linspace(0, 1, ni + 1)
    y = np.linspace(0, 1, nj + 1)
    xx, yy = np.meshgrid(x, y)
    nodes = np.column_stack((xx.flatten(), yy.flatten(), np.zeros_like(xx.flatten())))

    # Create element connectivity
    connectivity = []
    for j in range(nj):
        for i in range(ni):
            n1 = i + j * (ni + 1)
            n2 = n1 + 1
            n3 = n2 + ni + 1
            n4 = n3 - 1
            connectivity.append([n1, n2, n3, n4])

    connectivity = np.array(connectivity)

    return nodes, connectivity


def createTriGrid(ni: int, nj: int) -> Tuple[npt.NDArray, npt.NDArray]:
    """Create a 2D grid of triangular elements.

    Parameters
    ----------
    ni : int
        The number of elements in the i-direction.
    nj : int
        The number of elements in the j-direction.

    Returns
    -------
    Tuple[npt.NDArray, npt.NDArray]
        A tuple containing the node coordinates and element connectivity.
    """
    # Create node coordinates
    x = np.linspace(0, 1, ni + 1)
    y = np.linspace(0, 1, nj + 1)
    xx, yy = np.meshgrid(x, y)
    nodes = np.column_stack((xx.flatten(), yy.flatten(), np.zeros_like(xx.flatten())))

    # Create element connectivity
    connectivity = []
    for j in range(nj):
        for i in range(ni):
            n1 = i + j * (ni + 1)
            n2 = n1 + 1
            n3 = n2 + ni + 1
            connectivity.append([n1, n2, n3])

            n1 = i + j * (ni + 1)
            n2 = n1 + ni + 1
            n3 = n2 + 1
            connectivity.append([n1, n2, n3])

    connectivity = np.array(connectivity)

    return nodes, connectivity


def createLineSegGrid(ni: int) -> Tuple[npt.NDArray, npt.NDArray]:
    """Create a 1D grid of line segments.

    Parameters
    ----------
    ni : int
        The number of elements in the i-direction.

    Returns
    -------
    Tuple[npt.NDArray, npt.NDArray]
        A tuple containing the node coordinates and element connectivity.
    """
    # Create node coordinates
    x = np.linspace(0, 1, ni + 1)
    nodes = np.column_stack((x, x**2, np.zeros_like(x)))

    # Create element connectivity
    connectivity = np.column_stack((np.arange(ni), np.arange(1, ni + 1)))

    return nodes, connectivity


class TestTecplotIO(unittest.TestCase):
    N_PROCS = 1

    def setUp(self):
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

        msg = "Zone name must be a string"
        with self.assertRaises(TypeError, msg=msg):
            TecplotOrderedZone(123, {"X": X, "Y": Y, "Z": Z}, solutionTime=0.0, strandID=-1)

        msg = "Solution time must be a float"
        with self.assertRaises(TypeError):
            TecplotOrderedZone("Grid", {"X": X, "Y": Y, "Z": Z}, solutionTime="1.0", strandID=-1)

        msg = "Solution time must be greater than or equal to zero"
        with self.assertRaises(ValueError):
            TecplotOrderedZone("Grid", {"X": X, "Y": Y, "Z": Z}, solutionTime=-1.0, strandID=1)

        msg = "Strand ID must be an integer"
        with self.assertRaises(TypeError):
            TecplotOrderedZone("Grid", {"X": X, "Y": Y, "Z": Z}, solutionTime=0.0, strandID="1")

        msg = "Data values must be numpy arrays."
        with self.assertRaises(TypeError):
            TecplotOrderedZone(
                "Grid", {"X": X.tolist(), "Y": Y.tolist(), "Z": Z.tolist()}, solutionTime=0.0, strandID=-1
            )

        msg = "Data must be a dictionary."
        with self.assertRaises(TypeError):
            TecplotOrderedZone("Grid", X, solutionTime=0.0, strandID=-1)

        msg = "All variables must have the same shape."
        with self.assertRaises(ValueError):
            TecplotOrderedZone("Grid", {"X": X, "Y": Y, "Z": Z[:-1]}, solutionTime=0.0, strandID=-1)

    def test_FEZone(self):
        # Create a quad grid
        nx, ny = 10, 10
        nodes, connectivity = createQuadGrid(nx, ny)

        solutionTime = 10.0
        strandID = 4
        # Create a Tecplot zone with Quad elements
        zone = TecplotFEZone(
            "QuadGrid",
            {"X": nodes[:, 0], "Y": nodes[:, 1]},
            connectivity,
            zoneType=ZoneType.FEQUADRILATERAL,
            solutionTime=solutionTime,
            strandID=strandID,
        )

        self.assertEqual(zone.name, "QuadGrid")
        self.assertEqual(zone.shape, ((nx + 1) * (ny + 1),))
        self.assertEqual(len(zone.variables), 2)
        self.assertListEqual(zone.variables, ["X", "Y"])
        self.assertEqual(zone.nElements, connectivity.shape[0])
        self.assertEqual(zone.nNodes, (nx + 1) * (ny + 1))
        self.assertEqual(zone.solutionTime, solutionTime)
        self.assertEqual(zone.strandID, strandID)
        self.assertEqual(zone.zoneType, ZoneType.FEQUADRILATERAL)

        nx, ny, nz = 10, 10, 10
        nodes, connectivity = createTetGrid(nx, ny, nz)

        # Create a Tecplot zone with Tet elements
        zone = TecplotFEZone(
            "TetGrid",
            {"X": nodes[:, 0], "Y": nodes[:, 1], "Z": nodes[:, 2]},
            connectivity,
            zoneType=ZoneType.FETETRAHEDRON,
            solutionTime=solutionTime,
            strandID=strandID,
        )

        self.assertEqual(zone.name, "TetGrid")
        self.assertEqual(zone.shape, ((nx + 1) * (ny + 1) * (nz + 1),))
        self.assertEqual(len(zone.variables), 3)
        self.assertListEqual(zone.variables, ["X", "Y", "Z"])
        self.assertEqual(zone.nElements, connectivity.shape[0])
        self.assertEqual(zone.nNodes, (nx + 1) * (ny + 1) * (nz + 1))
        self.assertEqual(zone.solutionTime, solutionTime)
        self.assertEqual(zone.strandID, strandID)
        self.assertEqual(zone.zoneType, ZoneType.FETETRAHEDRON)

        msg = "Zone name must be a string"
        with self.assertRaises(TypeError, msg=msg):
            TecplotFEZone(
                123,
                {"X": nodes[:, 0], "Y": nodes[:, 1], "Z": nodes[:, 2]},
                connectivity,
                zoneType=ZoneType.FETETRAHEDRON,
            )

        msg = "Solution time must be a float"
        with self.assertRaises(TypeError):
            TecplotFEZone(
                "TetGrid",
                {"X": nodes[:, 0], "Y": nodes[:, 1], "Z": nodes[:, 2]},
                connectivity,
                zoneType=ZoneType.FETETRAHEDRON,
                solutionTime="1.0",
            )

        msg = "Solution time must be greater than or equal to zero"
        with self.assertRaises(ValueError):
            TecplotFEZone(
                "TetGrid",
                {"X": nodes[:, 0], "Y": nodes[:, 1], "Z": nodes[:, 2]},
                connectivity,
                zoneType=ZoneType.FETETRAHEDRON,
                solutionTime=-1.0,
            )

        msg = "Strand ID must be an integer"
        with self.assertRaises(TypeError):
            TecplotFEZone(
                "TetGrid",
                {"X": nodes[:, 0], "Y": nodes[:, 1], "Z": nodes[:, 2]},
                connectivity,
                zoneType=ZoneType.FETETRAHEDRON,
                strandID="1",
            )

        msg = "Data values must be numpy arrays."
        with self.assertRaises(TypeError):
            TecplotFEZone(
                "TetGrid",
                {"X": nodes[:, 0].tolist(), "Y": nodes[:, 1].tolist(), "Z": nodes[:, 2].tolist()},
                connectivity,
                zoneType=ZoneType.FETETRAHEDRON,
            )

        msg = "Data must be a dictionary."
        with self.assertRaises(TypeError):
            TecplotFEZone("TetGrid", nodes, connectivity, zoneType=ZoneType.FETETRAHEDRON)

        msg = "All variables must have the same shape."
        with self.assertRaises(ValueError):
            TecplotFEZone(
                "TetGrid",
                {"X": nodes[:, 0], "Y": nodes[:, 1], "Z": nodes[:-1, 2]},
                connectivity,
                zoneType=ZoneType.FETETRAHEDRON,
            )

        msg = "Connectivity shape does not match zone type."
        with self.assertRaises(AssertionError):
            TecplotFEZone(
                "TetGrid",
                {"X": nodes[:, 0], "Y": nodes[:, 1], "Z": nodes[:, 2]},
                connectivity,
                zoneType=ZoneType.FETRIANGLE,
            )

    @parameterized.expand(
        TEST_CASES_ORDERED,
        name_func=lambda f, n, p: parameterized.to_safe_name(f"{f.__name__}_{p[0]}"),
    )
    def test_ReadWriteOrderedZones(
        self, shape: Tuple[int, ...], precision: str, datapacking: str, ext: str, separator: Separator
    ):
        zones: List[TecplotOrderedZone] = []

        if len(shape) == 1:
            X = np.linspace(0, 1, shape[0])
            Y = np.zeros_like(X)
            Z = np.zeros_like(X)
        elif len(shape) == 2:
            x = np.linspace(0, 1, shape[0])
            y = np.linspace(0, 1, shape[1])

            X, Y = np.meshgrid(x, y)
            Z = np.zeros_like(X)
        elif len(shape) == 3:
            x = np.linspace(0, 1, shape[0])
            y = np.linspace(0, 1, shape[1])
            z = np.linspace(0, 1, shape[2])

            X, Y, Z = np.meshgrid(x, y, z, indexing="ij")

        zone = TecplotOrderedZone("Grid", {"X": X, "Y": Y, "Z": Z})
        zones.append(zone)

        title = "ASCII ORDERED ZONES TEST"
        prefix = f"ORDERED_{shape}_{precision}_{datapacking}_"
        with tempfile.NamedTemporaryFile(suffix=ext, delete=not SAVE_TEMPFILES, dir=SAVE_DIR, prefix=prefix) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, datapacking=datapacking, precision=precision, separator=separator)
            titleRead, zonesRead = readTecplot(tmpfile.name)

            if ext == ".dat":
                with open(tmpfile.name, "r") as f:
                    lines = f.readlines()

                for line in lines:
                    self.assertTrue(len(line) <= 4000)

        self.assertEqual(titleRead, title)
        self.assertOrderedZonesEqual(zones, zonesRead)

    @parameterized.expand(
        TEST_CASES_FE,
        name_func=lambda f, n, p: parameterized.to_safe_name(f"{f.__name__}_{p[0]}"),
    )
    def test_ReadWriteFEZones(
        self, zoneType: ZoneType, precision: str, datapacking: str, ext: str, separator: Separator
    ):
        zones: List[TecplotFEZone] = []

        if zoneType == ZoneType.FELINESEG:
            rawDataList = [createLineSegGrid(nx) for nx in range(2, 10)]
        elif zoneType == ZoneType.FETRIANGLE:
            rawDataList = [createTriGrid(nx, ny) for nx, ny in product(range(2, 10), range(2, 10))]
        elif zoneType == ZoneType.FEQUADRILATERAL:
            rawDataList = [createQuadGrid(nx, ny) for nx, ny in product(range(2, 10), range(2, 10))]
        elif zoneType == ZoneType.FETETRAHEDRON:
            rawDataList = [createTetGrid(nx, ny, nz) for nx, ny, nz in zip(range(2, 10), range(2, 10), range(2, 10))]
        elif zoneType == ZoneType.FEBRICK:
            rawDataList = [createBrickGrid(nx, ny, nz) for nx, ny, nz in zip(range(2, 10), range(2, 10), range(2, 10))]

        for i, (nodes, connectivity) in enumerate(rawDataList):
            zone = TecplotFEZone(
                f"Grid_{i}_{nodes.shape}",
                {"X": nodes[..., 0], "Y": nodes[..., 1], "Z": nodes[..., 2]},
                connectivity,
                zoneType=zoneType,
            )
            zones.append(zone)

        title = f"ASCII {zoneType.name} ZONES TEST"
        prefix = f"{zoneType.name}_{precision}_{datapacking}_"
        with tempfile.NamedTemporaryFile(suffix=ext, delete=not SAVE_TEMPFILES, dir=SAVE_DIR, prefix=prefix) as tmpfile:
            writeTecplot(tmpfile.name, title, zones, datapacking=datapacking, precision=precision, separator=separator)
            titleRead, zonesRead = readTecplot(tmpfile.name)

            if ext == ".dat":
                with open(tmpfile.name, "r") as f:
                    lines = f.readlines()

                for line in lines:
                    self.assertTrue(len(line) <= 4000)

        self.assertEqual(titleRead, title)
        self.assertFEZonesEqual(zones, zonesRead)

    def test_ASCIIReadWriteExternal(self):
        try:
            title, zones = readTecplot(self.externalFileAscii)
        except Exception as e:
            self.fail(f"Reading external ASCII file {self.externalFileAscii} failed with error: {e}")

    def test_BinaryReadWriteExternal(self):
        try:
            title, zones = readTecplot(self.externalFileBinary)
        except Exception as e:
            self.fail(f"Reading external binary file {self.externalFileBinary} failed with error: {e}")

    def test_TriToTriConn(self):
        # Create a fe ordered tri zone
        ni, nj = 10, 10
        nodes, connectivity = createTriGrid(ni, nj)
        zone = TecplotFEZone(
            "TriGrid", {"X": nodes[:, 0], "Y": nodes[:, 1]}, connectivity, zoneType=ZoneType.FETRIANGLE
        )

        triConn = zone.triConnectivity

        np.testing.assert_array_equal(triConn, zone.connectivity)

    def test_QuadToTriConn(self):
        # Create a fe ordered quad zone
        ni, nj = 10, 10
        nodes, connectivity = createQuadGrid(ni, nj)
        zone = TecplotFEZone(
            "QuadGrid", {"X": nodes[:, 0], "Y": nodes[:, 1]}, connectivity, zoneType=ZoneType.FEQUADRILATERAL
        )

        triConn = zone.triConnectivity

        self.assertEqual(triConn.shape, (zone.nElements * 2, 3))

    def test_TriConnBadZoneType(self):
        # Create an line seg zone
        ni = 10
        nodes, connectivity = createLineSegGrid(ni)
        zone = TecplotFEZone("LineSeg", {"X": nodes[:, 0], "Y": nodes[:, 1]}, connectivity, zoneType=ZoneType.FELINESEG)

        with self.assertRaises(TypeError):
            triConn = zone.triConnectivity

        # Create a tet zone
        ni, nj, nk = 10, 10, 10
        nodes, connectivity = createTetGrid(ni, nj, nk)
        zone = TecplotFEZone(
            "TetGrid",
            {"X": nodes[:, 0], "Y": nodes[:, 1], "Z": nodes[:, 2]},
            connectivity,
            zoneType=ZoneType.FETETRAHEDRON,
        )

        with self.assertRaises(TypeError):
            triConn = zone.triConnectivity

        # Create a brick zone
        ni, nj, nk = 10, 10, 10
        nodes, connectivity = createBrickGrid(ni, nj, nk)
        zone = TecplotFEZone(
            "BrickGrid",
            {"X": nodes[:, 0], "Y": nodes[:, 1], "Z": nodes[:, 2]},
            connectivity,
            zoneType=ZoneType.FEBRICK,
        )

        with self.assertRaises(TypeError):
            triConn = zone.triConnectivity
