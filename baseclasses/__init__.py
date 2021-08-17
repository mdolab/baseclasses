__version__ = "1.5.2"

from .problems.pyAero_problem import AeroProblem
from .problems.pyTransi_problem import TransiProblem
from .problems.pyStruct_problem import StructProblem
from .problems.pyAeroStruct_problem import AeroStructProblem
from .problems.pyMission_problem import MissionProblem, MissionProfile, MissionSegment
from .problems.pyWeight_problem import WeightProblem, FuelCase
from .problems.FluidProperties import FluidProperties
from .problems.ICAOAtmosphere import ICAOAtmosphere
from .problems.pyEngine_problem import EngineProblem
from .problems.pyFieldPerformance_problem import FieldPerformanceProblem
from .problems.pyLG_problem import LGProblem

from .solvers.pyAero_solver import AeroSolver
from .solvers.BaseSolver import BaseSolver

from .utils.py3Util import getPy3SafeString

from .testing.BaseRegTest import BaseRegTest
