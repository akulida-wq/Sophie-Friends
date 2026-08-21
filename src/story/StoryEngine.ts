import type * as THREE from 'three'
import type { Game } from '../core/Game'
import type { Mood } from '../core/Mood'
import type { FollowCamera } from '../camera/FollowCamera'
import type { CinematicCamera, CinematicPreset } from '../camera/CinematicCamera'
import { audio } from '../audio/AudioSystem'
import type { RewardGlow } from '../dialogue/RewardGlow'
import type { ChoicePanel } from '../dialogue/ChoicePanel'
import type { SophieBubble } from '../dialogue/SophieBubble'
import type { TapCue } from '../dialogue/TapCue'
import type { InteractionSystem } from '../interaction/InteractionSystem'
import type { BrunoView } from '../interaction/BrunoView'
import { iconFor, labelFromId } from '../dialogue/icons'
import type { VideoOverlay } from '../dialogue/VideoOverlay'
import type {
  ChoiceScene,
  CinematicChoiceScene,
  CinematicScene,
  EndMenuScene,
  MinigameScene,
  StoryAction,
  StoryChoice,
  StoryMission,
  StoryScene,
} from './types'

export interface StoryActors {
  /** Actor id (as used in JSON) → scene object. */
  resolve: (actorId: string) => THREE.Object3D | null
}

export interface StoryEngineDeps {
  game: Game
  followCamera: FollowCamera
  cinematicCamera: CinematicCamera
  choicePanel: ChoicePanel
  bubble: SophieBubble
  videoOverlay?: VideoOverlay
  tapCue: TapCue
  interaction: InteractionSystem
  brunoView: BrunoView
  mood: Mood
  actors: StoryActors
  /** Play a named animation clip on an actor; false = not handled (stub). */
  playActorAnim?: (actorId: string, anim: string) => boolean
  rewardGlow?: RewardGlow
}

/** Minigame option id → world interactable id. */
const MINIGAME_PROP: Record<string, string> = {
  roll_ball: 'ball',
  place_block: 'blocks',
  draw_chalk: 'chalk',
}

/**
 * Drives the full mission from story JSON. Content (lines, choices,
 * branching, safety thresholds) lives ONLY in the JSON — swapping the file
 * requires zero code changes here.
 */
export class StoryEngine {
  private readonly mission: StoryMission
  private active = false
  /** Bumped on soft-branch jumps / restarts so stale continuations cancel. */
  private generation = 0
  /** Per-scene count of gentle redirects (drives simplify_after_misses). */
  private missCounts = new Map<string, number>()
  private minigameTimer: number | null = null
  /** Каким предметом ребёнок сыграл в минигре — от него зависят реплики. */
  private lastMinigameProp: string | null = null
  /** Called when a choice is picked; SafetyLayer listens for avoidance. */
  onChoice: ((choiceId: string, redirect: boolean, avoidant: boolean) => void) | null = null

  constructor(
    private readonly deps: StoryEngineDeps,
    mission: StoryMission,
  ) {
    this.mission = mission
  }

  get isActive(): boolean {
    return this.active
  }

  get safetyConfig() {
    return this.mission.safety
  }

  start(): void {
    if (this.active) return
    this.active = true
    this.beginRun()
  }

  /** end_menu "Play again" — fresh run without leaving the mission. */
  restart(): void {
    if (!this.active) return
    console.log('[Story] restart')
    this.beginRun()
  }

  /** SafetyLayer jumps here after repeated avoidant choices. */
  jumpTo(sceneId: string): void {
    if (!this.active) return
    console.log(`[Story] soft branch -> ${sceneId}`)
    this.invalidatePending()
    this.runScene(sceneId)
  }

  private beginRun(): void {
    this.invalidatePending()
    this.missCounts.clear()
    this.lastMinigameProp = null
    const initialState = this.mission.actors?.bruno?.initial_state ?? 'withdrawn'
    this.deps.brunoView.setState(initialState)
    console.log(`[Story] mission "${this.mission.mission}" started`)
    this.runScene(this.entrySceneId())
  }

