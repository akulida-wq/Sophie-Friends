import type { Game } from '../core/Game'
import type { InteractionSystem } from '../interaction/InteractionSystem'
import type { SophieBubble } from '../dialogue/SophieBubble'
import type { StoryEngine } from '../story/StoryEngine'

const DEFAULT_IDLE_HINT = 'A little step is enough.'

/**
 * Sophie's support logic (never punitive):
 * - Inactivity in free-roam EXPLORE → softly highlight one object + a
 *   gentle line. (Mission scenes pace themselves — the minigame has its
 *   own hesitation fallback from JSON — so the generic hint stays out of
 *   the way while the story is active.)
 * - Avoidant choices (`"avoidant": true`) in a row → shortened supportive
 *   branch (`soft_branch_target` from the JSON safety block).
 */
export class SafetyLayer {
  private idleSeconds = 0
  private avoidStreak = 0
  private hintShown = false

  constructor(
    private readonly game: Game,
    private readonly interaction: InteractionSystem,
    private readonly bubble: SophieBubble,
    private readonly story: StoryEngine,
  ) {
    story.onChoice = (_id, _redirect, avoidant) => this.onChoice(avoidant)
  }

  /** Wire to every input source (taps, choice picks). */
  notifyActivity(): void {
    this.idleSeconds = 0
    if (this.hintShown) {
      this.interaction.setHint(null)
      this.hintShown = false
    }
  }

  update(dt: number): void {
    if (!this.game.states.is('EXPLORE') || this.story.isActive) {
      this.idleSeconds = 0
      return
    }

    this.idleSeconds += dt
    if (!this.hintShown && this.idleSeconds >= this.story.safetyConfig.idle_hint_sec) {
      this.hintShown = true
      this.showIdleHint()
    }
  }

  private showIdleHint(): void {
    // Highlight the nearest interactable — one gentle suggestion, no pressure.
    const nearest = this.interaction.nearest()
    if (nearest) this.interaction.setHint(nearest)
    console.log(`[Safety] idle hint (highlight: ${nearest?.id ?? 'none'})`)
    this.bubble.say(DEFAULT_IDLE_HINT)
  }

  private onChoice(avoidant: boolean): void {
    this.notifyActivity()
    if (!avoidant) {
      this.avoidStreak = 0
      return
    }
    this.avoidStreak++
    const { avoid_streak, soft_branch_target } = this.story.safetyConfig
    console.log(`[Safety] avoidant choice streak: ${this.avoidStreak}/${avoid_streak}`)
    if (this.avoidStreak >= avoid_streak && soft_branch_target) {
      this.avoidStreak = 0
      this.story.jumpTo(soft_branch_target)
    }
  }
}
