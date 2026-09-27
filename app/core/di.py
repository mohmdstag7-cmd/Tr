"""Minimal service container (no framework)."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class Container:
    """Tiny DI container with singleton caching."""

    def __init__(self) -> None:
        self._factories: dict[type[object], Callable[[], object]] = {}
        self._instances: dict[type[object], object] = {}

    def register(self, interface: type[T], factory: Callable[[], T]) -> None:
        """Register a factory for an interface. Clears cached instance if present."""
        self._factories[interface] = factory  # type: ignore[assignment]
        if interface in self._instances:
            del self._instances[interface]

    def resolve(self, interface: type[T]) -> T:
        """Resolve an interface, creating and caching the singleton instance."""
        if interface in self._instances:
            return self._instances[interface]  # type: ignore[return-value]
        factory = self._factories.get(interface)
        if factory is None:
            msg = f"No registration for {interface!r}"
            raise KeyError(msg)
        instance = factory()
        self._instances[interface] = instance
        return instance  # type: ignore[return-value]

    def singleton(self, instance: object) -> None:
        """Register a pre-built singleton instance by its concrete type."""
        self._instances[type(instance)] = instance

    def reset(self) -> None:
        """Clear all registrations and cached instances (for tests)."""
        self._factories.clear()
        self._instances.clear()


container = Container()
