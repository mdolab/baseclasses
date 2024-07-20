import re
import struct
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Generic, List, Literal, TextIO, Tuple, TypeVar, Union

import numpy as np
import numpy.typing as npt

T = TypeVar("T", bound="TecplotZone")


# ==============================================================================
# ENUMS
# ==============================================================================
class ZoneType(Enum):
    UNSET = -1
    ORDERED = 0
    FELINESEG = 1
    FETRIANGLE = 2
    FEQUADRILATERAL = 3
    FETETRAHEDRON = 4
    FEBRICK = 5


class DataPacking(Enum):
    BLOCK = 0
    POINT = 1


class VariableLocation(Enum):
    NODE = 0
    CELL_CENTER = 1
    NODE_AND_CELL_CENTER = 2


class DataPrecision(Enum):
    SINGLE = 6
    DOUBLE = 12


class BinaryDataPrecisionCodes(Enum):
    SINGLE = 1
    DOUBLE = 2


class DTypePrecision(Enum):
    SINGLE = np.float32
    DOUBLE = np.float64


class FileType(Enum):
    FULL = 0
    GRID = 1
    SOLUTION = 2


class SectionMarkers(Enum):
    ZONE = 299.0  # V11.2 marker
    DATA = 357.0


class BinaryFlags(Enum):
    NONE = -1
    FALSE = 0
    TRUE = 1


class StrandID(Enum):
    PENDING = -2
    STATIC = -1


# ==============================================================================
# DATA STRUCTURES
# ==============================================================================
class TecplotZone:
    """Base class for Tecplot zones."""

    def __init__(
        self,
        name: str,
        data: Dict[str, npt.NDArray],
        solutionTime: float = 0.0,
        strandID: int = -1,
    ):
        """Create a tecplot zone object.

        Parameters
        ----------
        name : str
            The name of the zone.
        data : Dict[str, npt.NDArray]
            A dictionary of variable names and their corresponding data.
        solutionTime : float, optional
            The solution time of the zone, by default 0.0
        strandID : int, optional
            The strand id of the zone, by default -1
        """
        self.name = name
        self.data = data
        self.solutionTime = solutionTime
        self.strandID = strandID
        self.zoneType: Union[str, ZoneType] = ZoneType.UNSET
        self._validateName()
        self._validateData()
        self._validateSolutionTime()
        self._validateStrandID()

    @property
    def variables(self) -> List[str]:
        return list(self.data.keys())

    @property
    def shape(self) -> Tuple[int, ...]:
        return self.data[self.variables[0]].shape

    @property
    def nNodes(self) -> int:
        return np.multiply.reduce(self.shape)

    def _validateName(self) -> None:
        """Check that the zone name is a valid string.

        Raises
        ------
        TypeError
            If the zone name is not a valid string.
        """
        if not isinstance(self.name, str):
            raise TypeError("Zone name must be a string.")

    def _validateData(self) -> None:
        """Check that the data is a valid dictionary and the values
        are numpy arrays that have the same shape.

        Raises
        ------
        TypeError
            If the data is not a dictionary or the values are not numpy arrays.
        ValueError
            If the variables do not have the same shape.
        """
        if not isinstance(self.data, dict):
            raise TypeError("Data must be a dictionary.")

        for val in self.data.values():
            if not isinstance(val, np.ndarray):
                raise TypeError("Data values must be numpy arrays.")

        if not all(self.data[var].shape == self.shape for var in self.variables):
            raise ValueError("All variables must have the same shape.")

    def _validateSolutionTime(self) -> None:
        """Check that the solution time is a valid float.

        Raises
        ------
        TypeError
            If the solution time is not a float.
        ValueError
            If the solution time is less than zero.
        """
        if not isinstance(self.solutionTime, float):
            raise TypeError("Solution time must be a float.")

        if self.solutionTime < 0.0:
            raise ValueError("Solution time must be greater than or equal to zero.")

    def _validateStrandID(self) -> None:
        """Check that the strand ID is a valid integer.

        Raises
        ------
        TypeError
            If the strand ID is not an integer.
        """
        if not isinstance(self.strandID, int):
            raise TypeError("Strand ID must be an integer.")


class TecplotOrderedZone(TecplotZone):
    """Tecplot ordered zone. These zones do not contain connectivity information
    because the data is ordered in an (i, j, k) grid.
    """

    def __init__(
        self,
        name: str,
        data: Dict[str, npt.NDArray],
        solutionTime: float = 0.0,
        strandID: int = -1,
    ):
        """To create a tecplot ordered zone object:

        .. code-block:: python

            # --- Example usage ---
            # Create the data
            nx, ny = 10, 10
            X = np.random.rand(nx, ny)
            Y = np.random.rand(nx, ny)

            # Create the zone
            zone = TecplotOrderedZone(
                "OrderedZone",
                {"X": X, "Y": Y},
                solutionTime=0.0,
                strandID=-1,
            )

        Parameters
        ----------
        name : str
            The name of the zone.
        data : Dict[str, npt.NDArray]
            A dictionary of variable names and their corresponding data.
        zoneType : Union[str, ZoneType], optional
            The type of the zone, by default ZoneType.ORDERED
        solutionTime : float, optional
            The solution time of the zone, by default 0.0
        strandID : int, optional
            The strand id of the zone, by default -1
        """
        super().__init__(name, data, solutionTime=solutionTime, strandID=strandID)
        self.zoneType = ZoneType.ORDERED

    @property
    def iMax(self) -> int:
        return self.shape[0]

    @property
    def jMax(self) -> int:
        return self.shape[1] if len(self.shape) > 1 else 1

    @property
    def kMax(self) -> int:
        return self.shape[2] if len(self.shape) > 2 else 1


