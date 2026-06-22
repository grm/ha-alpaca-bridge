"""Server transaction ID management."""

from __future__ import annotations

import itertools
import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class TransactionContext:
    client_id: int
    client_transaction_id: int


class TransactionManager:
    """Generate monotonically increasing server transaction IDs."""

    def __init__(self) -> None:
        self._counter = itertools.count(1)
        self._lock = threading.Lock()

    def next_server_transaction_id(self) -> int:
        with self._lock:
            return next(self._counter)
