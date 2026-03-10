"""All Everdell critter card definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ed_engine.cards import register
from ed_engine.cards.base import (
    DestinationCard,
    GovernanceCard,
    ProductionCard,
    ProsperityCard,
    TravelerCard,
)
from ed_engine.models.enums import CardCategory, CardType
from ed_engine.models.resources import ResourceBank

if TYPE_CHECKING:
    from ed_engine.models.card import Card
    from ed_engine.models.game import GameState
    from ed_engine.models.player import Player


# ---------------------------------------------------------------------------
# Purple / Prosperity critters
# ---------------------------------------------------------------------------


@register
class Architect(ProsperityCard):
    name: str = "Architect"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=4)
    base_points: int = 2
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Crane"

    def on_score(self, game: GameState, player: Player) -> int:
        """+1 pt per leftover resin and pebble, up to 6."""
        return min(player.resources.resin + player.resources.pebble, 6)


@register
class King(ProsperityCard):
    name: str = "King"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=6)
    base_points: int = 4
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Castle"

    def on_score(self, game: GameState, player: Player) -> int:
        """+1 pt per basic Event, +2 pt per special Event."""
        player_id = str(player.id)
        basic_count = sum(
            1 for edata in game.basic_events.values()
            if (isinstance(edata, dict) and edata.get("claimed_by") == player_id)
            or (hasattr(edata, "claimed_by") and getattr(edata, "claimed_by", None) == player_id)
        )
        special_count = sum(
            1 for edata in game.special_events.values()
            if (isinstance(edata, dict) and edata.get("claimed_by") == player_id)
            or (hasattr(edata, "claimed_by") and getattr(edata, "claimed_by", None) == player_id)
        )
        return basic_count + 2 * special_count


@register
class Gatherer(ProsperityCard):
    name: str = "Gatherer"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 2
    unique: bool = False
    copies_in_deck: int = 4
    paired_with: str | None = "Farm"

    def on_score(self, game: GameState, player: Player) -> int:
        """+3 pt if paired with Harvester in city."""
        has_harvester = any(c.name == "Harvester" for c in player.city)
        return 3 if has_harvester else 0


# ---------------------------------------------------------------------------
# Green / Production critters
# ---------------------------------------------------------------------------


@register
class BargeToad(ProductionCard):
    name: str = "Barge Toad"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 1
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "Twig Barge"

    def on_production(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Gain 2 twigs per Farm in city."""
        farm_count = sum(1 for c in player.city if c.name == "Farm")
        if farm_count > 0:
            player.resources = player.resources.gain(
                ResourceBank(twig=2 * farm_count)
            )