class TecplotFEZone(TecplotZone):
    """Tecplot finite element zone. These zones contain connectivity information
    to describe the elements in the zone. The type of element is determined by the
    shape of the connectivity array and the ``tetrahedral`` flag. The connectivity
    array is 0-based.

    The following shapes correspond to the following element types, where n is the number of elements:

    - ``(n, 2)``: FELINESEG
    - ``(n, 3)``: FETRIANGLE
    - ``(n, 4)``, FEQUADRILATERAL
    - ``(n, 4)``, FETETRAHEDRON
    - ``(n, 8)``: FEBRICK
    """

    def __init__(
        self,
        zoneName: str,
        data: Dict[str, npt.NDArray],
        connectivity: npt.NDArray,
        zoneType: Union[str, ZoneType],
        solutionTime: float = 0.0,
        strandID: int = -1,
    ):
        """To create a tecplot finite element zone object:

        .. code-block:: python

            # --- Example usage ---
            # Create node coordinates
            x = np.linspace(0, 1, nx + 1)
            nodes = np.column_stack((x, x**2))

            # Create element connectivity
            connectivity = np.column_stack((np.arange(nx), np.arange(1, nx + 1)))

            # Create the zone
            zone = TecplotFEZone(
                "FEZone",
                {"x": nodes[:, 0], "y": nodes[:, 1]},
                connectivity,
                zoneType="FELINESEG",
                solutionTime=0.0,
                strandID=-1,
            )

        Parameters
        ----------
        zoneName : str
            The name of the zone.
        data : Dict[str, npt.NDArray]
            A dictionary of variable names and their corresponding data.
        connectivity : npt.NDArray
            The connectivity array that describes the elements in the zone.
        zoneType : Union[str, ZoneType]
            The type of the zone. Can be a string that matches an entry
            in the ZoneType enum or the ZoneType enum itself.
        solutionTime : float, optional
            The solution time of the zone, by default 0.0
        strandID : int, optional
            The strand id of the zone, by default -1
        """
        super().__init__(zoneName, data, solutionTime=solutionTime, strandID=strandID)
        self.connectivity = connectivity
        self.zoneType = zoneType
        self._validateZoneType()
        self._validateConnectivity()

    @property
    def nElements(self) -> int:
        return self.connectivity.shape[0]

    def _validateZoneType(self) -> None:
        supportedZones = [zone.name for zone in ZoneType if zone.name != "ORDERED"]
        if isinstance(self.zoneType, str):
            if self.zoneType.upper() not in supportedZones:
                raise ValueError("Invalid zone type.")
            self.zoneType = ZoneType[self.zoneType.upper()]
        elif isinstance(self.zoneType, ZoneType):
            if self.zoneType.name not in supportedZones:
                raise ValueError("Invalid zone type.")
        else:
            raise ValueError("Invalid zone type.")

    def _validateConnectivity(self) -> None:
        if self.zoneType == ZoneType.FELINESEG:
            assert self.connectivity.shape[1] == 2, "Connectivity shape does not match zone type."
        elif self.zoneType == ZoneType.FETRIANGLE:
            assert self.connectivity.shape[1] == 3, "Connectivity shape does not match zone type."
        elif self.zoneType == ZoneType.FEQUADRILATERAL:
            assert self.connectivity.shape[1] == 4, "Connectivity shape does not match zone type."
        elif self.zoneType == ZoneType.FETETRAHEDRON:
            assert self.connectivity.shape[1] == 4, "Connectivity shape does not match zone type."
        elif self.zoneType == ZoneType.FEBRICK:
            assert self.connectivity.shape[1] == 8, "Connectivity shape does not match zone type."
        else:
            # Prior validation step should ensure we don't reach this point
            # but raise an error just in case.
            raise TypeError("Invalid zone type.")


# ==============================================================================
# ASCII WRITERS
# ==============================================================================
class TecplotZoneWriterASCII(Generic[T], ABC):
    def __init__(
        self,
        zone: T,
        datapacking: Literal["BLOCK", "POINT"],
        precision: Literal["SINGLE", "DOUBLE"],
    ) -> None:
        """Abstract base class for writing Tecplot zones to ASCII files.

        Parameters
        ----------
        zone : T
            The Tecplot zone to write.
        datapacking : Literal["BLOCK", "POINT"]
            The data packing format. BLOCK is row-major, POINT is column-major.
        precision : Literal["SINGLE", "DOUBLE"]
            The floating point precision to write the data.
        """
        self.zone = zone
        self.datapacking = DataPacking[datapacking].name
        self.fmtPrecision = DataPrecision[precision].value

    @abstractmethod
    def writeHeader(self, handle: TextIO):
        pass

    @abstractmethod
    def writeFooter(self, handle: TextIO):
        pass

    def writeData(self, handle: TextIO):
        data = np.stack([self.zone.data[var] for var in self.zone.variables], axis=-1)

        if self.datapacking == "POINT":
            data = data.reshape(-1, len(self.zone.variables))
        else:
            data = data.reshape(-1, len(self.zone.variables)).T

        np.savetxt(handle, data, fmt=f"%.{self.fmtPrecision}E")


class TecplotOrderedZoneWriterASCII(TecplotZoneWriterASCII[TecplotOrderedZone]):
    def __init__(
        self,
        zone: TecplotOrderedZone,
        datapacking: Literal["BLOCK", "POINT"],
        precision: Literal["SINGLE", "DOUBLE"],
    ) -> None:
        """Writer for Tecplot ordered zones in ASCII format.

        Parameters
        ----------
        zone : TecplotOrderedZone
            The ordered zone to write.
        datapacking : Literal["BLOCK", "POINT"]
            The data packing format. BLOCK is row-major, POINT is column-major.
        precision : Literal["SINGLE", "DOUBLE"]
            The floating point precision to write the data.
        """
        super().__init__(zone, datapacking, precision)

    def writeHeader(self, handle: TextIO):
        """Write the zone header to the file.

        Parameters
        ----------
        handle : TextIO
            The file handle.
        """
        # Write the zone header
        zoneString = f'ZONE T="{self.zone.name}"'
        zoneString += f", I={self.zone.iMax}"

        if self.zone.jMax > 1:
            zoneString += f", J={self.zone.jMax}"

        if self.zone.kMax > 1:
            zoneString += f", K={self.zone.kMax}"

        # Write the strand ID and solution time
        if self.zone.strandID != StrandID.STATIC and self.zone.strandID != StrandID.PENDING:
            # ASCII format does not support the -1 or -2 strand IDs
            # So we only write the strand ID if it is not -1
            zoneString += f", STRANDID={self.zone.strandID}"

        zoneString += f", SOLUTIONTIME={self.zone.solutionTime}"
        zoneString += f", DATAPACKING={self.datapacking}\n"

        handle.write(zoneString)

    def writeFooter(self, handle: TextIO):
        """Write the zone footer to the file.

        Parameters
        ----------
        handle : TextIO
            The file handle.
        """
        handle.write("\n")


