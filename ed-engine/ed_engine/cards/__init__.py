from __future__ import annotations

from typing import Callable, Type

from ed_engine.models.card import Card

_registry: dict[str, Type[Card]] = {}


class CardRegistry:
    @staticmethod
    def get(name: str) -> Type[Card] | None:
        return _registry.get(name)

    @staticmethod
    def all() -> dict[str, Type[Card]]:
        return dict(_registry)


def register(cls: Type[Card]) -> Type[Card]:
    """Decorator to register a card class by its name field default."""
    name = cls.model_fields["name"].default
    if name is None:
        raise ValueError(f"Card class {cls.__name__} must define a default name")
    _registry[name] = cls
    return cls