@register
class ChipSweep(ProductionCard):
    name: str = "Chip Sweep"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=3)
    base_points: int = 2
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "Resin Refinery"

    def on_production(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Activate any 1 green Production card in city — interactive choice."""
        skip = {"Chip Sweep"}
        eligible = [
            c for c in player.city
            if c.card_type == CardType.GREEN_PRODUCTION and c is not self and c.name not in skip
        ]
        if not eligible:
            return
        if len(eligible) == 1:
            # Only one option — activate directly
            eligible[0].on_production(game, player, ctx=ctx)
            return
        game.pending_choice = {
            "choice_type": "select_card",
            "card": "Chip Sweep",
            "player_id": str(player.id),
            "step": "pick_card",
            "prompt": "Choose a green Production card to activate with Chip Sweep",
            "options": [
                {"label": c.name, "value": c.name, "base_points": c.base_points}
                for c in eligible
            ],
            "context": {},
        }

    def resolve_choice(
        self, game: GameState, player: Player, choice_index: int, option: dict,
        pending_choice: dict, *, ctx: dict | None = None,
    ) -> list[str]:
        card_name = option["value"]
        for card in player.city:
            if card.name == card_name and card.card_type == CardType.GREEN_PRODUCTION:
                game.pending_choice = None
                card.on_production(game, player, ctx=ctx)
                return [f"{player.name} activated {card_name} via Chip Sweep"]
        game.pending_choice = None
        return [f"ERROR: Could not find {card_name} in city"]


@register
class Doctor(ProductionCard):
    name: str = "Doctor"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=4)
    base_points: int = 4
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "University"

    def on_production(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Pay up to 3 berries, gain 1 pt per berry paid."""
        pay = min(3, player.resources.berry)
        if pay > 0:
            player.resources = player.resources.spend(ResourceBank(berry=pay))
            player.point_tokens += pay


@register
class Harvester(ProductionCard):
    name: str = "Harvester"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=3)
    base_points: int = 2
    unique: bool = False
    copies_in_deck: int = 4
    paired_with: str | None = "Farm"

    def on_production(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """If paired with Gatherer and have Farm, gain 1 of any resource."""
        has_farm = any(c.name == "Farm" for c in player.city)
        has_gatherer = any(c.name == "Gatherer" for c in player.city)
        if has_farm and has_gatherer:
            game.pending_choice = {
                "choice_type": "select_resource",
                "card": "Harvester",
                "player_id": str(player.id),
                "step": "pick_resource",
                "prompt": "Choose a resource to gain from Harvester",
                "options": [
                    {"label": "1 Twig", "value": "1T", "resource": "twig", "amount": 1},
                    {"label": "1 Resin", "value": "1R", "resource": "resin", "amount": 1},
                    {"label": "1 Pebble", "value": "1P", "resource": "pebble", "amount": 1},
                    {"label": "1 Berry", "value": "1B", "resource": "berry", "amount": 1},
                ],
                "context": {},
            }

    def resolve_choice(
        self, game: GameState, player: Player, choice_index: int, option: dict,
        pending_choice: dict, *, ctx: dict | None = None,
    ) -> list[str]:
        resource = option["resource"]
        amount = option["amount"]
        player.resources = player.resources.gain(ResourceBank(**{resource: amount}))
        game.pending_choice = None
        return [f"{player.name} gained {amount} {resource} from Harvester"]


@register
class MinerMole(ProductionCard):
    name: str = "Miner Mole"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=3)
    base_points: int = 1
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "Mine"

    def on_production(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Copy 1 green Production card from an opponent's city — interactive choice."""
        skip = {"Chip Sweep", "Miner Mole"}
        opponents = [p for p in game.players if str(p.id) != str(player.id)]
        if not opponents:
            return

        # Collect all eligible green cards from all opponents
        all_eligible = []
        for opp in opponents:
            for card in opp.city:
                if card.card_type == CardType.GREEN_PRODUCTION and card.name not in skip:
                    all_eligible.append((opp, card))

        if not all_eligible:
            return

        if len(all_eligible) == 1:
            # Only one option — activate directly
            _, card = all_eligible[0]
            card.on_production(game, player, ctx=ctx)
            return

        # Check if all from same opponent
        opp_ids = {str(o.id) for o, _ in all_eligible}
        if len(opp_ids) == 1:
            # Single opponent, pick card directly
            options = [
                {"label": f"{c.name} ({opp.name})", "value": c.name, "opponent_id": str(opp.id), "base_points": c.base_points}
                for opp, c in all_eligible
            ]
            game.pending_choice = {
                "choice_type": "select_card",
                "card": "Miner Mole",
                "player_id": str(player.id),
                "step": "pick_card",
                "prompt": "Choose an opponent's green Production card to copy (Miner Mole)",
                "options": options,
                "context": {},
            }
        else:
            # Multiple opponents — pick opponent first
            opp_options = []
            seen = set()
            for opp, _ in all_eligible:
                oid = str(opp.id)
                if oid not in seen:
                    seen.add(oid)
                    opp_options.append({"label": opp.name, "value": oid})
            game.pending_choice = {
                "choice_type": "select_opponent",
                "card": "Miner Mole",
                "player_id": str(player.id),
                "step": "pick_opponent",
                "prompt": "Choose an opponent to copy a green Production card from (Miner Mole)",
                "options": opp_options,
                "context": {},
            }

    def resolve_choice(
        self, game: GameState, player: Player, choice_index: int, option: dict,
        pending_choice: dict, *, ctx: dict | None = None,
    ) -> list[str]:
        step = pending_choice.get("step")
        skip = {"Chip Sweep", "Miner Mole"}

        if step == "pick_opponent":
            opponent_id = option["value"]
            opp = None
            for p in game.players:
                if str(p.id) == opponent_id:
                    opp = p
                    break
            if not opp:
                game.pending_choice = None
                return ["ERROR: Opponent not found for Miner Mole"]

            eligible = [c for c in opp.city if c.card_type == CardType.GREEN_PRODUCTION and c.name not in skip]
            if len(eligible) == 1:
                game.pending_choice = None
                eligible[0].on_production(game, player, ctx=ctx)
                return [f"{player.name} copied {eligible[0].name} from {opp.name} via Miner Mole"]

            options = [
                {"label": c.name, "value": c.name, "opponent_id": opponent_id, "base_points": c.base_points}
                for c in eligible
            ]
            game.pending_choice = {
                "choice_type": "select_card",
                "card": "Miner Mole",
                "player_id": str(player.id),
                "step": "pick_card",
                "prompt": f"Choose a green Production card to copy from {opp.name} (Miner Mole)",
                "options": options,
                "context": {"opponent_id": opponent_id},
            }
            return [f"{player.name} chose {opp.name} for Miner Mole"]

        elif step == "pick_card":
            card_name = option["value"]
            opponent_id = option.get("opponent_id") or pending_choice.get("context", {}).get("opponent_id")
            game.pending_choice = None
            for p in game.players:
                if str(p.id) == opponent_id:
                    for c in p.city:
                        if c.name == card_name and c.card_type == CardType.GREEN_PRODUCTION:
                            c.on_production(game, player, ctx=ctx)
                            return [f"{player.name} copied {card_name} from {p.name} via Miner Mole"]

        game.pending_choice = None
        return []


@register
class Monk(ProductionCard):
    name: str = "Monk"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=1)
    base_points: int = 0
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Monastery"

    def on_production(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Give up to 2 berries to an opponent, gain 2 VP per berry — interactive choice."""
        opponents = [p for p in game.players if str(p.id) != str(player.id)]
        max_give = min(2, player.resources.berry)
        if not opponents or max_give == 0:
            return

        if len(opponents) == 1:
            # Skip opponent selection, go straight to amount
            opp = opponents[0]
            options = [
                {"label": f"Give {n} berry(ies) (+{n*2} VP)", "value": str(n), "amount": n}
                for n in range(max_give + 1)
            ]
            game.pending_choice = {
                "choice_type": "select_resource",
                "card": "Monk",
                "player_id": str(player.id),
                "step": "pick_amount",
                "prompt": f"Choose how many berries to give {opp.name} (Monk)",
                "options": options,
                "context": {"opponent_id": str(opp.id)},
            }
        else:
            # Multi-opponent: pick opponent first
            options = [
                {"label": p.name, "value": str(p.id)}
                for p in opponents
            ]
            game.pending_choice = {
                "choice_type": "select_opponent",
                "card": "Monk",
                "player_id": str(player.id),
                "step": "pick_opponent",
                "prompt": "Choose an opponent to give berries to (Monk)",
                "options": options,
                "context": {"max_give": max_give},
            }

    def resolve_choice(
        self, game: GameState, player: Player, choice_index: int, option: dict,
        pending_choice: dict, *, ctx: dict | None = None,
    ) -> list[str]:
        step = pending_choice.get("step")
        context = pending_choice.get("context", {})

        if step == "pick_opponent":
            opponent_id = option["value"]
            max_give = context.get("max_give", min(2, player.resources.berry))
            options = [
                {"label": f"Give {n} berry(ies) (+{n*2} VP)", "value": str(n), "amount": n}
                for n in range(max_give + 1)
            ]
            game.pending_choice = {
                "choice_type": "select_resource",
                "card": "Monk",
                "player_id": str(player.id),
                "step": "pick_amount",
                "prompt": "Choose how many berries to give (Monk)",
                "options": options,
                "context": {"opponent_id": opponent_id},
            }
            return [f"{player.name} chose opponent for Monk"]

        elif step == "pick_amount":
            amount = option.get("amount", int(option["value"]))
            opponent_id = context.get("opponent_id")
            game.pending_choice = None
            if amount > 0:
                player.resources = player.resources.spend(ResourceBank(berry=amount))
                for other in game.players:
                    if str(other.id) == opponent_id:
                        other.resources = other.resources.gain(ResourceBank(berry=amount))
                        player.point_tokens += 2 * amount
                        return [f"{player.name} gave {amount} berry(ies) to {other.name} via Monk (+{amount*2} VP)"]
            return [f"{player.name} gave 0 berries via Monk"]

        game.pending_choice = None
        return []


@register
class Peddler(ProductionCard):
    name: str = "Peddler"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 1
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "Ruins"

    def on_production(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Trade up to 2 resources for 2 other resources — interactive choice."""
        total = player.resources.twig + player.resources.resin + player.resources.pebble + player.resources.berry
        if total == 0:
            return
        options: list[dict] = [{"label": "Trade nothing", "value": "0"}]
        if total >= 1:
            options.append({"label": "Trade 1 resource", "value": "1"})
        if total >= 2:
            options.append({"label": "Trade 2 resources", "value": "2"})
        game.pending_choice = {
            "choice_type": "select_resource",
            "card": "Peddler",
            "player_id": str(player.id),
            "step": "pick_trade_count",
            "prompt": "How many resources to trade? (Peddler)",
            "options": options,
            "context": {},
        }

    def resolve_choice(
        self, game: GameState, player: Player, choice_index: int, option: dict,
        pending_choice: dict, *, ctx: dict | None = None,
    ) -> list[str]:
        step = pending_choice.get("step", "")
        context = pending_choice.get("context", {})

        if step == "pick_trade_count":
            count = int(option["value"])
            if count == 0:
                game.pending_choice = None
                return [f"{player.name} traded nothing via Peddler"]
            give_options: list[dict] = []
            for res in ("twig", "resin", "pebble", "berry"):
                if getattr(player.resources, res) > 0:
                    give_options.append({"label": f"1 {res.title()}", "value": res})
            game.pending_choice = {
                "choice_type": "select_resource",
                "card": "Peddler",
                "player_id": str(player.id),
                "step": "pick_give",
                "prompt": f"Choose resource to give (1 of {count}) — Peddler",
                "options": give_options,
                "context": {"trade_count": count, "given": [], "remaining_give": count},
            }
            return []

        elif step == "pick_give":
            res = option["value"]
            given = list(context.get("given", []))
            given.append(res)
            remaining = context["remaining_give"] - 1
            player.resources = player.resources.spend(ResourceBank(**{res: 1}))

            if remaining > 0:
                give_options = []
                for r in ("twig", "resin", "pebble", "berry"):
                    if getattr(player.resources, r) > 0:
                        give_options.append({"label": f"1 {r.title()}", "value": r})
                if not give_options:
                    remaining = 0
                else:
                    game.pending_choice = {
                        "choice_type": "select_resource",
                        "card": "Peddler",
                        "player_id": str(player.id),
                        "step": "pick_give",
                        "prompt": f"Choose resource to give ({remaining} left) — Peddler",
                        "options": give_options,
                        "context": {"trade_count": context["trade_count"], "given": given, "remaining_give": remaining},
                    }
                    return []

            # Now pick resources to receive
            trade_count = len(given)
            receive_options = [{"label": f"1 {r.title()}", "value": r} for r in ("twig", "resin", "pebble", "berry")]
            game.pending_choice = {
                "choice_type": "select_resource",
                "card": "Peddler",
                "player_id": str(player.id),
                "step": "pick_receive",
                "prompt": f"Choose resource to receive (1 of {trade_count}) — Peddler",
                "options": receive_options,
                "context": {"given": given, "received": [], "remaining_receive": trade_count},
            }
            return []

        elif step == "pick_receive":
            res = option["value"]
            received = list(context.get("received", []))
            received.append(res)
            remaining = context["remaining_receive"] - 1
            player.resources = player.resources.gain(ResourceBank(**{res: 1}))

            if remaining > 0:
                receive_options = [{"label": f"1 {r.title()}", "value": r} for r in ("twig", "resin", "pebble", "berry")]
                game.pending_choice = {
                    "choice_type": "select_resource",
                    "card": "Peddler",
                    "player_id": str(player.id),
                    "step": "pick_receive",
                    "prompt": f"Choose resource to receive ({remaining} left) — Peddler",
                    "options": receive_options,
                    "context": {"given": context["given"], "received": received, "remaining_receive": remaining},
                }
                return []

            game.pending_choice = None
            return [f"{player.name} traded {', '.join(context['given'])} for {', '.join(received)} via Peddler"]

        game.pending_choice = None
        return []


@register
class Teacher(ProductionCard):
    name: str = "Teacher"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 2
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "School"

    def on_production(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Draw 2 cards, choose which to keep — interactive choice."""
        deck_mgr = ctx.get("deck_mgr") if ctx else None
        if not deck_mgr:
            return
        drawn = deck_mgr.draw(2)
        if not drawn:
            return
        if len(drawn) == 1:
            # Only 1 card drawn — keep it automatically
            player.hand.append(drawn[0])
            return
        game.pending_choice = {
            "choice_type": "select_card",
            "card": "Teacher",
            "player_id": str(player.id),
            "step": "pick_card",
            "prompt": "Choose a card to keep (the other goes to an opponent)",
            "options": [
                {"label": c.name, "value": c.name, "base_points": c.base_points}
                for c in drawn
            ],
            "context": {"revealed_cards": [{"name": c.name, "base_points": c.base_points} for c in drawn]},
        }
        # Store actual card objects temporarily on game for resolve_choice
        if not hasattr(game, "_teacher_drawn"):
            game._teacher_drawn = {}
        game._teacher_drawn[str(player.id)] = drawn

    def resolve_choice(
        self, game: GameState, player: Player, choice_index: int, option: dict,
        pending_choice: dict, *, ctx: dict | None = None,
    ) -> list[str]:
        deck_mgr = ctx.get("deck_mgr") if ctx else None
        drawn = getattr(game, "_teacher_drawn", {}).pop(str(player.id), [])
        if not drawn:
            game.pending_choice = None
            return ["ERROR: No Teacher drawn cards found"]

        kept = drawn[choice_index]
        given = drawn[1 - choice_index]
        player.hand.append(kept)

        # Give other card to first opponent
        gave_to = None
        for other in game.players:
            if str(other.id) != str(player.id):
                other.hand.append(given)
                gave_to = other.name
                break
        if gave_to is None and deck_mgr:
            deck_mgr.discard([given])

        game.pending_choice = None
        return [f"{player.name} kept {kept.name} from Teacher, gave {given.name} to {gave_to or 'discard'}"]


@register
class Woodcarver(ProductionCard):
    name: str = "Woodcarver"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 2
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "Storehouse"

    def on_production(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Pay up to 3 twigs, gain 1 pt per twig paid."""
        pay = min(3, player.resources.twig)
        if pay > 0:
            player.resources = player.resources.spend(ResourceBank(twig=pay))
            player.point_tokens += pay


# ---------------------------------------------------------------------------
# Red / Destination critters
# ---------------------------------------------------------------------------


@register
class Queen(DestinationCard):
    name: str = "Queen"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=5)
    base_points: int = 4
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Palace"

    def on_worker_placed(
        self, game: GameState, player: Player, visitor: Player, *, ctx: dict | None = None
    ) -> None:
        """Play any card from hand/Meadow worth <=3 pt free — interactive choice."""
        from ed_engine.engine.actions import MAX_CITY_SIZE
        city_size = sum(1 for c in player.city if c.occupies_city_space)
        city_names = {c.name for c in player.city}

        def _eligible(card):
            if card.base_points > 3:
                return False
            if card.unique and card.name in city_names:
                return False
            if card.occupies_city_space and city_size >= MAX_CITY_SIZE:
                return False
            return True

        options = []
        # Hand cards
        for i, card in enumerate(player.hand):
            if _eligible(card):
                options.append({
                    "label": f"{card.name} (hand)",
                    "value": card.name,
                    "source": "hand",
                    "hand_index": i,
                    "base_points": card.base_points,
                })
        # Meadow cards
        deck_mgr = ctx.get("deck_mgr") if ctx else None
        if deck_mgr:
            for i, card in enumerate(deck_mgr.meadow):
                if _eligible(card):
                    options.append({
                        "label": f"{card.name} (meadow)",
                        "value": card.name,
                        "source": "meadow",
                        "meadow_index": i,
                        "base_points": card.base_points,
                    })

        if not options:
            return  # No eligible cards

        # Add "play none" option
        options.append({"label": "Play nothing", "value": "__none__", "source": "none", "base_points": 0})

        game.pending_choice = {
            "choice_type": "select_card",
            "card": "Queen",
            "player_id": str(player.id),
            "step": "pick_card",
            "prompt": "Choose a card to play free via Queen (VP <= 3)",
            "options": options,
            "context": {},
        }

    def resolve_choice(
        self, game: GameState, player: Player, choice_index: int, option: dict,
        pending_choice: dict, *, ctx: dict | None = None,
    ) -> list[str]:
        value = option["value"]
        if value == "__none__":
            game.pending_choice = None
            return [f"{player.name} chose not to play a card via Queen"]

        source = option.get("source")
        deck_mgr = ctx.get("deck_mgr") if ctx else None
        played = None

        if source == "hand":
            for i, card in enumerate(player.hand):
                if card.name == value:
                    played = player.hand.pop(i)
                    break
        elif source == "meadow" and deck_mgr:
            meadow_idx = option.get("meadow_index")
            if meadow_idx is not None and 0 <= meadow_idx < len(deck_mgr.meadow):
                if deck_mgr.meadow[meadow_idx].name == value:
                    played = deck_mgr.draw_from_meadow(meadow_idx)
                else:
                    # Meadow shifted — find by name
                    for i, card in enumerate(deck_mgr.meadow):
                        if card.name == value:
                            played = deck_mgr.draw_from_meadow(i)
                            break

        if played is None:
            game.pending_choice = None
            return [f"ERROR: Could not find {value} for Queen"]

        game.pending_choice = None
        player.city.append(played)
        played.on_play(game, player, ctx=ctx)
        return [f"{player.name} played {played.name} free via Queen"]


# ---------------------------------------------------------------------------
# Blue / Governance critters
# ---------------------------------------------------------------------------


@register
class Historian(GovernanceCard):
    name: str = "Historian"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 1
    unique: bool = True
    copies_in_deck: int = 3
    paired_with: str | None = "Clock Tower"

    def on_card_played(
        self, game: GameState, player: Player, played_card: Card, *, ctx: dict | None = None
    ) -> None:
        """Draw 1 card after playing any card."""
        deck_mgr = ctx.get("deck_mgr") if ctx else None
        if deck_mgr:
            drawn = deck_mgr.draw(1)
            player.hand.extend(drawn)


@register
class Innkeeper(GovernanceCard):
    name: str = "Innkeeper"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=1)
    base_points: int = 1
    unique: bool = True
    copies_in_deck: int = 3
    paired_with: str | None = "Inn"

    def on_card_played(
        self, game: GameState, player: Player, played_card: Card, *, ctx: dict | None = None
    ) -> None:
        """Discard Innkeeper to decrease Critter cost by 3 berries. (Deferred — requires pre-play hook.)"""
        pass