class TecplotFEZoneWriterASCII(TecplotZoneWriterASCII[TecplotFEZone]):
    def __init__(
        self,
        zone: TecplotFEZone,
        datapacking: Literal["BLOCK", "POINT"],
        precision: Literal["SINGLE", "DOUBLE"],
    ) -> None:
        """Writer for Tecplot finite element zones in ASCII format.

        Parameters
        ----------
        zone : TecplotFEZone
            The finite element zone to write.
        datapacking : Literal["BLOCK", "POINT"]
            The data packing format. BLOCK is row-major, POINT is column-major.
        precision : Literal["SINGLE", "DOUBLE"]
            The floating point precision to write the data.
        """
        super().__init__(zone, datapacking, precision)

    def writeHeader(self, handle: TextIO):
        """Write the zone header to the file.

        Parameters
        ----------
        handle : TextIO
            The file handle.
        """
        # Write the zone header
        zoneString = f'ZONE T="{self.zone.name}"'
        zoneString += f", DATAPACKING={self.datapacking}"

        # Write the node and element information
        zoneString += f", NODES={np.multiply.reduce(self.zone.shape):d}"
        zoneString += f", ELEMENTS={self.zone.nElements:d}"
        zoneString += f", ZONETYPE={self.zone.zoneType.name}"

        # Write the strand ID and solution time
        if self.zone.strandID != StrandID.STATIC and self.zone.strandID != StrandID.PENDING:
            # ASCII format does not support the -1 or -2 strand IDs
            # So we only write the strand ID if it is not -1
            zoneString += f", STRANDID={self.zone.strandID}"

        zoneString += f", SOLUTIONTIME={self.zone.solutionTime}\n"

        handle.write(zoneString)

    def writeFooter(self, handle: TextIO):
        """Write the zone footer to the file. This includes the connectivity information.

        Parameters
        ----------
        handle : TextIO
            The file handle.
        """
        connectivity = self.zone.connectivity + 1
        # Get the max characters in the connectivity
        maxChars = len(str(connectivity.max()))

        np.savetxt(handle, connectivity, fmt=f"%{maxChars}d")

        handle.write("\n")


class TecplotWriterASCII:
    def __init__(
        self,
        title: str,
        zones: List[TecplotZone],
        datapacking: Literal["BLOCK", "POINT"],
        precision: Literal["SINGLE", "DOUBLE"],
    ) -> None:
        """Writer for Tecplot files in ASCII format.

        Parameters
        ----------
        title : str
            The title of the Tecplot file.
        zones : List[TecplotZone]
            A list of Tecplot zones to write.
        datapacking : Literal["BLOCK", "POINT"]
            The data packing format. BLOCK is row-major, POINT is column-major.
        precision : Literal["SINGLE", "DOUBLE"]
            The floating point precision to write the data.
        """
        self.title = title
        self.zones = zones
        self.datapacking = DataPacking[datapacking].name
        self.precision = DataPrecision[precision].name
        self._validateVariables()

    def _validateVariables(self) -> None:
        """Check that all zones have the same variables."""
        if not all(set(self.zones[0].variables) == set(zone.variables) for zone in self.zones):
            raise ValueError("All zones must have the same variables.")

    def _writeVariables(self, handle: TextIO) -> None:
        """Write the variable names to the file.

        Parameters
        ----------
        handle : TextIO
            The file handle.
        """
        variables = [f'"{var}"' for var in self.zones[0].variables]
        variableString = ", ".join(variables)
        handle.write(f"VARIABLES = {variableString}\n")

    def _writeZone(self, handle: TextIO, zone: TecplotZone) -> None:
        """Write a Tecplot zone to the file.

        Parameters
        ----------
        handle : TextIO
            The file handle.
        zone : TecplotZone
            The zone to write.

        Raises
        ------
        ValueError
            If the zone type is invalid.
        """
        if isinstance(zone, TecplotOrderedZone):
            writer = TecplotOrderedZoneWriterASCII(zone, self.datapacking, self.precision)
        elif isinstance(zone, TecplotFEZone):
            writer = TecplotFEZoneWriterASCII(zone, self.datapacking, self.precision)
        else:
            raise ValueError("Invalid zone type.")

        writer.writeHeader(handle)
        writer.writeData(handle)
        writer.writeFooter(handle)

    def write(self, filename: Union[str, Path]) -> None:
        """Write the Tecplot file to disk.

        Parameters
        ----------
        filename : Union[str, Path]
            The filename as a string or pathlib.Path object.
        """
        with open(filename, "w") as handle:
            handle.write(f'TITLE = "{self.title}"\n')
            self._writeVariables(handle)
            for zone in self.zones:
                self._writeZone(handle, zone)


# ==============================================================================
# BINARY WRITERS
# ==============================================================================
def _writeInteger(handle: TextIO, value: int) -> None:
    """Write an integer to a binary file as int32.

    Parameters
    ----------
    handle : TextIO
        The file handle to write to.
    value : int
        Integer value to write.
    """
    handle.write(struct.pack("i", value))


def _writeFloat32(handle: TextIO, value: float) -> None:
    """Write a float to a binary file as float32.

    Parameters
    ----------
    handle : TextIO
        The file handle to write to.
    value : float
        Float value to write.
    """
    handle.write(struct.pack("f", value))


def _writeFloat64(handle: TextIO, value: float) -> None:
    """Write a float to a binary file as float64.

    Parameters
    ----------
    handle : TextIO
        The file handle to write to.
    value : float
        Float value to write.
    """
    handle.write(struct.pack("d", value))


def _writeString(handle: TextIO, value: str) -> None:
    """Write a string to a binary file as a string.

    Parameters
    ----------
    handle : TextIO
        The file handle to write to.
    value : str
        String value to write.
    """
    for char in value:
        asciiValue = ord(char)
        handle.write(struct.pack("i", asciiValue))

    handle.write(struct.pack("i", 0))


