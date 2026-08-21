/**
 * Story JSON schema for the full mission file (see docs/03_TECH_SPEC.md).
 * Content lives ONLY in the JSON — the psychologist's file must drop in
 * with zero code changes. Schema evolution happens here + in the engine.
 */

export type ColorTemp = 'cool' | 'neutral' | 'warm'

export interface MoodSpec {
  music?: string
  color_temp?: ColorTemp
  note?: string
}

/** One staged step inside a scene — heterogeneous by design. */
export interface StoryAction {
  /** Кино-вставка: id ролика из /video/<id>.mp4 */
  video?: string
  actor?: string
  anim?: string
  line?: string
  voice?: string
  move?: string
  prop?: string
  props?: string[]
  mood?: MoodSpec
  reward?: { type?: string; style?: string; note?: string }
  highlight?: string
  style?: string
  note?: string
}

export interface StoryChoice {
  id: string
  icon: string
  label?: string
  next: string
  sophie_line?: string
  voice?: string
  /** Gentle non-match — loops back, may trigger choice simplification. */
  redirect?: boolean
  /** Avoidant pick — counted by SafetyLayer toward the soft branch. */
  avoidant?: boolean
  bruno_state?: string
  outcome_actions?: StoryAction[]
  note?: string
}

interface SceneBase {
  id: string
  camera?: string
  mood?: MoodSpec
  bruno_state?: string
  duration_hint_sec?: number
  note?: string
}

export interface CinematicScene extends SceneBase {
  type: 'cinematic'
  actions: StoryAction[]
  /** tap_cue: wait for a soft pulsing cue tap before continuing (no timer). */
  advance?: { on: 'tap_cue'; cue_targets?: string[] }
  next: string
}

export interface ChoiceScene extends SceneBase {
  type: 'choice'
  prompt?: { line?: string; voice?: string; icon?: string }
  setup_actions?: StoryAction[]
  choices: StoryChoice[]
  simplify_after_misses?: { count: number; keep_choice_ids: string[] }
}

export interface CinematicChoiceScene extends SceneBase {
  type: 'cinematic_choice'
  prompt?: { line?: string; voice?: string; icon?: string }
  intro_actions?: StoryAction[]
  choices: StoryChoice[]
  simplify_after_misses?: { count: number; keep_choice_ids: string[] }
}

export interface MinigameScene extends SceneBase {
  type: 'minigame'
  mechanics: {
    interaction: string
    options: Array<{ id: string; verb: string }>
  }
  success: {
    condition: string
    feedback_actions: StoryAction[]
    next: string
  }
  hesitation_fallback?: {
    after_sec: number
    actions: StoryAction[]
  }
}

export interface EndMenuScene extends SceneBase {
  type: 'end_menu'
  actions?: StoryAction[]
  options: Array<{ id: string; icon: string; label: string; action: string }>
}

export type StoryScene =
  | CinematicScene
  | ChoiceScene
  | CinematicChoiceScene
  | MinigameScene
  | EndMenuScene

export interface StorySafetyConfig {
  idle_hint_sec: number
  /** Avoidant choices in a row before the soft branch. */
  avoid_streak: number
  /** Scene id of the shortened supportive branch. */
  soft_branch_target?: string
}

export interface StoryMission {
  mission: string
  title?: string
  entry?: string
  safety: StorySafetyConfig
  actors?: Record<string, { model?: string; initial_state?: string; count?: number }>
  bruno_states?: string[]
  scenes: StoryScene[]
}
