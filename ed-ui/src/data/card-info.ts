export interface CardInfoEntry {
  description: string
  ability: string
}

export const CARD_INFO: Record<string, CardInfoEntry> = {
  // === PURPLE / PROSPERITY ===
  "Castle": {
    description: "A grand fortification overlooking the valley.",
    ability: "+1 VP per common (non-unique) Construction in your city.",
  },
  "Ever Tree": {
    description: "The ancient tree at the heart of Everdell.",
    ability: "+1 VP per Prosperity (purple) card in your city.",
  },
  "Palace": {
    description: "A magnificent palace of stone and glass.",
    ability: "+1 VP per unique Construction in your city.",
  },
  "School": {
    description: "Where young critters learn their trades.",
    ability: "+1 VP per common Critter in your city.",
  },
  "Theater": {
    description: "A stage for Everdell's finest performers.",
    ability: "+1 VP per unique Critter in your city.",
  },
  "Architect": {
    description: "A master builder who wastes nothing.",
    ability: "+1 VP per leftover resin and pebble (up to 6 bonus VP).",
  },
  "King": {
    description: "The wise ruler of the valley. Paired with Castle.",
    ability: "+1 VP per basic Event claimed, +2 VP per special Event claimed.",
  },
  "Gatherer": {
    description: "A resourceful forager of the woodland. Common (up to 4 in deck).",
    ability: "+3 VP if paired with a Harvester in your city.",
  },

  // === GREEN / PRODUCTION ===
  "Fair Grounds": {
    description: "A bustling marketplace of wonders.",
    ability: "Production: Draw 2 cards.",
  },
  "Farm": {
    description: "Rich soil yields a bountiful harvest.",
    ability: "Production: Gain 1 berry.",
  },
  "General Store": {
    description: "Everything a critter could need.",
    ability: "Production: Gain 1 berry (or 2 if you have a Farm).",
  },
  "Mine": {
    description: "Deep tunnels rich with precious stones.",
    ability: "Production: Gain 1 pebble.",
  },
  "Resin Refinery": {
    description: "Sap collected and refined into golden resin.",
    ability: "Production: Gain 1 resin.",
  },
  "Storehouse": {
    description: "A well-stocked storehouse for lean times.",
    ability: "Production: Place 3 twigs, 2 resin, 1 pebble, or 2 berries on this card.",
  },
  "Twig Barge": {
    description: "Logs floated down the river.",
    ability: "Production: Gain 2 twigs.",
  },
  "Barge Toad": {
    description: "A stout toad who mans the river barges.",
    ability: "Production: Gain 2 twigs per Farm in your city.",
  },
  "Chip Sweep": {
    description: "A tidy chipmunk who keeps things running.",
    ability: "Production: Activate any 1 green Production card in your city.",
  },
  "Doctor": {
    description: "Healer of the woodland creatures.",
    ability: "Production: Pay up to 3 berries to gain 1 VP per berry paid.",
  },
  "Harvester": {
    description: "A tireless worker of the fields. Common (up to 4 in deck).",
    ability: "Production: If you have a Farm, gain 1 resource of any type. +3 VP if paired with Gatherer.",
  },
  "Miner Mole": {
    description: "Always digging into others' business.",
    ability: "Production: Copy 1 green Production card from an opponent's city.",
  },
  "Monk": {
    description: "A generous soul devoted to charity.",
    ability: "Production: Give up to 2 berries to an opponent, gain 2 VP per berry given.",
  },
  "Peddler": {
    description: "A shrewd trader of goods.",
    ability: "Production: Trade up to 2 of your resources for 2 different resources.",
  },
  "Teacher": {
    description: "A wise instructor sharing knowledge.",
    ability: "Production: Draw 2 cards, keep 1, give 1 to an opponent.",
  },
  "Woodcarver": {
    description: "A craftsman who turns twigs into art.",
    ability: "Production: Pay up to 3 twigs to gain 1 VP per twig paid.",
  },

  // === RED / DESTINATION ===
  "Cemetery": {
    description: "A somber place with hidden treasures.",
    ability: "Worker: Reveal 4 cards from deck/discard, play 1 for free.",
  },
  "Chapel": {
    description: "A sacred place of reflection.",
    ability: "Worker: Place 1 VP token on Chapel. Draw 2 cards per VP token on it.",
  },
  "Inn": {
    description: "A cozy waypoint for weary travelers. Open destination.",
    ability: "Worker: Play a Critter or Construction from the Meadow for 3 less of any resource.",
  },
  "Lookout": {
    description: "A high vantage point over the valley.",
    ability: "Worker: Copy the effect of any basic or Forest location.",
  },
  "Monastery": {
    description: "A place of quiet contemplation. Permanent worker.",
    ability: "Worker: Give 2 resources to an opponent, gain 4 VP. Worker stays permanently.",
  },
  "Post Office": {
    description: "Where letters and parcels find their way. Open destination.",
    ability: "Worker: Give an opponent 2 cards, discard any from hand, draw up to hand limit.",
  },
  "University": {
    description: "The pinnacle of learning. Permanent worker.",
    ability: "Worker: Discard 1 card from city, get its cost back +1 any resource +1 VP. Worker stays permanently.",
  },
  "Queen": {
    description: "Her Majesty graces a card with her presence.",
    ability: "Worker: Play any card worth 3 VP or less from your hand or Meadow for free.",
  },

  // === BLUE / GOVERNANCE ===
  "Clock Tower": {
    description: "Its bells mark the changing seasons.",
    ability: "When played: Receive 3 VP tokens. Before each Prepare for Season, remove 1 to activate a basic/forest location.",
  },
  "Courthouse": {
    description: "Where order is maintained in the valley.",
    ability: "Ongoing: Gain 1 twig, resin, or pebble each time you play a Construction.",
  },
  "Crane": {
    description: "A towering machine for heavy lifting.",
    ability: "Ongoing: Discard Crane from city to reduce a Construction's cost by 3 of any resource.",
  },
  "Dungeon": {
    description: "A dark cell beneath the city.",
    ability: "Ongoing: Place a Critter from your city beneath Dungeon to reduce a played card's cost by 3.",
  },
  "Historian": {
    description: "A keeper of records and stories.",
    ability: "Ongoing: Draw 1 card after playing any card (Construction or Critter).",
  },
  "Innkeeper": {
    description: "A hospitable host with a warm hearth.",
    ability: "Ongoing: Discard Innkeeper to reduce a Critter's cost by 3 berries.",
  },
  "Judge": {
    description: "A fair arbiter of disputes.",
    ability: "Ongoing: When playing a card, replace 1 resource in its cost with 1 of a different type.",
  },
  "Shopkeeper": {
    description: "A keen-eyed merchant of fine wares.",
    ability: "Ongoing: Gain 1 berry each time you play a Critter.",
  },

  // === TAN / TRAVELER ===
  "Ruins": {
    description: "Crumbling walls with hidden potential. Free to play.",
    ability: "When played: Discard a Construction from your city, gain its cost back, draw 2 cards.",
  },
  "Bard": {
    description: "A wandering minstrel with tales to tell.",
    ability: "When played: Discard up to 5 cards from hand, gain 1 VP per card discarded.",
  },
  "Fool": {
    description: "A mischievous trickster. Worth -2 VP.",
    ability: "When played: Place into an OPPONENT's city (not yours).",
  },
  "Postal Pigeon": {
    description: "Swift delivery through the canopy.",
    ability: "When played: Reveal 2 cards from deck, play 1 worth 3 VP or less for free, discard the other.",
  },
  "Ranger": {
    description: "A skilled scout of the deep woods.",
    ability: "When played: Move 1 of your deployed workers to a new valid location. Unlocks 2nd Dungeon cell.",
  },
  "Shepherd": {
    description: "A gentle guardian of the flock.",
    ability: "When played: Gain 3 berries. +1 VP per VP token on your Chapel.",
  },
  "Undertaker": {
    description: "A solemn caretaker of the departed.",
    ability: "When played: Discard 3 cards from Meadow (replenished), then draw 1 Meadow card to hand. Unlocks 2nd Cemetery plot.",
  },
  "Wanderer": {
    description: "A free spirit who roams the valley.",
    ability: "When played: Draw 3 cards. Does NOT occupy a city space.",
  },
}