class TecplotZoneWriterBinary(Generic[T], ABC):
    def __init__(
        self,
        title: str,
        zone: T,
        precision: Literal["SINGLE", "DOUBLE"],
    ) -> None:
        """Abstract base class for writing Tecplot zones to binary files.

        Parameters
        ----------
        title : str
            The title of the Tecplot file.
        zone : T
            The Tecplot zone to write.
        precision : Literal["SINGLE", "DOUBLE"]
            The floating point precision to write the data.
        """
        self.title = title
        self.zone = zone
        self.datapacking = "BLOCK"
        self.precision = DataPrecision[precision].name

    def _writeCommonHeader(self, handle: TextIO) -> None:
        """Write the common header information for all zones.

        Parameters
        ----------
        handle : TextIO
            The file handle.
        """
        # Write the zone marker
        _writeFloat32(handle, SectionMarkers.ZONE.value)  # Write the zone marker
        _writeString(handle, self.zone.name)  # Write the zone name
        _writeInteger(handle, BinaryFlags.NONE.value)  # Write the parent zone
        _writeInteger(handle, self.zone.strandID)  # Write the strand ID
        _writeFloat64(handle, self.zone.solutionTime)  # Write the solution time
        _writeInteger(handle, BinaryFlags.NONE.value)  # Write the default color
        _writeInteger(handle, self.zone.zoneType.value)  # Write the zone type
        _writeInteger(handle, DataPacking.BLOCK.value)  # Data Packing (Always block for binary)
        _writeInteger(handle, VariableLocation.NODE.value)  # Specify the variable location
        _writeInteger(handle, BinaryFlags.FALSE.value)  # Are raw 1-1 face neighbors supplied

    @abstractmethod
    def writeHeader(self, handle: TextIO):
        pass

    def writeData(self, handle: TextIO):
        """Write the zone data to the file.

        Parameters
        ----------
        handle : TextIO
            The file handle.
        """
        # Get the data into a single array
        data = np.stack([self.zone.data[var] for var in self.zone.variables], axis=-1)

        # Flatten the data such that each variable is a row
        data = data.reshape(-1, len(self.zone.variables)).T

        _writeFloat32(handle, SectionMarkers.ZONE.value)  # Write the zone marker

        # Write the variable data format for each variable
        for _ in range(len(self.zone.variables)):
            _writeInteger(handle, BinaryDataPrecisionCodes[self.precision].value)

        _writeInteger(handle, BinaryFlags.FALSE.value)  # No passive variables
        _writeInteger(handle, BinaryFlags.FALSE.value)  # No variable sharing
        _writeInteger(handle, BinaryFlags.NONE.value)  # No connectivity sharing

        # Write the min/max values for the variables
        for i in range(len(self.zone.variables)):
            _writeFloat64(handle, data[i, ...].min())
            _writeFloat64(handle, data[i, ...].max())

        # Write the data using the specified data format (single or double)
        data.astype(DTypePrecision[self.precision].value).tofile(handle)

    @abstractmethod
    def writeFooter(self, handle: TextIO):
        pass


class TecplotOrderedZoneWriterBinary(TecplotZoneWriterBinary[TecplotOrderedZone]):
    def __init__(
        self,
        title: str,
        zone: TecplotOrderedZone,
        precision: Literal["SINGLE", "DOUBLE"],
    ) -> None:
        """Writer for Tecplot ordered zones in binary format.

        Parameters
        ----------
        title : str
            The title of the Tecplot file.
        zone : TecplotOrderedZone
            The ordered zone to write.
        precision : Literal["SINGLE", "DOUBLE"]
            The floating point precision to write the data.
        """
        super().__init__(title, zone, precision)

    def writeHeader(self, handle: TextIO):
        """Write the zone header to the file.

        Parameters
        ----------
        handle : TextIO
            The file handle.
        """
        self._writeCommonHeader(handle)  # Write the common header information

        # --- Specific to Ordered Zones ---
        _writeInteger(handle, self.zone.iMax)  # Write the I dimension
        _writeInteger(handle, self.zone.jMax)  # Write the J dimension
        _writeInteger(handle, self.zone.kMax)  # Write the K dimension
        _writeInteger(handle, BinaryFlags.FALSE.value)  # No aux data

    def writeFooter(self, handle: TextIO):
        """Write the zone footer to the file. This is not used for ordered zones.

        Parameters
        ----------
        handle : TextIO
            The file handle.
        """
        pass


class TecplotFEZoneWriterBinary(TecplotZoneWriterBinary[TecplotFEZone]):
    def __init__(
        self,
        title: str,
        zone: TecplotFEZone,
        precision: Literal["SINGLE", "DOUBLE"],
    ) -> None:
        """Writer for Tecplot finite element zones in binary format.

        Parameters
        ----------
        title : str
            The title of the Tecplot file.
        zone : TecplotFEZone
            The finite element zone to write.
        precision : Literal["SINGLE", "DOUBLE"]
            The floating point precision to write the data.
        """
        super().__init__(title, zone, precision)

    def writeHeader(self, handle: TextIO):
        """Write the zone header to the file.

        Parameters
        ----------
        handle : TextIO
            The file handle.
        """
        self._writeCommonHeader(handle)  # Write the common header information

        # --- Specific to FE Zones ---
        _writeInteger(handle, self.zone.nNodes)  # Write the number of nodes
        _writeInteger(handle, self.zone.nElements)  # Write the number of elements
        _writeInteger(handle, 0)  # iCellDim (future use, set to 0)
        _writeInteger(handle, 0)  # jCellDim (future use, set to 0)
        _writeInteger(handle, 0)  # kCellDim (future use, set to 0)
        _writeInteger(handle, BinaryFlags.FALSE.value)  # No aux data

    def writeFooter(self, handle: TextIO):
        """Write the zone footer to the file. This includes the connectivity information.

        Parameters
        ----------
        handle : TextIO
            The file handle.
        """
        self.zone.connectivity.astype("int32").tofile(handle)


