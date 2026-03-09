"""Special rules — complex card interactions spanning multiple systems."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ed_engine.models.enums import CardCategory, Season
from ed_engine.models.resources import ResourceBank

if TYPE_CHECKING:
    from ed_engine.models.card import Card
    from ed_engine.models.game import GameState
    from ed_engine.models.player import Player


class SpecialRules:
    """Handles complex card interactions that span multiple systems."""

    # Cards that unlock a second permanent-worker slot on a destination
    _SECOND_SLOT_UNLOCKERS: dict[str, str] = {
        "Cemetery": "Undertaker",
        "Monastery": "Monk",
        "Dungeon": "Ranger",
    }

    @staticmethod
    def handle_haven(player: Player, cards_to_discard: list[Card]) -> ResourceBank:
        """Haven: discard any number of cards from hand, gain 1 any resource
        per 2 cards discarded.

        The caller chooses which resource(s) to gain; here we return the
        *maximum* resources the player is entitled to.  Actual resource
        selection is left to the action layer.

        Returns a ResourceBank representing the number of "any resource"
        tokens earned (encoded as total()).
        """
        if not cards_to_discard:
            return ResourceBank()

        # Remove cards from hand
        hand_names = [c.name for c in player.hand]
        for card in cards_to_discard:
            if card.name not in hand_names:
                raise ValueError(f"Card {card.name} not in player's hand")
            hand_names.remove(card.name)

        # Actually remove from hand
        remaining = list(player.hand)
        for card in cards_to_discard:
            for i, h in enumerate(remaining):
                if h.name == card.name:
                    remaining.pop(i)
                    break
        player.hand = remaining

        resources_earned = len(cards_to_discard) // 2
        # Return a bank with the total stored in twig as placeholder;
        # real implementation would let the player choose distribution.
        return ResourceBank(twig=resources_earned)

    @staticmethod
    def handle_journey(
        player: Player, journey_location_id: str, cards_to_discard: list[Card]
    ) -> int:
        """Journey (autumn only): discard cards equal to location's point value.

        Returns points earned.  Raises ValueError if conditions not met.
        """
        if player.season != Season.AUTUMN:
            raise ValueError("Journey locations are only available in Autumn")

        # Parse point value from location id  (journey_2pt, journey_3pt, etc.)
        try:
            point_value = int(journey_location_id.split("_")[1].replace("pt", ""))
        except (IndexError, ValueError):
            raise ValueError(f"Invalid journey location id: {journey_location_id}")

        if len(cards_to_discard) != point_value:
            raise ValueError(
                f"Must discard exactly {point_value} cards for this journey, "
                f"got {len(cards_to_discard)}"
            )

        # Validate and remove cards from hand
        remaining = list(player.hand)
        for card in cards_to_discard:
            found = False
            for i, h in enumerate(remaining):
                if h.name == card.name:
                    remaining.pop(i)
                    found = True
                    break
            if not found:
                raise ValueError(f"Card {card.name} not in player's hand")

        player.hand = remaining
        return point_value

    @staticmethod
    def handle_cemetery(
        game: GameState,
        player: Player,
        revealed_cards: list[Card],
        chosen_index: int,
    ) -> Card | None:
        """Cemetery: from 4 revealed cards, play 1 for free into city.

        The caller is responsible for revealing 4 cards from deck or discard
        and passing them here.  The chosen card is added to the player's city;
        the rest go to the discard pile.

        Returns the played card, or None if no valid choice.
        """
        if not revealed_cards:
            return None
        if chosen_index < 0 or chosen_index >= len(revealed_cards):
            raise ValueError(f"Invalid choice index: {chosen_index}")

        chosen = revealed_cards[chosen_index]
        # Discard the rest
        for i, card in enumerate(revealed_cards):
            if i != chosen_index:
                game.discard.append(card)

        # Play into city for free
        player.city.append(chosen)
        return chosen

    @staticmethod
    def handle_monastery(
        game: GameState,
        player: Player,
        target_player: Player,
        resources: ResourceBank,
    ) -> int:
        """Monastery: give exactly 2 resources to an opponent, gain 4 points.

        Returns points gained (always 4 on success).
        """
        if resources.total() != 2:
            raise ValueError("Must give exactly 2 resources to opponent")
        if not player.resources.can_afford(resources):
            raise ValueError("Player cannot afford to give those resources")

        player.resources = player.resources.spend(resources)
        target_player.resources = target_player.resources.gain(resources)
        player.point_tokens += 4
        return 4

    @staticmethod
    def handle_dungeon(
        game: GameState,
        player: Player,
        critter_to_sacrifice: str,
        card_to_play: str,
    ) -> ResourceBank:
        """Dungeon: sacrifice a critter from city, reduce next card's cost by 3 any resource.

        Returns a ResourceBank representing the discount (3 total, distributed
        against the target card's cost).
        """
        # Find and remove the critter
        critter_idx = None
        for i, c in enumerate(player.city):
            if c.name == critter_to_sacrifice and c.category == CardCategory.CRITTER:
                critter_idx = i
                break
        if critter_idx is None:
            raise ValueError(
                f"Critter {critter_to_sacrifice} not found in player's city"
            )

        sacrificed = player.city.pop(critter_idx)
        game.discard.append(sacrificed)

        # Find the card to play (in hand or meadow) and calculate discount
        target = None
        for c in player.hand:
            if c.name == card_to_play:
                target = c
                break
        if target is None:
            for c in game.meadow:
                if c.name == card_to_play:
                    target = c
                    break

        if target is None:
            raise ValueError(f"Card {card_to_play} not found in hand or meadow")

        # Calculate discount: reduce cost by up to 3 total resources
        cost = target.cost
        discount_remaining = 3
        disc_twig = min(cost.twig, discount_remaining)
        discount_remaining -= disc_twig
        disc_resin = min(cost.resin, discount_remaining)
        discount_remaining -= disc_resin
        disc_pebble = min(cost.pebble, discount_remaining)
        discount_remaining -= disc_pebble
        disc_berry = min(cost.berry, discount_remaining)

        return ResourceBank(
            twig=disc_twig, resin=disc_resin, pebble=disc_pebble, berry=disc_berry
        )

    @staticmethod
    def handle_university(
        game: GameState,
        player: Player,
        card_to_discard: str,
    ) -> tuple[ResourceBank, int]:
        """University: discard 1 card from city, get its cost back + 1 any resource + 1 point.

        Returns (resources_refunded, points_gained).  The +1 any resource is
        added to the refund total; the caller picks which resource type.
        """
        card_idx = None
        for i, c in enumerate(player.city):
            if c.name == card_to_discard:
                card_idx = i
                break
        if card_idx is None:
            raise ValueError(f"Card {card_to_discard} not in player's city")

        removed = player.city.pop(card_idx)
        game.discard.append(removed)

        # Refund the card's cost
        refund = removed.cost
        player.resources = player.resources.gain(refund)

        # +1 point
        player.point_tokens += 1

        return refund, 1

    @staticmethod
    def handle_ruins(
        game: GameState,
        player: Player,
        construction_to_discard: str,
    ) -> tuple[ResourceBank, list[Card]]:
        """Ruins: discard a Construction from city, get cost back, draw 2 cards.

        Returns (resources_refunded, cards_drawn).
        """
        card_idx = None
        for i, c in enumerate(player.city):
            if (
                c.name == construction_to_discard
                and c.category == CardCategory.CONSTRUCTION
            ):
                card_idx = i
                break
        if card_idx is None:
            raise ValueError(
                f"Construction {construction_to_discard} not in player's city"
            )

        removed = player.city.pop(card_idx)
        game.discard.append(removed)

        # Refund cost
        refund = removed.cost
        player.resources = player.resources.gain(refund)

        # Draw 2 cards from deck
        drawn: list[Card] = []
        for _ in range(2):
            if game.deck:
                drawn.append(game.deck.pop(0))
        player.hand.extend(drawn)

        return refund, drawn

    @staticmethod
    def handle_inn(
        game: GameState,
        player: Player,
        meadow_index: int,
    ) -> None:
        """Inn: play a Critter or Construction from the Meadow for 3 fewer any resources.

        This method removes the card from the meadow and adds it to the
        player's city.  Cost reduction is applied automatically.
        """
        if meadow_index < 0 or meadow_index >= len(game.meadow):
            raise ValueError(f"Invalid meadow index: {meadow_index}")

        card = game.meadow[meadow_index]
        cost = card.cost

        # Apply 3 any-resource discount
        discount_remaining = 3
        disc_twig = min(cost.twig, discount_remaining)
        discount_remaining -= disc_twig
        disc_resin = min(cost.resin, discount_remaining)
        discount_remaining -= disc_resin
        disc_pebble = min(cost.pebble, discount_remaining)
        discount_remaining -= disc_pebble
        disc_berry = min(cost.berry, discount_remaining)

        reduced_cost = ResourceBank(
            twig=cost.twig - disc_twig,
            resin=cost.resin - disc_resin,
            pebble=cost.pebble - disc_pebble,
            berry=cost.berry - disc_berry,
        )

        if not player.resources.can_afford(reduced_cost):
            raise ValueError("Cannot afford card even with Inn discount")

        player.resources = player.resources.spend(reduced_cost)
        played = game.meadow.pop(meadow_index)
        player.city.append(played)

    @staticmethod
    def handle_lookout(
        game: GameState,
        player: Player,
        location_to_copy: str,
    ) -> None:
        """Lookout: copy any basic or Forest location effect.

        This is a placeholder — the actual location effect execution depends
        on the LocationManager, which the action layer would invoke.
        """
        # Validation only; execution delegated to action layer + LocationManager
        pass

    @staticmethod
    def can_use_second_slot(player: Player, card_name: str) -> bool:
        """Check if player has the unlocking card for a 2nd permanent-worker slot.

        Cemetery needs Undertaker, Monastery needs Monk, Dungeon needs Ranger.
        """
        unlocker = SpecialRules._SECOND_SLOT_UNLOCKERS.get(card_name)
        if unlocker is None:
            return False
        return any(c.name == unlocker for c in player.city)