@register
class Judge(GovernanceCard):
    name: str = "Judge"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=3)
    base_points: int = 2
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Courthouse"

    def on_card_played(
        self, game: GameState, player: Player, played_card: Card, *, ctx: dict | None = None
    ) -> None:
        """Replace 1 resource in cost with 1 other resource. (Deferred — requires cost modification hook.)"""
        pass


@register
class Shopkeeper(GovernanceCard):
    name: str = "Shopkeeper"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 1
    unique: bool = True
    copies_in_deck: int = 3
    paired_with: str | None = "General Store"

    def on_card_played(
        self, game: GameState, player: Player, played_card: Card, *, ctx: dict | None = None
    ) -> None:
        """Gain 1 berry after playing a Critter."""
        if played_card.category == CardCategory.CRITTER:
            player.resources = player.resources.gain(ResourceBank(berry=1))


# ---------------------------------------------------------------------------
# Tan / Traveler critters
# ---------------------------------------------------------------------------


@register
class Bard(TravelerCard):
    name: str = "Bard"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=3)
    base_points: int = 0
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Theater"

    def on_play(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Discard up to 5 cards from hand (lowest VP), gain 1 VP per card."""
        deck_mgr = ctx.get("deck_mgr") if ctx else None
        hand = sorted(player.hand, key=lambda c: c.base_points)
        to_discard = hand[:min(5, len(hand))]
        for card in to_discard:
            player.hand.remove(card)
        player.point_tokens += len(to_discard)
        if deck_mgr and to_discard:
            deck_mgr.discard(to_discard)


@register
class Fool(TravelerCard):
    name: str = "Fool"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=3)
    base_points: int = -2
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Fair Grounds"

    def on_play(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Played into an opponent's city — interactive opponent selection."""
        opponents = [p for p in game.players if str(p.id) != str(player.id)]
        if not opponents:
            return
        if len(opponents) == 1:
            # Only one opponent — move directly
            opp = opponents[0]
            if self in player.city:
                player.city.remove(self)
            opp.city.append(self)
            return

        options = [
            {"label": p.name, "value": str(p.id)}
            for p in opponents
        ]
        game.pending_choice = {
            "choice_type": "select_opponent",
            "card": "Fool",
            "player_id": str(player.id),
            "step": "pick_opponent",
            "prompt": "Choose an opponent to receive the Fool (-2 VP for them!)",
            "options": options,
            "context": {},
        }

    def resolve_choice(
        self, game: GameState, player: Player, choice_index: int, option: dict,
        pending_choice: dict, *, ctx: dict | None = None,
    ) -> list[str]:
        opponent_id = option["value"]
        for other in game.players:
            if str(other.id) == opponent_id:
                if self in player.city:
                    player.city.remove(self)
                other.city.append(self)
                game.pending_choice = None
                return [f"{player.name} sent Fool to {other.name}'s city"]
        game.pending_choice = None
        return ["ERROR: Could not find opponent for Fool"]


@register
class PostalPigeon(TravelerCard):
    name: str = "Postal Pigeon"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 0
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "Post Office"

    def on_play(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Reveal 2 from deck, choose 1 worth <=3 pt to play free — interactive choice."""
        deck_mgr = ctx.get("deck_mgr") if ctx else None
        if not deck_mgr:
            return
        drawn = deck_mgr.draw(2)
        if not drawn:
            return

        from ed_engine.engine.actions import MAX_CITY_SIZE
        city_size = sum(1 for c in player.city if c.occupies_city_space)
        city_names = {c.name for c in player.city}

        eligible = []
        for card in drawn:
            if card.base_points <= 3:
                if card.unique and card.name in city_names:
                    continue
                if card.occupies_city_space and city_size >= MAX_CITY_SIZE:
                    continue
                eligible.append(card)

        if not eligible:
            # No eligible cards — discard all
            deck_mgr.discard(drawn)
            return

        options = [
            {"label": c.name, "value": c.name, "base_points": c.base_points}
            for c in eligible
        ]
        # Add "play none" option
        options.append({"label": "Play none", "value": "__none__", "base_points": 0})

        game.pending_choice = {
            "choice_type": "select_card",
            "card": "Postal Pigeon",
            "player_id": str(player.id),
            "step": "pick_card",
            "prompt": "Choose a revealed card to play free (VP <= 3)",
            "options": options,
            "context": {},
        }
        # Store drawn cards for resolve_choice
        if not hasattr(game, "_postal_pigeon_drawn"):
            game._postal_pigeon_drawn = {}
        game._postal_pigeon_drawn[str(player.id)] = drawn

    def resolve_choice(
        self, game: GameState, player: Player, choice_index: int, option: dict,
        pending_choice: dict, *, ctx: dict | None = None,
    ) -> list[str]:
        deck_mgr = ctx.get("deck_mgr") if ctx else None
        drawn = getattr(game, "_postal_pigeon_drawn", {}).pop(str(player.id), [])
        if not drawn:
            game.pending_choice = None
            return ["ERROR: No Postal Pigeon drawn cards found"]

        value = option["value"]
        events: list[str] = []

        if value != "__none__":
            played = None
            for card in drawn:
                if card.name == value:
                    played = card
                    break
            if played:
                drawn.remove(played)
                player.city.append(played)
                played.on_play(game, player, ctx=ctx)
                events.append(f"{player.name} played {played.name} free via Postal Pigeon")

        # Discard remaining
        if drawn and deck_mgr:
            deck_mgr.discard(drawn)

        game.pending_choice = None
        return events


@register
class Ranger(TravelerCard):
    name: str = "Ranger"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 1
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Dungeon"

    def on_play(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Move 1 deployed worker to a new location."""
        if not player.workers_deployed:
            return  # No deployed workers to move

        game.pending_choice = {
            "card": self.name,
            "type": "pick_worker",
            "prompt": "Choose a deployed worker to move:",
            "options": list(player.workers_deployed),
        }

    def resolve_choice(
        self,
        game: GameState,
        player: Player,
        idx: int,
        option: str,
        pending: dict,
        *,
        ctx: dict | None = None,
    ) -> list[str]:
        choice_type = pending.get("type")
        location_mgr = (ctx or {}).get("location_mgr")

        if choice_type == "pick_worker":
            # Player chose which deployed worker to move
            old_location_id = option

            # Remove worker from old location
            if location_mgr:
                old_loc = location_mgr.get_location(old_location_id)
                if old_loc is not None:
                    old_loc.remove_worker(str(player.id))

            # Find available locations for the worker
            if location_mgr:
                available = location_mgr.get_available_locations(str(player.id), player.season)
                available_ids = [loc.id for loc in available if loc.id != old_location_id]
            else:
                available_ids = []

            if not available_ids:
                # No valid destinations — put worker back
                if location_mgr:
                    old_loc = location_mgr.get_location(old_location_id)
                    if old_loc is not None:
                        old_loc.place_worker(str(player.id))
                game.pending_choice = None
                return [f"{player.name}'s Ranger found no available location to move to"]

            game.pending_choice = {
                "card": self.name,
                "type": "pick_destination",
                "prompt": "Choose a new location for the worker:",
                "options": available_ids,
                "context": {"old_location": old_location_id},
            }
            return [f"{player.name}'s Ranger picks up worker from {old_location_id}"]

        elif choice_type == "pick_destination":
            # Player chose the new location
            new_location_id = option
            old_location_id = pending.get("context", {}).get("old_location")

            # Update workers_deployed
            if old_location_id in player.workers_deployed:
                player.workers_deployed.remove(old_location_id)
            player.workers_deployed.append(new_location_id)

            # Place worker on new location and activate it
            if location_mgr:
                new_loc = location_mgr.get_location(new_location_id)
                if new_loc is not None:
                    new_loc.place_worker(str(player.id))
                    deck_mgr = (ctx or {}).get("deck_mgr")
                    new_loc.on_activate(game, player, deck_mgr=deck_mgr)

            game.pending_choice = None
            return [f"{player.name}'s Ranger moved worker to {new_location_id}"]

        game.pending_choice = None
        return []


@register
class Shepherd(TravelerCard):
    name: str = "Shepherd"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=3)
    base_points: int = 1
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Chapel"

    def on_play(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Gain 3 berries, +1 pt per VP token on Chapel."""
        player.resources = player.resources.gain(ResourceBank(berry=3))


@register
class Undertaker(TravelerCard):
    name: str = "Undertaker"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 1
    unique: bool = True
    copies_in_deck: int = 2
    paired_with: str | None = "Cemetery"

    def on_play(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Set up interactive meadow selection: discard 3, then draw 1."""
        deck_mgr = ctx.get("deck_mgr") if ctx else None
        if not deck_mgr or not deck_mgr.meadow:
            return
        # Set pending choice — player must select meadow cards interactively
        game.pending_choice = {
            "card": "Undertaker",
            "player_id": str(player.id),
            "step": "discard",
            "discards_remaining": 3,
            "prompt": "Select a meadow card to discard (3 remaining)",
        }


@register
class Wanderer(TravelerCard):
    name: str = "Wanderer"
    category: CardCategory = CardCategory.CRITTER
    cost: ResourceBank = ResourceBank(berry=2)
    base_points: int = 1
    unique: bool = False
    copies_in_deck: int = 3
    paired_with: str | None = "Lookout"
    occupies_city_space: bool = False

    def on_play(self, game: GameState, player: Player, *, ctx: dict | None = None) -> None:
        """Draw 3 cards. Does not occupy a city space."""
        deck_mgr = ctx.get("deck_mgr") if ctx else None
        if deck_mgr:
            drawn = deck_mgr.draw(3)
            player.hand.extend(drawn)
