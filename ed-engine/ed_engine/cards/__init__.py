from __future__ import annotations

from typing import Type

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


def get_card_definition(name: str) -> Card:
    """Return a fresh Card instance for the given card name.

    Raises KeyError if the name is not in the registry.
    """
    cls = _registry.get(name)
    if cls is None:
        raise KeyError(f"Unknown card: {name!r}")
    return cls()


def build_deck() -> list[Card]:
    """Build the full 128-card Everdell deck.

    Each registered card class contributes `copies_in_deck` instances.
    """
    # Force-import card modules so all @register decorators fire.
    import ed_engine.cards.constructions  # noqa: F401
    import ed_engine.cards.critters  # noqa: F401

    deck: list[Card] = []
    for cls in _registry.values():
        instance = cls()
        for _ in range(instance.copies_in_deck):
            deck.append(cls())
    return deck
