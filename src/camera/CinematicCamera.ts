import * as THREE from 'three'

export type CinematicPresetKind = 'wide' | 'closeup' | 'over_shoulder'

export interface CinematicPreset {
  kind: CinematicPresetKind
  /** Actor the shot frames (closeup / over_shoulder target). */
  actor: THREE.Object3D
  /** Second point of interest — Sophie for over-shoulder shots. */
  companion?: THREE.Object3D
}

const TWEEN_SECONDS = 2.2 // slow and soft — never a cut

function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
}

/**
 * Owns the camera during CINEMATIC scenes: slow eased tweens into staged
 * shots (GTA-style realtime scenes, but calm). Returning control is done by
 * simply re-enabling the FollowCamera — its damped lerp continues from the
 * current pose, so there is never a jump, shake or flash.
 */
export class CinematicCamera {
  private tweenT = 1
  private readonly fromPos = new THREE.Vector3()
  private readonly fromLook = new THREE.Vector3()
  private readonly toPos = new THREE.Vector3()
  private readonly toLook = new THREE.Vector3()
  private readonly look = new THREE.Vector3()
  private active = false
  private onSettled: (() => void) | null = null

  constructor(private readonly camera: THREE.PerspectiveCamera) {}

  /** Tween to a preset; resolves when the shot has settled. */
  play(preset: CinematicPreset): Promise<void> {
    return new Promise((resolve) => {
      const { position, lookAt } = this.composeShot(preset)
      this.fromPos.copy(this.camera.position)
      this.fromLook.copy(this.currentLookPoint())
      this.toPos.copy(position)
      this.toLook.copy(lookAt)
      this.tweenT = 0
      this.active = true
      this.onSettled?.()
      this.onSettled = resolve
    })
  }

  /** Hand the camera back (FollowCamera eases it home from wherever it is). */
  stop(): void {
    this.active = false
    this.onSettled?.()
    this.onSettled = null
  }

  update(dt: number): void {
    if (!this.active) return
    if (this.tweenT < 1) {
      this.tweenT = Math.min(1, this.tweenT + dt / TWEEN_SECONDS)
      const k = easeInOutCubic(this.tweenT)
      this.camera.position.lerpVectors(this.fromPos, this.toPos, k)
      this.look.lerpVectors(this.fromLook, this.toLook, k)
      this.camera.lookAt(this.look)
      if (this.tweenT >= 1 && this.onSettled) {
        const settled = this.onSettled
        this.onSettled = null
        settled()
      }
    } else {
      // Hold the shot (actors may move a little — keep framing them).
      this.camera.position.copy(this.toPos)
      this.camera.lookAt(this.toLook)
    }
  }

  private composeShot(preset: CinematicPreset): { position: THREE.Vector3; lookAt: THREE.Vector3 } {
    const actorPos = new THREE.Vector3()
    preset.actor.getWorldPosition(actorPos)

    switch (preset.kind) {
      case 'closeup': {
        const lookAt = actorPos.clone().setY(actorPos.y + 1.5)
        const position = actorPos.clone().add(new THREE.Vector3(1.1, 1.9, 2.6))
        return { position, lookAt }
      }
      case 'over_shoulder': {
        const companionPos = new THREE.Vector3()
        ;(preset.companion ?? preset.actor).getWorldPosition(companionPos)
        // Behind the companion's shoulder, looking at the actor.
        const back = companionPos.clone().sub(actorPos).normalize()
        const position = companionPos
          .clone()
          .addScaledVector(back, 1.6)
          .add(new THREE.Vector3(0.7, 1.6, 0))
        const lookAt = actorPos.clone().setY(actorPos.y + 1.3)
        return { position, lookAt }
      }
      case 'wide':
      default: {
        const lookAt = actorPos.clone().setY(actorPos.y + 0.9)
        const position = actorPos.clone().add(new THREE.Vector3(5, 5.5, 7.5))
        return { position, lookAt }
      }
    }
  }

  /** Approximate current look point 6 units along the view direction. */
  private currentLookPoint(): THREE.Vector3 {
    const dir = new THREE.Vector3()
    this.camera.getWorldDirection(dir)
    return this.camera.position.clone().addScaledVector(dir, 6)
  }
}
