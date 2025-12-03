from __future__ import annotations

from abc import ABC, abstractmethod


class IUnitOfWork(ABC):
    """
    Interface to coordinate transactions across repositories.
    """

    @abstractmethod
    def __enter__(self) -> "IUnitOfWork":
        """
        Enter the unit of work context.

        Returns:
            IUnitOfWork: The current unit of work instance.
        """
        raise NotImplementedError()

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the unit of work context, committing or rolling back.

        Args:
            exc_type: Exception type if raised inside the context.
            exc_val: Exception value.
            exc_tb: Traceback.
        """
        raise NotImplementedError()

    @abstractmethod
    def commit(self) -> None:
        """
        Commit the current transaction.
        """
        raise NotImplementedError()

    @abstractmethod
    def rollback(self) -> None:
        """
        Roll back the current transaction.
        """
        raise NotImplementedError()