class TecplotWriterBinary:
    def __init__(
        self,
        title: str,
        zones: List[TecplotZone],
        precision: Literal["SINGLE", "DOUBLE"],
    ) -> None:
        """Writer for Tecplot files in binary format.

        This writer only supports files formatted using the format
        designated by magic number ``#!TDV112``.

        See the Tecplot 360 User's Manual for more information on the
        binary file format and the magic number.

        Parameters
        ----------
        title : str
            The title of the Tecplot file.
        zones : List[TecplotZone]
            A list of Tecplot zones to write.
        precision : Literal["SINGLE", "DOUBLE"]
            The floating point precision to write the data.
        """
        self._magicNumber = b"#!TDV112"
        self.title = title
        self.zones = zones
        self.precision = precision
        self._checkVariables()

    def _checkVariables(self) -> None:
        """Check that all zones have the same variables."""
        if not all(set(self.zones[0].variables) == set(zone.variables) for zone in self.zones):
            raise ValueError("All zones must have the same variables.")

    def _getZoneWriter(self, zone: TecplotZone) -> TecplotZoneWriterBinary:
        """Get the appropriate zone writer based on the zone type.

        Parameters
        ----------
        zone : TecplotZone
            The Tecplot zone to write.

        Returns
        -------
        TecplotZoneWriterBinary
            The appropriate zone writer object.

        Raises
        ------
        ValueError
            If the zone type is invalid.
        """
        if isinstance(zone, TecplotOrderedZone):
            return TecplotOrderedZoneWriterBinary(self.title, zone, self.precision)
        elif isinstance(zone, TecplotFEZone):
            return TecplotFEZoneWriterBinary(self.title, zone, self.precision)
        else:
            raise ValueError("Invalid zone type.")

    def write(self, filename: Union[str, Path]) -> None:
        """Write the Tecplot file to disk.

        Parameters
        ----------
        filename : Union[str, Path]
            The filename as a string or pathlib.Path object.
        """
        with open(filename, "wb") as handle:
            handle.write(self._magicNumber)  # Magic number
            _writeInteger(handle, 1)  # Byte order
            _writeInteger(handle, FileType.FULL.value)  # Full filetype
            _writeString(handle, self.title)  # Write the title
            _writeInteger(handle, len(self.zones[0].variables))  # Write the number of variables

            for var in self.zones[0].variables:
                _writeString(handle, var)  # Write the variable names

            # Write the zone headers
            for zone in self.zones:
                writer = self._getZoneWriter(zone)
                writer.writeHeader(handle)

            # Write the data marker
            _writeFloat32(handle, SectionMarkers.DATA.value)

            # Write the data and footer for each zone
            for zone in self.zones:
                writer = self._getZoneWriter(zone)
                writer.writeData(handle)
                writer.writeFooter(handle)


