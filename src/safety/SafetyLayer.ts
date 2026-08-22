import type { Game } from '../core/Game'
import type { InteractionSystem } from '../interaction/InteractionSystem'
import type { SophieBubble } from '../dialogue/SophieBubble'
import type { StoryEngine } from '../story/StoryEngine'
import { audio } from '../audio/AudioSystem'

/** Подсказка при бездействии: текст/голос задаёт main из props.json;
 *  null = подсказывать нечего (после знакомства с Бруно гуляем свободно). */
export type IdleHint = { line: string; voice?: string; target?: string } | null

const IDLE_HINT_SEC = 30
const IDLE_HINT_MAX_PER_SESSION = 3

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
  private hintsGiven = 0
  /** Что сказать при бездействии (ставит main; null — молчим). */
  idleHint: () => IdleHint = () => null

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
    if (
      !this.hintShown &&
      this.hintsGiven < IDLE_HINT_MAX_PER_SESSION &&
      this.idleSeconds >= IDLE_HINT_SEC
    ) {
      this.hintShown = true
      this.showIdleHint()
    }
  }

  private showIdleHint(): void {
    const hint = this.idleHint()
    if (!hint || audio.isVoicePlaying) return
    this.hintsGiven++
    // Подсветить, к кому идти — одна мягкая подсказка, без давления.
    const target = hint.target
      ? this.interaction.list().find((i) => i.id === hint.target) ?? null
      : this.interaction.nearest()
    if (target) this.interaction.setHint(target)
    console.log(`[Safety] idle hint ${this.hintsGiven}/${IDLE_HINT_MAX_PER_SESSION} (highlight: ${target?.id ?? 'none'})`)
    audio.voice(hint.voice)
    void this.bubble.say(hint.line)
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