  /** Cancel pending continuations (bubbles, timers, cues, minigame). */
  private invalidatePending(): void {
    this.generation++
    this.deps.choicePanel.hide()
    this.deps.bubble.hideNow()
    this.deps.tapCue.hide()
    this.deps.interaction.overrideActivate = null
    this.deps.interaction.setHint(null)
    if (this.minigameTimer !== null) {
      window.clearTimeout(this.minigameTimer)
      this.minigameTimer = null
    }
  }

  private entrySceneId(): string {
    return this.mission.entry ?? this.mission.scenes[0].id
  }

  private findScene(id: string): StoryScene | null {
    return this.mission.scenes.find((s) => s.id === id) ?? null
  }

  private runScene(id: string): void {
    if (id === 'end') return this.finish()
    const scene = this.findScene(id)
    if (!scene) {
      console.warn(`[Story] scene "${id}" not found — returning to exploration`)
      return this.finish()
    }
    console.log(`[Story] scene: ${scene.id} (${scene.type})`)
    this.deps.mood.apply(scene.mood)
    if (scene.bruno_state) this.deps.brunoView.setState(scene.bruno_state)

    switch (scene.type) {
      case 'cinematic':
        return this.runCinematic(scene)
      case 'choice':
        return this.runChoice(scene, scene.setup_actions)
      case 'cinematic_choice':
        return this.runChoice(scene, scene.intro_actions)
      case 'minigame':
        return this.runMinigame(scene)
      case 'end_menu':
        return this.runEndMenu(scene)
    }
  }

  // --- Cinematic scenes -------------------------------------------------

  private runCinematic(scene: CinematicScene): void {
    this.deps.game.states.transition('CINEMATIC')
    const gen = this.generation
    this.deps.followCamera.setEnabled(false)
    this.deps.cinematicCamera.play(this.parsePreset(scene.camera)).then(() => {
      if (gen !== this.generation) return
      this.playActions(scene.actions, gen, () => {
        if (scene.advance?.on === 'tap_cue') {
          // Wait calmly (no timer) for a tap on the pulsing cue.
          const cueTarget = this.resolveCueTarget(scene.advance.cue_targets)
          this.deps.tapCue.show(cueTarget, () => {
            if (gen === this.generation) this.runScene(scene.next)
          })
        } else {
          this.runScene(scene.next)
        }
      })
    })
  }

  private resolveCueTarget(targets: string[] | undefined): THREE.Object3D {
    for (const id of targets ?? []) {
      const obj = this.deps.actors.resolve(id)
      if (obj) return obj
    }
    return this.deps.actors.resolve('bruno') ?? this.deps.game.sophie
  }

  // --- Choice / cinematic_choice scenes ---------------------------------

  private runChoice(scene: ChoiceScene | CinematicChoiceScene, preActions?: StoryAction[]): void {
    const gen = this.generation
    const showPanel = () => {
      if (gen !== this.generation) return
      this.deps.game.states.transition('CHOICE')
      this.deps.cinematicCamera.stop()
      this.deps.followCamera.setEnabled(true)
      this.applyChoiceCamera(scene.camera)
      this.showChoices(scene)
    }

    if (preActions && preActions.length > 0) {
      // Stage the intro like a mini-cinematic, then reveal the cards.
      this.deps.game.states.transition('CINEMATIC')
      this.deps.followCamera.setEnabled(false)
      this.deps.cinematicCamera.play(this.parsePreset(scene.camera)).then(() => {
        if (gen !== this.generation) return
        this.playActions(preActions, gen, showPanel)
      })
    } else {
      showPanel()
    }
  }

