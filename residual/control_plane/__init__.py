"""RESIDUAL gateway/control-plane primitives (SPEC-GCP-001)."""
from .models import *
from .policy import AuthorityPolicy, AmendmentPolicy, RoutingPolicy
from .transactions import SideEffectTransaction
