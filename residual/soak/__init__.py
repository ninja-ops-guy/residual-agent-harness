"""Track Q — Production soak test harness.

Implements SPEC-NINE-002 requirements:

- N9-R9: continuous soak execution with a configurable load generator
  (>= 1000 tasks/day supported), synthetic NetOps/SecOps operational
  tasks, intentional failures (bad configs, missing dependencies) and
  adversarial inputs.
- N9-R10: SoakTestReport with totals (executed/accepted/rejected/
  escalated), unhandled-exception accounting (any exception = failure),
  cache hit rate (target >= 60%), token savings (target >= 40%),
  brake FP rate (<= 5%), brake FN rate (<= 1%), HITL escalation rate
  (<= 10%), and mean time to recovery (MTTR) from intentional failures.
- N9-R11: the report is cryptographically signed (HMAC-SHA256) with the
  Station identity key, suitable for publication as evidence.
- N9-R12: at least one red team exercise (quarantine bypass, receipt
  forgery, unsafe execution, exfiltration); every attempt produces a
  receipt; the report documents blocked vs succeeded.

Soak state is persisted after every day so an interrupted soak resumes
deterministically (see ``state.py``).
"""

from .tasks import NETOPS_TEMPLATES, SECOPS_TEMPLATES, SyntheticTask, make_task
from .loadgen import LoadGenerator
from .failure_injection import FailureInjector, InjectionMix
from .metrics import SoakMetrics, SOAK_TARGETS
from .report import SoakTestReport, sign_report, verify_report
from .state import SoakState
from .harness import SoakConfig, SoakHarness
from .redteam import RedTeamExercise, RedTeamAttempt

__all__ = [
    "FailureInjector",
    "InjectionMix",
    "LoadGenerator",
    "NETOPS_TEMPLATES",
    "RedTeamAttempt",
    "RedTeamExercise",
    "SECOPS_TEMPLATES",
    "SOAK_TARGETS",
    "SoakConfig",
    "SoakHarness",
    "SoakMetrics",
    "SoakState",
    "SoakTestReport",
    "SyntheticTask",
    "make_task",
    "sign_report",
    "verify_report",
]
