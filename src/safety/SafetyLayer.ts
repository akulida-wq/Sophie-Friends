import type { Game } from '../core/Game'
import type { InteractionSystem } from '../interaction/InteractionSystem'
import type { SophieBubble } from '../dialogue/SophieBubble'
import type { StoryEngine } from '../story/StoryEngine'

/**
 * Sophie's support logic (never punitive):
 * - Inactivity in EXPLORE/CHOICE → softly highlight one object + a gentle line.
 * - Repeated avoidant (redirect) choices → shortened supportive branch.
 * Thresholds and lines come from the story JSON's `safety` block.
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
    story.onChoice = (_id, redirect) => this.onChoice(redirect)
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
    const state = this.game.states.state
    if (state !== 'EXPLORE' && state !== 'CHOICE') {
      this.idleSeconds = 0
      return
    }

    this.idleSeconds += dt
    const { idle_hint_sec, idle_hint_line } = this.story.safetyConfig
    if (!this.hintShown && this.idleSeconds >= idle_hint_sec) {
      this.hintShown = true
      this.showIdleHint(idle_hint_line ?? 'A little step is enough.')
    }
  }

  private showIdleHint(line: string): void {
    // Highlight the nearest interactable — one gentle suggestion, no pressure.
    let nearest = null
    let nearestDist = Infinity
    for (const item of this.interaction.list()) {
      const d = item.object.position.distanceTo(this.game.sophie.position)
      if (d < nearestDist) {
        nearest = item
        nearestDist = d
      }
    }
    if (nearest) this.interaction.setHint(nearest)
    console.log(`[Safety] idle hint (highlight: ${nearest?.id ?? 'none'})`)
    this.bubble.say(line)
  }

  private onChoice(redirect: boolean): void {
    this.notifyActivity()
    if (!redirect) {
      this.avoidStreak = 0
      return
    }
    this.avoidStreak++
    const { avoid_streak_soft_branch, soft_branch_id } = this.story.safetyConfig
    console.log(`[Safety] avoidant choice streak: ${this.avoidStreak}/${avoid_streak_soft_branch}`)
    if (this.avoidStreak >= avoid_streak_soft_branch && soft_branch_id) {
      this.avoidStreak = 0
      this.story.jumpTo(soft_branch_id)
    }
  }
}
