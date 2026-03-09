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
  action_type: 'place_worker' | 'play_card' | 'prepare_for_season' | 'claim_event'
  location_id?: string
  card_name?: string
  source?: 'hand' | 'meadow'
  meadow_index?: number
  use_paired_construction?: boolean
  event_id?: string
  discard_cards?: string[]
}

export interface LobbyState {
  status: 'waiting'
  players: Record<string, string>  // player_id -> name
  max_players: number
  current_count: number
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
  haven_locations: LocationData[]
  journey_locations: LocationData[]
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

// Move evaluation from ed-ai service
export type MoveQuality = 'brilliant' | 'good' | 'inaccuracy' | 'mistake' | 'blunder'

export interface MoveAlternative {
  action: ValidAction
  description: string
  score_delta: number
}

export interface MoveEvaluation {
  quality: MoveQuality
  score: number
  explanation: string
  alternatives: MoveAlternative[]
}

// Player profile and leaderboard
export type PlayerClassification = 'Seedling' | 'Wanderer' | 'Forager' | 'Ranger' | 'Elder'

export interface GameHistoryEntry {
  game_id: string
  date: string
  players: number
  placement: number
  score: number
  opponent_scores: number[]
}

export interface PlayerProfile {
  username: string
  elo: number
  classification: PlayerClassification
  games_played: number
  win_rate: number
  avg_move_accuracy: number
  elo_history: number[]
  recent_games: GameHistoryEntry[]
}

export interface LeaderboardEntry {
  rank: number
  username: string
  elo: number
  classification: PlayerClassification
  games_played: number
  win_rate: number
}

export function getClassification(elo: number): PlayerClassification {
  if (elo >= 1600) return 'Elder'
  if (elo >= 1400) return 'Ranger'
  if (elo >= 1200) return 'Forager'
  if (elo >= 1000) return 'Wanderer'
  return 'Seedling'
}