  private showChoices(scene: ChoiceScene | CinematicChoiceScene): void {
    const gen = this.generation
    let choices = scene.choices
    const simplify = scene.simplify_after_misses
    if (simplify && (this.missCounts.get(scene.id) ?? 0) >= simplify.count) {
      choices = choices.filter((c) => simplify.keep_choice_ids.includes(c.id))
      console.log(`[Story] simplified choices for "${scene.id}" -> ${choices.map((c) => c.id).join(', ')}`)
    }

    audio.voice(scene.prompt?.voice)
    this.deps.choicePanel.show(
      {
        promptIcon: scene.prompt?.icon ? iconFor(scene.prompt.icon) : undefined,
        promptText: scene.prompt?.line,
        choices: choices.slice(0, 3).map((c) => ({
          id: c.id,
          icon: iconFor(c.icon),
          label: c.label ?? labelFromId(c.id),
        })),
      },
      (choiceId) => {
        if (gen !== this.generation) return
        const choice = scene.choices.find((c) => c.id === choiceId)
        if (!choice) return
        this.handlePick(scene, choice, gen)
      },
    )
  }

  private handlePick(
    scene: ChoiceScene | CinematicChoiceScene,
    choice: StoryChoice,
    gen: number,
  ): void {
    const flags = [choice.redirect && 'redirect', choice.avoidant && 'avoidant']
      .filter(Boolean)
      .join(', ')
    console.log(`[Story] choice: ${choice.id}${flags ? ` (${flags})` : ''}`)

    if (choice.redirect && !choice.avoidant) {
      this.missCounts.set(scene.id, (this.missCounts.get(scene.id) ?? 0) + 1)
    }
    if (choice.bruno_state) this.deps.brunoView.setState(choice.bruno_state)

    this.onChoice?.(choice.id, choice.redirect === true, choice.avoidant === true)
    // A safety jump inside onChoice bumps the generation — this
    // continuation is then stale and must not run the old branch.
    if (gen !== this.generation) return

    const proceed = () => {
      if (gen !== this.generation) return
      if (choice.outcome_actions && choice.outcome_actions.length > 0) {
        this.playActions(choice.outcome_actions, gen, () => this.runScene(choice.next))
      } else {
        this.runScene(choice.next)
      }
    }
    if (choice.sophie_line) {
      audio.voice(choice.voice)
      this.deps.bubble.say(choice.sophie_line).then(proceed)
    } else proceed()
  }

  // --- Minigame ---------------------------------------------------------

  private runMinigame(scene: MinigameScene): void {
    // Playable: the child explores and taps a cooperative prop. Controls on.
    this.deps.game.states.transition('EXPLORE')
    this.deps.cinematicCamera.stop()
    this.deps.followCamera.setEnabled(true)
    this.deps.followCamera.focusOn(null)
    const gen = this.generation
    const verbs = scene.mechanics.options.map((o) => o.verb).join(' / ')
    console.log(`[Minigame] ${scene.mechanics.interaction}: ${verbs}`)

    const propIds = scene.mechanics.options
      .map((o) => MINIGAME_PROP[o.id])
      .filter((id): id is string => id !== undefined)

    this.deps.interaction.overrideActivate = (id) => {
      if (gen !== this.generation) return false
      if (!propIds.includes(id)) return false
      const option = scene.mechanics.options.find((o) => MINIGAME_PROP[o.id] === id)
      console.log(`[Minigame] cooperative action: ${option?.id ?? id}`)
      this.lastMinigameProp = id
      this.deps.interaction.overrideActivate = null
      if (this.minigameTimer !== null) {
        window.clearTimeout(this.minigameTimer)
        this.minigameTimer = null
      }
      this.deps.interaction.setHint(null)
      // Success feedback plays as a short staged moment.
      this.deps.game.states.transition('CINEMATIC')
      this.deps.followCamera.setEnabled(false)
      this.deps.cinematicCamera.play(this.parsePreset('wide')).then(() => {
        if (gen !== this.generation) return
        this.playActions(scene.success.feedback_actions, gen, () =>
          this.runScene(scene.success.next),
        )
      })
      return true
    }

    // Hesitation fallback: one gentle nudge, only if nothing happened yet.
    const fallback = scene.hesitation_fallback
    if (fallback) {
      this.minigameTimer = window.setTimeout(() => {
        this.minigameTimer = null
        if (gen !== this.generation) return
        console.log('[Minigame] hesitation fallback')
        this.playActions(fallback.actions, gen, () => {})
      }, fallback.after_sec * 1000)
    }
  }

