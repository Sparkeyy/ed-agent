export interface ResourceBank {
  twig: number
  resin: number
  pebble: number
  berry: number
}

export interface CardData {
  name: string
  card_type: 'tan_traveler' | 'green_production' | 'red_destination' | 'blue_governance' | 'purple_prosperity'
  category: 'critter' | 'construction'
  cost: ResourceBank
  base_points: number
  unique: boolean
  paired_with: string | null
  occupies_city_space: boolean
  is_open_destination: boolean
}

export interface PlayerData {
  id: string
  name: string
  resources: ResourceBank
  city: CardData[]
  workers_total: number
  workers_placed: number
  workers_deployed: string[]
  season: 'winter' | 'spring' | 'summer' | 'autumn'
  score: number
  has_passed: boolean
  hand?: CardData[]
  hand_size: number
}

export interface LocationData {
  id: string
  name: string
  location_type: string
  exclusive: boolean
  workers: string[]
}

export interface ValidAction {
  action_type: 'place_worker' | 'play_card' | 'prepare_for_season'
  location_id?: string
  card_name?: string
  source?: 'hand' | 'meadow'
  meadow_index?: number
  use_paired_construction?: boolean
}

export interface GameState {
  game_id: string
  turn_number: number
  current_player_id: string | null
  players: PlayerData[]
  meadow: CardData[]
  deck_size: number
  discard_size: number
  events: {
    basic_events: Record<string, any>
    special_events: Record<string, any>
  }
  forest_locations: LocationData[]
  basic_locations: LocationData[]
  game_over: boolean
  valid_actions: ValidAction[]
}

export type CardType = CardData['card_type']
export type Season = PlayerData['season']

export const CARD_TYPE_LABELS: Record<CardType, string> = {
  tan_traveler: 'Traveler',
  green_production: 'Production',
  red_destination: 'Destination',
  blue_governance: 'Governance',
  purple_prosperity: 'Prosperity',
}

export const SEASON_ORDER: Season[] = ['winter', 'spring', 'summer', 'autumn']

export const RESOURCE_ICONS: Record<keyof ResourceBank, string> = {
  twig: '\u{1FAB5}',
  resin: '\u{1F4A7}',
  pebble: '\u{1FAA8}',
  berry: '\u{1FAD0}',
}
