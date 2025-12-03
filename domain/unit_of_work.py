from __future__ import annotations

from abc import ABC, abstractmethod


class IUnitOfWork(ABC):
    """
    Interface to coordinate transactions across repositories.
    """

    @abstractmethod
    def __enter__(self) -> "IUnitOfWork":
        raise NotImplementedError()

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        raise NotImplementedError()

    @abstractmethod
    def commit(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    def rollback(self) -> None:
        raise NotImplementedError()
