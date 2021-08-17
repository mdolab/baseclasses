__version__ = "1.5.2"

from .problems import (
    AeroProblem,
    TransiProblem,
    StructProblem,
    AeroStructProblem,
    MissionProblem,
    MissionProfile,
    MissionSegment,
    WeightProblem,
    FuelCase,
    FluidProperties,
    ICAOAtmosphere,
    EngineProblem,
    FieldPerformanceProblem,
    LGProblem,
)

from .solvers import BaseSolver, AeroSolver

from .utils import getPy3SafeString

from .testing import BaseRegTest
from .testing import require_mpi