export const LOCATION_INFO: Record<string, string> = {
  // Basic locations
  "basic_3twigs": "Gain 3 Twigs",
  "basic_2twigs_1card": "Gain 2 Twigs and draw 1 Card",
  "basic_2resin": "Gain 2 Resin",
  "basic_1resin_1card": "Gain 1 Resin and draw 1 Card",
  "basic_2cards_1point": "Draw 2 Cards and gain 1 VP",
  "basic_1pebble": "Gain 1 Pebble",
  "basic_1berry_1card": "Gain 1 Berry and draw 1 Card",
  "basic_1berry": "Gain 1 Berry",

  // Forest locations
  "forest_01": "Gain 2 Twigs and 2 Resin",
  "forest_02": "Gain 2 Resin and draw 1 Card",
  "forest_03": "Gain 1 Twig, 1 Resin, and 1 Pebble",
  "forest_04": "Gain 2 Twigs and 1 Pebble",
  "forest_05": "Gain 1 Pebble and 1 Berry",
  "forest_06": "Gain 2 Berries and draw 1 Card",
  "forest_07": "Gain 3 Twigs and draw 1 Card",
  "forest_08": "Gain 1 Twig, 1 Resin, and 1 Berry",
  "forest_09": "Gain 3 Berries",
  "forest_10": "Copy any basic or forest location reward",
  "forest_11": "Discard up to 3 cards, gain 1 resource of any type per card",

  // Haven
  "haven": "Discard 2 cards to gain 1 resource of any type",

  // Journey
  "journey_2vp": "Discard cards to score 2 VP (Autumn only)",
  "journey_3vp": "Discard cards to score 3 VP (Autumn only, exclusive)",
  "journey_4vp": "Discard cards to score 4 VP (Autumn only, exclusive)",
  "journey_5vp": "Discard cards to score 5 VP (Autumn only, exclusive)",
}
