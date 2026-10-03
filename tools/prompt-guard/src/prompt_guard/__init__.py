"""Policy inspection of untrusted prompt data."""
from .core import GuardError, GuardResult, inspect, policy_from_dict
from .files import load_policy
from .profiles import load_profile

__all__ = ["GuardError", "GuardResult", "inspect", "policy_from_dict", "load_policy", "load_profile"]
__version__ = "0.2.0"
