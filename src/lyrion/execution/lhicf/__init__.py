"""LYRION Host Integration & Control Fabric (LHICF).

This package is a controlled boundary over already-authorized execution
context and existing host-observation primitives.

LHICF does not authorize, grant capabilities, execute arbitrary commands,
weaken sandbox controls, or replace Linux enforcement.
"""

from .boundary import LHICFBoundaryValidator
from .contracts import (
    AdapterLifecycleState,
    AdapterRegistration,
    BoundaryStatus,
    LHICFRequest,
    LHICFResult,
)
from .registry import AdapterRegistry, AdapterSelectionError

__all__ = [
    "AdapterLifecycleState",
    "AdapterRegistration",
    "AdapterRegistry",
    "AdapterSelectionError",
    "BoundaryStatus",
    "LHICFBoundaryValidator",
    "LHICFRequest",
    "LHICFResult",
]
