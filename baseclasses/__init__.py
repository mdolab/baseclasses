__version__ = "1.7.0"

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

from .testing import BaseRegTest, getTol
