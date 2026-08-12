import type * as THREE from 'three'
import type { Game } from '../core/Game'
import type { FollowCamera } from '../camera/FollowCamera'
import type { CinematicCamera, CinematicPreset } from '../camera/CinematicCamera'
import type { ChoicePanel } from '../dialogue/ChoicePanel'
import type { SophieBubble } from '../dialogue/SophieBubble'
import { iconFor, labelFromId } from '../dialogue/icons'
import type { CinematicScene, ChoiceScene, StoryMission, StoryScene } from './types'

export interface StoryActors {
  /** Actor id (as used in JSON) → scene object. */
  resolve: (actorId: string) => THREE.Object3D | null
}

/** Applied to Bruno's placeholder as his state warms up (grey-phase stub
 *  for pose/animation changes — cold and closed → warmer and open). */
const BRUNO_STATE_TINT: Record<string, number> = {
  withdrawn: 0x6f94c4,
  noticed: 0x769bcb,
  named: 0x7fa8d9,
  accepted: 0x8ab3e0,
  trying: 0x95bde6,
  wobble: 0x8ab3e0,
  connected: 0xa3cbef,
}


/**
 * Drives the mission from story JSON. Content (lines, choices, branching)
 * lives ONLY in the JSON — swapping in the full 8-scene file must require
 * zero code changes here.
 */
export class StoryEngine {
  private mission: StoryMission
  private active = false
  /** Bumped on soft-branch jumps so stale scene continuations cancel. */
  private generation = 0
  /** Called when a choice is picked; SafetyLayer listens for redirects. */
  onChoice: ((choiceId: string, redirect: boolean) => void) | null = null

  constructor(
    private readonly game: Game,
    private readonly followCamera: FollowCamera,
    private readonly cinematicCamera: CinematicCamera,
    private readonly choicePanel: ChoicePanel,
    private readonly bubble: SophieBubble,
    private readonly actors: StoryActors,
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
    // Invalidate any continuation still pending from a previous run
    // (e.g. the final line's bubble timer when Bruno is tapped again).
    this.generation++
    this.bubble.hideNow()
    console.log(`[Story] mission "${this.mission.mission}" started`)
    this.runScene(this.mission.scenes[0].id)
  }

  /** SafetyLayer jumps here after repeated avoidant choices. */
  jumpTo(sceneId: string): void {
    if (!this.active) return
    console.log(`[Story] soft branch -> ${sceneId}`)
    this.generation++
    this.choicePanel.hide()
    this.bubble.hideNow()
    this.runScene(sceneId)
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
    if (scene.type === 'choice') this.runChoice(scene)
    else this.runCinematic(scene)
  }

  private runChoice(scene: ChoiceScene): void {
    this.game.states.transition('CHOICE')
    // Hand the camera back to the follow rig; its damped lerp eases the
    // view over from wherever the last shot left it — no cuts.
    this.cinematicCamera.stop()
    this.followCamera.setEnabled(true)
    this.applyChoiceCamera(scene.camera)
    this.choicePanel.show(
      {
        promptIcon: iconFor(scene.prompt?.icon),
        choices: scene.choices.slice(0, 3).map((c) => ({
          id: c.id,
          icon: iconFor(c.icon),
          label: c.label ?? labelFromId(c.id),
        })),
      },
      (choiceId) => {
        const choice = scene.choices.find((c) => c.id === choiceId)
        if (!choice) return
        console.log(`[Story] choice: ${choice.id}${choice.redirect ? ' (redirect)' : ''}`)
        const gen = this.generation
        this.onChoice?.(choice.id, choice.redirect === true)
        // A safety jump inside onChoice bumps the generation — this
        // continuation is then stale and must not run the old branch.
        if (gen !== this.generation) return
        const proceed = () => {
          if (gen === this.generation) this.runScene(choice.next)
        }
        if (choice.sophie_line) this.bubble.say(choice.sophie_line).then(proceed)
        else proceed()
      },
    )
  }

  private runCinematic(scene: CinematicScene): void {
    this.game.states.transition('CINEMATIC')
    if (scene.bruno_state) this.applyBrunoState(scene.bruno_state)
    const gen = this.generation

    // Controls are already locked (state gate); take the camera and tween
    // slowly into the staged shot, then play the actions.
    this.followCamera.setEnabled(false)
    this.cinematicCamera.play(this.parsePreset(scene.camera)).then(() => {
      if (gen !== this.generation) return
      this.playActions(scene, () => this.runScene(scene.next))
    })
  }

  /** Anim stubs are logged; lines go through Sophie's bubble. */
  private playActions(scene: CinematicScene, done: () => void): void {
    const actions = [...scene.actions]
    const gen = this.generation
    const step = () => {
      if (gen !== this.generation) return
      const action = actions.shift()
      if (!action) return done()
      if (action.line) {
        console.log(`[Cinematic] ${action.actor}: "${action.line}"`)
        this.bubble.say(action.line).then(step)
      } else {
        console.log(`[Cinematic] ${action.actor} plays anim "${action.anim}"`)
        window.setTimeout(step, 900)
      }
    }
    step()
  }

  /**
   * Story JSON camera strings → cinematic presets:
   * "wide", "closeup_<actor>", "over_shoulder_<actor>" (default actor: bruno).
   */
  private parsePreset(raw: string | undefined): CinematicPreset {
    const fallback = this.actors.resolve('bruno') ?? this.game.sophie
    if (raw?.startsWith('closeup_')) {
      return { kind: 'closeup', actor: this.actors.resolve(raw.slice(8)) ?? fallback }
    }
    if (raw?.startsWith('over_shoulder')) {
      const actorId = raw.replace(/^over_shoulder_?/, '')
      return {
        kind: 'over_shoulder',
        actor: (actorId && this.actors.resolve(actorId)) || fallback,
        companion: this.game.sophie,
      }
    }
    return { kind: 'wide', actor: fallback }
  }

  /** CHOICE scenes use the softer follow-camera focus ease-in. */
  private applyChoiceCamera(preset: string | undefined): void {
    if (preset?.startsWith('closeup_')) {
      this.followCamera.focusOn(this.actors.resolve(preset.slice(8)))
    } else {
      this.followCamera.focusOn(null)
    }
  }

  private applyBrunoState(state: string): void {
    console.log(`[Story] bruno_state -> ${state}`)
    const bruno = this.actors.resolve('bruno')
    if (!bruno) return
    const tint = BRUNO_STATE_TINT[state]
    if (tint === undefined) return
    bruno.traverse((child) => {
      const mesh = child as THREE.Mesh
      if (mesh.isMesh && (mesh.name === 'bruno-body' || mesh.name === 'bruno-head')) {
        ;(mesh.material as THREE.MeshStandardMaterial).color.setHex(tint)
      }
    })
  }

  private finish(): void {
    this.active = false
    this.choicePanel.hide()
    this.cinematicCamera.stop()
    this.followCamera.focusOn(null)
    this.followCamera.setEnabled(true) // eases home from the last shot
    this.game.states.transition('EXPLORE')
    console.log('[Story] segment complete — back to exploration')
  }
}
