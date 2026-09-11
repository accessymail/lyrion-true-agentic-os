"""Linux enforcement primitive adapters."""

from lyrion.execution.backends.linux.enforcement.primitives.no_new_privs import (
    PR_GET_NO_NEW_PRIVS,
    PR_SET_NO_NEW_PRIVS,
    LibcNoNewPrivsOperations,
    NoNewPrivsAdapter,
    NoNewPrivsOperations,
)

__all__ = [
    "LibcNoNewPrivsOperations",
    "NoNewPrivsAdapter",
    "NoNewPrivsOperations",
    "PR_GET_NO_NEW_PRIVS",
    "PR_SET_NO_NEW_PRIVS",
]