  // --- End menu ---------------------------------------------------------

  private runEndMenu(scene: EndMenuScene): void {
    const gen = this.generation
    const showMenu = () => {
      if (gen !== this.generation) return
      this.deps.game.states.transition('CHOICE')
      this.deps.cinematicCamera.stop()
      this.deps.followCamera.setEnabled(true)
      this.deps.followCamera.focusOn(null)
      this.deps.choicePanel.show(
        {
          choices: scene.options.slice(0, 3).map((o) => ({
            id: o.id,
            icon: iconFor(o.icon),
            label: o.label,
          })),
        },
        (optionId) => {
          if (gen !== this.generation) return
          const option = scene.options.find((o) => o.id === optionId)
          if (!option) return
          console.log(`[Story] end menu: ${option.id} (${option.action})`)
          this.handleEndMenuAction(option.action, showMenu)
        },
      )
    }

    if (scene.actions && scene.actions.length > 0) {
      this.deps.game.states.transition('CINEMATIC')
      this.deps.followCamera.setEnabled(false)
      this.deps.cinematicCamera.play(this.parsePreset(scene.camera)).then(() => {
        if (gen !== this.generation) return
        this.playActions(scene.actions ?? [], gen, showMenu)
      })
    } else {
      showMenu()
    }
  }

  private handleEndMenuAction(action: string, reshowMenu: () => void): void {
    switch (action) {
      case 'restart_mission':
        return this.restart()
      case 'to_hub_stub':
        // Soft "coming soon" — warm words, no locks, no error styling.
        audio.voice('s8_sophie_hub_soon')
        this.deps.bubble
          .say('Another friend is getting ready to meet you. We can visit them soon. 🌿')
          .then(reshowMenu)
        return
      case 'free_roam':
      default:
        return this.finish()
    }
  }

  // --- Shared action player --------------------------------------------

  /** Plays heterogeneous staged actions sequentially (grey-phase stubs). */
  private playActions(actions: StoryAction[], gen: number, done: () => void): void {
    const queue = [...actions]
    const step = () => {
      if (gen !== this.generation) return
      const action = queue.shift()
      if (!action) return done()

      if (action.video) {
        console.log(`[Cinematic] video insert: ${action.video}`)
        if (this.deps.videoOverlay) {
          this.deps.videoOverlay.play(action.video).then(() => {
            if (gen === this.generation) step()
          })
        } else {
          step()
        }
        return
      }
      if (action.line) {
        // фраза может зависеть от предмета минигры (мяч/кубики/мелки)
        const variant =
          (this.lastMinigameProp && action.line_variants?.[this.lastMinigameProp]) || action
        console.log(`[Cinematic] ${action.actor ?? 'voice'}: "${variant.line}"`)
        audio.voice(variant.voice)
        this.deps.bubble
          .say(variant.line ?? action.line, undefined, action.actor === 'bruno' ? 'bruno' : 'sophie')
          .then(step)
        return
      }
      if (action.mood) {
        this.deps.mood.apply(action.mood)
        step()
        return
      }
      if (action.highlight) {
        const target = this.deps.interaction.nearest(['bruno'])
        if (target) this.deps.interaction.setHint(target)
        console.log(`[Cinematic] highlight ${action.highlight} -> ${target?.id ?? 'none'}`)
        step()
        return
      }
      if (action.reward) {
        console.log(`[Cinematic] reward: ${action.reward.type} (${action.reward.style})`)
        this.deps.mood.setColorTemp('warm')
        audio.ui('reward')
        this.deps.rewardGlow?.shine()
        window.setTimeout(step, 1600) // дать сиянию раскрыться
        return
      }
      if (action.move) {
        console.log(`[Stage] ${action.actor} move "${action.move}" (stub)`)
        // A move can carry its own clip (e.g. Sophie walks in playing Walk).
        if (action.actor && action.anim) this.deps.playActorAnim?.(action.actor, action.anim)
        window.setTimeout(step, 600)
        return
      }
      if (action.anim) {
        // проп-анимация чужого предмета (мяч укатился, а играли мелками) — мимо
        if (!action.actor && action.prop && this.lastMinigameProp &&
            action.prop !== this.lastMinigameProp) {
          step()
          return
        }
        const actorId = action.actor ?? action.prop ?? 'stage'
        const played = action.actor
          ? this.deps.playActorAnim?.(action.actor, action.anim) === true
          : false
        console.log(`[Cinematic] ${actorId} plays anim "${action.anim}"${played ? '' : ' (stub)'}`)
        window.setTimeout(step, 900)
        return
      }
      if (action.props) {
        console.log(`[Stage] props present: ${action.props.join(', ')}`)
        step()
        return
      }
      step() // unknown action shape — skip gracefully
    }
    step()
  }