# ==============================================================================
# ASCII READERS
# ==============================================================================
class TecplotASCIIReader:
    def __init__(self, filename: Union[str, Path]) -> None:
        """Reader for Tecplot files in ASCII format.

        Parameters
        ----------
        filename : Union[str, Path]
            The filename as a string or pathlib.Path object.
        """
        self.filename = filename

    def _readZoneHeader(self, lines: List[str], iCurrent: int) -> Tuple[Dict[str, Any], int]:
        """Read the zone header information from a line in a Tecplot file.

        Parameters
        ----------
        line : str
            The line containing the zone header information.

        Returns
        -------
        Dict[str, Any]
            A dictionary containing the parsed zone header information.
        """
        # Get all the header lines into a single string
        header = []

        # Loop until the line starts with a number which denotes the start of the data section
        exitPattern = re.compile(r"^\s*\d")
        while not exitPattern.match(lines[iCurrent]):
            header.append(lines[iCurrent].strip("\n"))
            iCurrent += 1

        # Join the header lines into a single string
        headerString = ", ".join(header)

        # Use regex to parse the header information
        zoneNameMatch = re.search(r'zone t\s*=\s*"(.+)"', headerString, re.IGNORECASE)
        zoneName = zoneNameMatch.group(1) if zoneNameMatch else None

        zoneTypeMatch = re.search(r"zonetype\s*=\s*(\w+)", headerString, re.IGNORECASE)
        zoneType = zoneTypeMatch.group(1) if zoneTypeMatch else "ORDERED"

        datapackingMatch = re.search(r"datapacking\s*=\s*(\w+)", headerString, re.IGNORECASE)
        datapacking = datapackingMatch.group(1) if datapackingMatch else None

        nNodesMatch = re.search(r"nodes\s*=\s*(\d+)", headerString, re.IGNORECASE)
        nNodes = int(nNodesMatch.group(1)) if nNodesMatch else None

        nElementsMatch = re.search(r"elements\s*=\s*(\d+)", headerString, re.IGNORECASE)
        nElements = int(nElementsMatch.group(1)) if nElementsMatch else None

        iMaxMatch = re.search(r"i\s*=\s*(\d+)", headerString, re.IGNORECASE)
        iMax = int(iMaxMatch.group(1)) if iMaxMatch else 1

        jMaxMatch = re.search(r"j\s*=\s*(\d+)", headerString, re.IGNORECASE)
        jMax = int(jMaxMatch.group(1)) if jMaxMatch else 1

        kMaxMatch = re.search(r"k\s*=\s*(\d+)", headerString, re.IGNORECASE)
        kMax = int(kMaxMatch.group(1)) if kMaxMatch else 1

        solutionTimeMatch = re.search(r"solutiontime\s*=\s*(\d+\.\d+)", headerString, re.IGNORECASE)
        solutionTime = float(solutionTimeMatch.group(1)) if solutionTimeMatch else 0.0

        strandIDMatch = re.search(r"strandid\s*=\s*(\d+)", headerString, re.IGNORECASE)
        strandID = int(strandIDMatch.group(1)) if strandIDMatch else -1

        headerDict = {
            "zoneName": zoneName,
            "zoneType": zoneType,
            "datapacking": datapacking,
            "nNodes": nNodes,
            "nElements": nElements,
            "iMax": iMax,
            "jMax": jMax,
            "kMax": kMax,
            "solutionTime": solutionTime,
            "strandID": strandID,
        }

        return headerDict, iCurrent

    def _readOrderedZoneData(
        self, iCurrent: int, variables: List[str], zoneHeaderDict: Dict[str, Any]
    ) -> Tuple[TecplotOrderedZone, int]:
        """Read the data for an ordered Tecplot zone.

        Parameters
        ----------
        iCurrent : int
            The current line number in the file.
        variables : List[str]
            The list of variable names.
        zoneHeaderDict : Dict[str, Any]
            The zone header information.

        Returns
        -------
        Tuple[TecplotOrderedZone, int]
            The ordered zone object and the number of lines read.
        """
        iMax = zoneHeaderDict["iMax"]
        jMax = zoneHeaderDict["jMax"]
        kMax = zoneHeaderDict["kMax"]
        nNodes = iMax * jMax * kMax
        shape = (iMax, jMax, kMax, len(variables))

        if zoneHeaderDict["datapacking"] == "POINT":
            # Point data is column-major
            nodalData = np.loadtxt(self.filename, skiprows=iCurrent, max_rows=nNodes, dtype=float)
            nodalData = nodalData.reshape(shape).squeeze()
            nodeOffset = nNodes
        else:
            # Block data is row-major
            nodalData = np.loadtxt(self.filename, skiprows=iCurrent, max_rows=len(variables), dtype=float)
            nodalData = nodalData.T.reshape(shape).squeeze()
            nodeOffset = len(variables)

        data = {var: nodalData[..., i] for i, var in enumerate(variables)}
        zone = TecplotOrderedZone(
            zoneHeaderDict["zoneName"],
            data,
            solutionTime=zoneHeaderDict["solutionTime"],
            strandID=zoneHeaderDict["strandID"],
        )

        return zone, nodeOffset

    def _readFEZoneData(
        self, iCurrent: int, variables: List[str], zoneHeaderDict: Dict[str, Any]
    ) -> Tuple[TecplotFEZone, int]:
        """Read the data for a finite element Tecplot zone.

        Parameters
        ----------
        iCurrent : int
            The current line number in the file.
        variables : List[str]
            The list of variable names.
        zoneHeaderDict : Dict[str, Any]
            The zone header information.

        Returns
        -------
        Tuple[TecplotFEZone, int]
            The finite element zone object and the number of lines read.
        """
        nNodes = zoneHeaderDict["nNodes"]
        nElements = zoneHeaderDict["nElements"]

        if zoneHeaderDict["datapacking"] == "POINT":
            # Point data is column-major
            nodalData = np.loadtxt(self.filename, skiprows=iCurrent, max_rows=nNodes, dtype=float)
            nodeOffset = nNodes
        else:
            # Block data is row-major
            nodalData = np.loadtxt(self.filename, skiprows=iCurrent, max_rows=len(variables), dtype=float)
            nodalData = np.atleast_2d(nodalData).T
            nodeOffset = len(variables)

        connectivity = np.loadtxt(self.filename, skiprows=iCurrent + nodeOffset, max_rows=nElements, dtype=int)

        # Check if the nodal data is 1D
        if nodalData.ndim == 1:
            nodalData = nodalData.reshape(-1, len(variables))

        data = {var: nodalData[..., i] for i, var in enumerate(variables)}
        zone = TecplotFEZone(
            zoneHeaderDict["zoneName"],
            data,
            connectivity - 1,
            zoneType=zoneHeaderDict["zoneType"],
            solutionTime=zoneHeaderDict["solutionTime"],
            strandID=zoneHeaderDict["strandID"],
        )

        return zone, nodeOffset + nElements

    def _readZoneData(self, lines: List[str], iLine: int, variables: List[str]) -> Tuple[TecplotZone, int]:
        """Read the data for a Tecplot zone.

        Parameters
        ----------
        lines : List[str]
            The list of lines in the Tecplot file.
        iLine : int
            The current line number in the file.
        variables : List[str]
            The list of variable names.

        Returns
        -------
        Tuple[TecplotZone, int]
            The Tecplot zone object and the number of lines read.
        """
        zoneHeaderDict, iLine = self._readZoneHeader(lines, iLine)

        if zoneHeaderDict["zoneType"] == "ORDERED":
            zone, iOffset = self._readOrderedZoneData(iLine, variables, zoneHeaderDict)
        else:
            zone, iOffset = self._readFEZoneData(iLine, variables, zoneHeaderDict)

        return zone, iLine + iOffset

    def read(self) -> Tuple[str, List[TecplotZone]]:
        """Read the Tecplot file and return the title and zones.

        Returns
        -------
        Tuple[str, List[TecplotZone]]
            The title of the Tecplot file and a list of Tecplot zones.

        Raises
        ------
        ValueError
            If the file is not a valid Tecplot file.
        ValueError
            If the title is missing.
        """
        with open(self.filename, "r") as handle:
            lines = handle.readlines()

        zones = []

        # Get the title
        title = re.search(r'title\s*=\s*"(.*)"', lines[0], re.IGNORECASE)
        if title is None:
            raise ValueError("Tecplot file must have a title on the first line.")
        title = title.group(1)

        # Get the variable names
        variables = re.findall(r'"([^"]*)"', lines[1])

        iLine = 2
        while iLine < len(lines):
            zone, iLine = self._readZoneData(lines, iLine, variables)
            zones.append(zone)

            # Skip any empty lines
            while iLine < len(lines) and not lines[iLine].strip():
                iLine += 1

        return title, zones


