from enum import Enum


class Season(str, Enum):
    WINTER = "winter"
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"


class ResourceType(str, Enum):
    TWIG = "twig"
    RESIN = "resin"
    PEBBLE = "pebble"
    BERRY = "berry"


class CardType(str, Enum):
    TAN_TRAVELER = "tan_traveler"
    GREEN_PRODUCTION = "green_production"
    RED_DESTINATION = "red_destination"
    BLUE_GOVERNANCE = "blue_governance"
    PURPLE_PROSPERITY = "purple_prosperity"


class CardCategory(str, Enum):
    CRITTER = "critter"
    CONSTRUCTION = "construction"


class LocationType(str, Enum):
    BASIC = "basic"
    FOREST = "forest"
    HAVEN = "haven"
    JOURNEY = "journey"
    DESTINATION = "destination"
    EVENT = "event"
