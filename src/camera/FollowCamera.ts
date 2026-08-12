import * as THREE from 'three'

const OFFSET = new THREE.Vector3(0, 8, 10) // above and slightly behind (Sims-like)
const LOOK_AHEAD = new THREE.Vector3(0, 0.6, 0)
const POSITION_DAMP = 3.0 // higher = tighter follow
const LOOK_DAMP = 4.0
const FOCUS_OFFSET = new THREE.Vector3(0, 3.2, 4.6) // closer view for CHOICE
const FOCUS_LOOK = new THREE.Vector3(0, 1.2, 0)
const FOCUS_DAMP = 1.8 // slower ease-in, gentle

/**
 * Third-person follow camera with soft lag: world-fixed offset (the view
 * direction never spins with the dog — Sims-style), position and look
 * target eased with exponential smoothing so there is no jitter.
 */
export class FollowCamera {
  private readonly lookTarget = new THREE.Vector3()
  private enabled = true
  private focusSubject: THREE.Object3D | null = null

  constructor(
    private readonly camera: THREE.PerspectiveCamera,
    private readonly subject: THREE.Object3D,
  ) {
    this.lookTarget.copy(subject.position).add(LOOK_AHEAD)
    this.snap()
  }

  /** Cinematic system (Task 5) disables follow while it owns the camera. */
  setEnabled(on: boolean): void {
    this.enabled = on
    if (on) this.lookTarget.copy(this.subject.position).add(LOOK_AHEAD)
  }

  /** CHOICE state: ease the camera in on a target (e.g. Bruno). */
  focusOn(subject: THREE.Object3D | null): void {
    this.focusSubject = subject
  }

  snap(): void {
    this.camera.position.copy(this.subject.position).add(OFFSET)
    this.camera.lookAt(this.lookTarget)
  }

  update(dt: number): void {
    if (!this.enabled) return

    let desired: THREE.Vector3
    let desiredLook: THREE.Vector3
    let damp = POSITION_DAMP
    if (this.focusSubject) {
      const focusPos = new THREE.Vector3()
      this.focusSubject.getWorldPosition(focusPos)
      desired = focusPos.clone().add(FOCUS_OFFSET)
      desiredLook = focusPos.clone().add(FOCUS_LOOK)
      damp = FOCUS_DAMP
    } else {
      desired = new THREE.Vector3().copy(this.subject.position).add(OFFSET)
      desiredLook = new THREE.Vector3().copy(this.subject.position).add(LOOK_AHEAD)
    }

    const posT = 1 - Math.exp(-damp * dt)
    this.camera.position.lerp(desired, posT)

    const lookT = 1 - Math.exp(-LOOK_DAMP * dt)
    this.lookTarget.lerp(desiredLook, lookT)
    this.camera.lookAt(this.lookTarget)
  }
}
