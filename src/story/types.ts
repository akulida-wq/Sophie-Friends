/**
 * Story JSON schema (see docs/03_TECH_SPEC.md). The full 8-scene mission
 * JSON from the psychologist must drop in with ZERO code changes — any
 * schema evolution happens here and in the engine, never in content.
 */

export interface StoryChoice {
  id: string
  /** Icon key resolved by the dialogue icon registry (e.g. "face_lonely"). */
  icon: string
  /** Scene id to go to after this choice. */
  next: string
  sophie_line?: string
  /** Gentle non-match: loops back per `next`, counted by the SafetyLayer. */
  redirect?: boolean
  /** Optional short card label; falls back to a prettified id. */
  label?: string
}

export interface ChoiceScene {
  id: string
  type: 'choice'
  camera?: string
  prompt?: { icon?: string; voice?: string }
  choices: StoryChoice[]
}

export interface CinematicAction {
  actor: string
  anim?: string
  line?: string
}

export interface CinematicScene {
  id: string
  type: 'cinematic'
  camera?: string
  actions: CinematicAction[]
  next: string
  bruno_state?: string
}

export type StoryScene = ChoiceScene | CinematicScene

export interface StorySafetyConfig {
  idle_hint_sec: number
  /** Avoidant (redirect) choices in a row before the soft branch. */
  avoid_streak_soft_branch: number
  /** Scene id of the shortened supportive branch. */
  soft_branch_id?: string
  idle_hint_line?: string
}

export interface StoryMission {
  mission: string
  scenes: StoryScene[]
  safety: StorySafetyConfig
}
