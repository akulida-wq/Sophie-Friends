import * as THREE from 'three'

const OFFSET = new THREE.Vector3(0, 8, 10) // above and slightly behind (Sims-like)
const LOOK_AHEAD = new THREE.Vector3(0, 0.6, 0)
const POSITION_DAMP = 3.0 // higher = tighter follow
const LOOK_DAMP = 4.0

/**
 * Third-person follow camera with soft lag: world-fixed offset (the view
 * direction never spins with the dog — Sims-style), position and look
 * target eased with exponential smoothing so there is no jitter.
 */
export class FollowCamera {
  private readonly lookTarget = new THREE.Vector3()
  private enabled = true

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

  snap(): void {
    this.camera.position.copy(this.subject.position).add(OFFSET)
    this.camera.lookAt(this.lookTarget)
  }

  update(dt: number): void {
    if (!this.enabled) return
    const desired = new THREE.Vector3().copy(this.subject.position).add(OFFSET)
    const posT = 1 - Math.exp(-POSITION_DAMP * dt)
    this.camera.position.lerp(desired, posT)

    const desiredLook = new THREE.Vector3().copy(this.subject.position).add(LOOK_AHEAD)
    const lookT = 1 - Math.exp(-LOOK_DAMP * dt)
    this.lookTarget.lerp(desiredLook, lookT)
    this.camera.lookAt(this.lookTarget)
  }
}