# ==============================================================================
# BINARY READERS
# ==============================================================================
class TecplotBinaryReader:
    def __init__(self, filename: Union[str, Path]) -> None:
        """Reader for Tecplot files in binary format.

        Parameters
        ----------
        filename : Union[str, Path]
            The filename as a string or pathlib.Path object
        """
        self.filename = filename
        self._nVariables = 0
        self._variables = []

    def _readString(self, handle: TextIO) -> str:
        """Read a string from a binary file that is null-terminated.

        Parameters
        ----------
        handle : TextIO
            The file handle to read from.

        Returns
        -------
        str
            The string read from the file.
        """
        result = []
        while True:
            data = handle.read(4)
            integer = struct.unpack_from("i", data, 0)[0]

            if integer == 0:
                break

            result.append(chr(integer))

        return "".join(result)

    def _readInteger(self, handle: TextIO, offset: int = 0) -> int:
        """Read an integer from a binary file as int32.

        Parameters
        ----------
        handle : TextIO
            The file handle to read from.
        offset : int, optional
            The offset (in bytes) from the file's current position, by default 0

        Returns
        -------
        int
            The integer read from the file.
        """
        return int(np.fromfile(handle, dtype=np.int32, count=1, offset=offset)[0])

    def _readIntegerArray(self, handle: TextIO, nValues: int, offset: int = 0) -> npt.NDArray[np.int32]:
        """Read an array of integers from a binary file as int32.

        Parameters
        ----------
        handle : TextIO
            The file handle to read from.
        nValues : int
            The number of values to read.
        offset : int, optional
            The offset (in bytes) from the file's current position, by default 0

        Returns
        -------
        npt.NDArray[np.int32]
            The integer array read from the file.
        """
        return np.fromfile(handle, dtype=np.int32, count=nValues, offset=offset)

    def _readFloat32(self, handle: TextIO, offset: int = 0) -> float:
        """Read a float from a binary file as float32.

        Parameters
        ----------
        handle : TextIO
            The file handle to read from.
        offset : int, optional
            The offset (in bytes) from the file's current position, by default 0

        Returns
        -------
        float
            The float read from the file.
        """
        return float(np.fromfile(handle, dtype=np.float32, count=1, offset=offset)[0])

    def _readFloat32Array(self, handle: TextIO, nValues: int, offset: int = 0) -> npt.NDArray[np.float32]:
        """Read an array of floats from a binary file as float32.

        Parameters
        ----------
        handle : TextIO
            The file handle to read from.
        nValues : int
            The number of values to read.
        offset : int, optional
            The offset (in bytes) from the file's current position, by default 0

        Returns
        -------
        npt.NDArray[np.float32]
            The float array read from the file.
        """
        return np.fromfile(handle, dtype=np.float32, count=nValues, offset=offset)

    def _readFloat64(self, handle: TextIO, offset: int = 0) -> float:
        """Read a float from a binary file as float64.

        Parameters
        ----------
        handle : TextIO
            The file handle to read from.
        offset : int, optional
            The offset (in bytes) from the file's current position, by default 0

        Returns
        -------
        float
            The float read from the file.
        """
        return float(np.fromfile(handle, dtype=np.float64, count=1, offset=offset)[0])

    def _readFloat64Array(self, handle: TextIO, nValues: int, offset: int = 0) -> npt.NDArray[np.float64]:
        """Read an array of floats from a binary file as float64.

        Parameters
        ----------
        handle : TextIO
            The file handle to read from.
        nValues : int
            The number of values to read.
        offset : int, optional
            The offset (in bytes) from the file's current position, by default 0

        Returns
        -------
        npt.NDArray[np.float64]
            The float array read from the file.
        """
        return np.fromfile(handle, dtype=np.float64, count=nValues, offset=offset)

    def _readOrderedZone(self, handle: TextIO, zoneName: str, strandID: int, solutionTime: float) -> TecplotOrderedZone:
        """Read an ordered Tecplot zone header from a binary file.

        Parameters
        ----------
        handle : TextIO
            The file handle to read from.
        zoneName : str
            The name of the zone.
        strandID : int
            The strand ID.
        solutionTime : float
            The solution time.

        Returns
        -------
        TecplotOrderedZone
            The ordered Tecplot zone object.
        """
        iMax = self._readInteger(handle)
        jMax = self._readInteger(handle)
        kMax = self._readInteger(handle)

        return TecplotOrderedZone(
            zoneName,
            {var: np.zeros((iMax, jMax, kMax)).squeeze() for _, var in enumerate(self._variables)},
            solutionTime=solutionTime,
            strandID=strandID,
        )

    def _readFEZone(
        self, handle: TextIO, zoneName: str, zoneType: int, strandID: int, solutionTime: float
    ) -> TecplotFEZone:
        """Read a finite element Tecplot zone header from a binary file.

        Parameters
        ----------
        handle : TextIO
            The file handle to read from.
        zoneName : str
            The name of the zone.
        zoneType : int
            The zone type.
        strandID : int
            The strand ID.
        solutionTime : float
            The solution time.

        Returns
        -------
        TecplotFEZone
            The finite element Tecplot zone object.

        Raises
        ------
        ValueError
            If the zone type is invalid.
        """
        nNodes = self._readInteger(handle)
        nElements = self._readInteger(handle)
        iCellDim = self._readInteger(handle)  # NOQA: F841
        jCellDim = self._readInteger(handle)  # NOQA: F841
        kCellDim = self._readInteger(handle)  # NOQA: F841

        if zoneType == ZoneType.FELINESEG.value:
            connectivity = np.zeros((nElements, 2), dtype=int)
        elif zoneType == ZoneType.FETRIANGLE.value:
            connectivity = np.zeros((nElements, 3), dtype=int)
        elif zoneType == ZoneType.FEQUADRILATERAL.value:
            connectivity = np.zeros((nElements, 4), dtype=int)
        elif zoneType == ZoneType.FETETRAHEDRON.value:
            connectivity = np.zeros((nElements, 4), dtype=int)
        elif zoneType == ZoneType.FEBRICK.value:
            connectivity = np.zeros((nElements, 8), dtype=int)
        else:
            raise ValueError("Invalid zone type.")

        return TecplotFEZone(
            zoneName,
            {var: np.zeros(nNodes) for _, var in enumerate(self._variables)},
            connectivity,
            zoneType=ZoneType(zoneType),
            solutionTime=solutionTime,
            strandID=strandID,
        )

    def _readZoneHeader(self, handle: TextIO) -> Union[TecplotOrderedZone, TecplotFEZone]:
        """Read a Tecplot zone header from a binary file.

        Parameters
        ----------
        handle : TextIO
            The file handle to read from.

        Returns
        -------
        Union[TecplotOrderedZone, TecplotFEZone]
            The Tecplot zone object, either ordered or finite element.
        """
        zoneName = self._readString(handle)
        parentZone = self._readInteger(handle)  # NOQA: F841
        strandID = self._readInteger(handle)
        solutionTime = self._readFloat64(handle)
        defaultColor = self._readInteger(handle)  # NOQA: F841
        zoneType = self._readInteger(handle)
        datapacking = self._readInteger(handle)  # NOQA: F841
        variableLocation = self._readInteger(handle)  # NOQA: F841
        rawFaceNeighbors = self._readInteger(handle)  # NOQA: F841

        if zoneType == ZoneType.ORDERED.value:
            zone = self._readOrderedZone(handle, zoneName, strandID, solutionTime)
        else:
            zone = self._readFEZone(handle, zoneName, zoneType, strandID, solutionTime)

        return zone

    def read(self) -> Tuple[str, List[TecplotZone]]:
        """Read the Tecplot file and return the title and zones.

        Returns
        -------
        Tuple[str, List[TecplotZone]]
            The title of the Tecplot file and a list of Tecplot zones.

        Raises
        ------
        ValueError
            If the file is not a valid Tecplot file.
        """
        file = open(self.filename, "rb")
        file.seek(0, 2)
        fileSize = file.tell()
        file.seek(0)

        magic = file.read(8).decode("utf-8")
        if magic != "#!TDV112":
            raise ValueError("Invalid Tecplot binary file version.")

        byteOrder = self._readInteger(file)  # NOQA: F841
        filetype = self._readInteger(file)  # NOQA: F841
        title = self._readString(file)
        self._nVariables = self._readInteger(file)
        self._variables = [self._readString(file) for _ in range(self._nVariables)]
        zones: List[Union[TecplotOrderedZone, TecplotFEZone]] = []

        # Read all the zone headers
        while True:
            marker = self._readFloat32(file)

            if marker == SectionMarkers.ZONE.value:
                # Initialize zone from the header
                zone = self._readZoneHeader(file)
                zones.append(zone)
            if marker == SectionMarkers.DATA.value:
                break

        # Read the data for each zone
        izone = 0
        while file.tell() < fileSize:
            zoneMarker = self._readFloat32(file)  # NOQA: F841
            dataFormats = [self._readInteger(file) for _ in range(self._nVariables)]
            passiveVariables = self._readInteger(file)  # NOQA: F841
            variableSharing = self._readInteger(file)  # NOQA: F841
            connSharing = self._readInteger(file)  # NOQA: F841
            minMaxArray = self._readFloat64Array(file, 2 * self._nVariables).reshape(self._nVariables, 2)  # NOQA: F841

            if isinstance(zones[izone], TecplotOrderedZone):
                iMax = zones[izone].iMax
                jMax = zones[izone].jMax
                kMax = zones[izone].kMax

                for i in range(self._nVariables):
                    if dataFormats[i] == BinaryDataPrecisionCodes.SINGLE.value:
                        readData = self._readFloat32Array(file, iMax * jMax * kMax).reshape(iMax, jMax, kMax).squeeze()
                    else:
                        readData = self._readFloat64Array(file, iMax * jMax * kMax).reshape(iMax, jMax, kMax).squeeze()

                    zones[izone].data[self._variables[i]][...] = readData

            if isinstance(zones[izone], TecplotFEZone):
                nNodes = zones[izone].nNodes
                nElements = zones[izone].nElements

                for i in range(self._nVariables):
                    if dataFormats[i] == BinaryDataPrecisionCodes.SINGLE.value:
                        readData = self._readFloat32Array(file, nNodes)
                    else:
                        readData = self._readFloat64Array(file, nNodes)

                    zones[izone].data[self._variables[i]][...] = readData

                connectivitySize = zones[izone].connectivity.size
                connectivity = self._readIntegerArray(file, connectivitySize).reshape(nElements, -1)
                zones[izone].connectivity = connectivity

            izone += 1

        file.close()

        return title, zones