  // --- Camera helpers ---------------------------------------------------

  /**
   * Story JSON camera strings → cinematic presets: "wide",
   * "closeup_<actor>", "over_shoulder[_<actor>]", "follow_<actor>".
   */
  private parsePreset(raw: string | undefined): CinematicPreset {
    const fallback = this.deps.actors.resolve('bruno') ?? this.deps.game.sophie
    if (raw?.startsWith('closeup_')) {
      return { kind: 'closeup', actor: this.deps.actors.resolve(raw.slice(8)) ?? fallback }
    }
    if (raw?.startsWith('over_shoulder')) {
      const actorId = raw.replace(/^over_shoulder_?/, '')
      return {
        kind: 'over_shoulder',
        actor: (actorId && this.deps.actors.resolve(actorId)) || fallback,
        companion: this.deps.game.sophie,
      }
    }
    if (raw?.startsWith('follow_')) {
      return { kind: 'wide', actor: this.deps.actors.resolve(raw.slice(7)) ?? fallback }
    }
    return { kind: 'wide', actor: fallback }
  }

  /** CHOICE scenes use the softer follow-camera focus ease-in. */
  private applyChoiceCamera(preset: string | undefined): void {
    if (preset?.startsWith('closeup_') || preset === 'over_shoulder') {
      const actorId = preset.startsWith('closeup_') ? preset.slice(8) : 'bruno'
      this.deps.followCamera.focusOn(this.deps.actors.resolve(actorId))
    } else {
      this.deps.followCamera.focusOn(null)
    }
  }

  /** Мягко завершить миссию по желанию пользователя (кнопка выхода). */
  abort(): void {
    if (!this.active) return
    this.deps.bubble.hideNow()
    this.finish()
  }

  /** Вызывается после завершения миссии (любым способом). */
  onFinished: (() => void) | null = null

  private finish(): void {
    this.invalidatePending()
    this.active = false
    this.deps.cinematicCamera.stop()
    this.deps.followCamera.focusOn(null)
    this.deps.followCamera.setEnabled(true) // eases home from the last shot
    this.deps.game.states.transition('EXPLORE')
    // персонажи возвращаются к спокойным айдлам — никаких вечных танцев
    this.deps.brunoView.setState(this.deps.brunoView.currentState)
    this.deps.playActorAnim?.('sophie', 'Idle')
    this.onFinished?.()
    console.log('[Story] segment complete — back to exploration')
  }
}
