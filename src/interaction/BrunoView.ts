import * as THREE from 'three'

/**
 * Grey-phase visual stub for Bruno's emotional state: cool gray-blue tint
 * warming to a brighter blue, head rising, body straightening as he opens
 * up. Everything eases smoothly — real animation clips come with the GLB.
 */

interface Pose {
  tint: number
  headY: number
  bodyTiltX: number
}

const STATE_POSE: Record<string, Pose> = {
  withdrawn: { tint: 0x6b7f99, headY: 1.9, bodyTiltX: 0.16 },
  noticed: { tint: 0x6f8aab, headY: 1.97, bodyTiltX: 0.12 },
  named: { tint: 0x7495bc, headY: 2.03, bodyTiltX: 0.08 },
  accepted: { tint: 0x7fa3cc, headY: 2.08, bodyTiltX: 0.05 },
  trying: { tint: 0x88afdb, headY: 2.12, bodyTiltX: 0.03 },
  wobble: { tint: 0x82a8d4, headY: 2.08, bodyTiltX: 0.06 },
  connected: { tint: 0x93bfe8, headY: 2.18, bodyTiltX: -0.02 },
}

const EASE = 2.0 // damp factor — state shifts are slow and gentle

export class BrunoView {
  private readonly body: THREE.Mesh | null
  private readonly head: THREE.Mesh | null
  private readonly current: Pose
  private target: Pose
  private readonly tintCurrent = new THREE.Color()
  private readonly tintTarget = new THREE.Color()
  private state = 'withdrawn'

  constructor(bruno: THREE.Object3D) {
    this.body = bruno.getObjectByName('bruno-body') as THREE.Mesh | null
    this.head = bruno.getObjectByName('bruno-head') as THREE.Mesh | null
    this.target = STATE_POSE.withdrawn
    this.current = { ...this.target }
    this.tintCurrent.setHex(this.target.tint)
    this.tintTarget.setHex(this.target.tint)
    this.applyPose()
  }

  get currentState(): string {
    return this.state
  }

  setState(state: string): void {
    const pose = STATE_POSE[state]
    if (!pose) {
      console.warn(`[BrunoView] unknown bruno_state "${state}" — keeping "${this.state}"`)
      return
    }
    this.state = state
    this.target = pose
    this.tintTarget.setHex(pose.tint)
    console.log(`[BrunoView] state -> ${state}`)
  }

  update(dt: number): void {
    const t = 1 - Math.exp(-EASE * dt)
    this.current.headY += (this.target.headY - this.current.headY) * t
    this.current.bodyTiltX += (this.target.bodyTiltX - this.current.bodyTiltX) * t
    this.tintCurrent.lerp(this.tintTarget, t)
    this.applyPose()
  }

  private applyPose(): void {
    if (this.head) this.head.position.y = this.current.headY
    if (this.body) this.body.rotation.x = this.current.bodyTiltX
    for (const mesh of [this.body, this.head]) {
      if (!mesh) continue
      ;(mesh.material as THREE.MeshStandardMaterial).color.copy(this.tintCurrent)
    }
  }
}