# ==============================================================================
# PUBLIC FUNCTIONS
# ==============================================================================
def writeTecplot(
    filename: Union[str, Path],
    title: str,
    zones: List[TecplotZone],
    datapacking: Literal["BLOCK", "POINT"] = "POINT",
    precision: Literal["SINGLE", "DOUBLE"] = "SINGLE",
) -> None:
    """Write a Tecplot file to disk. The file format is determined by the
    file extension. If the extension is .plt, the file will be written in
    binary format. If the extension is .dat, the file will be written in
    ASCII format.

    .. note::

        - ASCII files can be written with either BLOCK or POINT data packing.
        - Binary files are always written with BLOCK data packing.

    Parameters
    ----------
    filename : Union[str, Path]
        The filename as a string or pathlib.Path object.
    title : str
        The title of the Tecplot file.
    zones : List[TecplotZone]
        A list of Tecplot zones to write
    datapacking : Literal["BLOCK", "POINT"], optional
        The data packing format. BLOCK is row-major, POINT is column-major, by default "POINT"
    precision : Literal["SINGLE", "DOUBLE"], optional
        The floating point precision to write the data, by default "SINGLE"

    Raises
    ------
    ValueError
        If the file extension is invalid.

    Examples
    --------
    .. code-block:: python

        from baseclasses.utils import TecplotOrderedZone, writeTecplot
        import numpy as np

        nx, ny, nz = 10, 10, 10
        X, Y, Z = np.meshgrid(np.random.rand(nx), np.random.rand(ny), np.random.rand(nz), indexing="ij")
        data = {"X": X, "Y": Y, "Z": Z}
        zone = TecplotOrderedZone("OrderedZone", data)

        # Write the Tecplot file in ASCII format
        writeTecplot("ordered.dat", "Ordered Zone", [zone], datapacking="BLOCK", precision="SINGLE")

        # Write the Tecplot file in binary format
        writeTecplot("ordered.plt", "Ordered Zone", [zone], precision="SINGLE")

    """
    filepath = Path(filename)
    if filepath.suffix == ".plt":
        writer = TecplotWriterBinary(title, zones, precision)
        writer.write(filepath)
    elif filepath.suffix == ".dat":
        writer = TecplotWriterASCII(title, zones, datapacking, precision)
        writer.write(filename)
    else:
        raise ValueError("Invalid file extension. Must be .plt (binary) or .dat (ASCII).")


def readTecplot(filename: Union[str, Path]) -> Tuple[str, List[Union[TecplotOrderedZone, TecplotFEZone]]]:
    """Read a Tecplot file from disk. The file format is determined by the
    file extension. If the extension is .plt, the file will be read in
    binary format. If the extension is .dat, the file will be read in
    ASCII format.

    Parameters
    ----------
    filename : Union[str, Path]
        The filename as a string or pathlib.Path object.

    Returns
    -------
    Tuple[str, List[Union[TecplotOrderedZone, TecplotFEZone]]]
        The title of the Tecplot file and a list of Tecplot zones.

    Raises
    ------
    ValueError
        If the file extension is invalid.

    Examples
    --------
    .. code-block:: python

        from baseclasses.utils import readTecplot

        # Read a Tecplot file in ASCII format
        title, zones = readTecplot("ordered.dat")

        # Read a Tecplot file in binary format
        title, zones = readTecplot("ordered.plt")
    """
    filepath = Path(filename)
    if filepath.suffix == ".plt":
        reader = TecplotBinaryReader(filename)
        title, zones = reader.read()
    elif filepath.suffix == ".dat":
        reader = TecplotASCIIReader(filename)
        title, zones = reader.read()
    else:
        raise ValueError("Invalid file extension. Must be .plt (binary) or .dat (ASCII).")

    return title, zones
