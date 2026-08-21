import * as THREE from 'three'
import { resolveYardCollisions } from '../core/Environment'
import type { Game } from '../core/Game'

export type AnimState = 'Idle' | 'Walk' | 'Run'

const WALK_SPEED = 2.2
const RUN_SPEED = 4.6
const RUN_DISTANCE = 6 // farther than this → Sophie runs
const ARRIVE_RADIUS = 0.15
const TURN_SPEED = 8 // rad/s damping factor for smooth turning

// Animation stubs are visualised with a gentle body tint until GLB
// animations arrive (Idle soft white / Walk cream / Run warm gold).
const ANIM_TINT: Record<AnimState, number> = {
  Idle: 0xfffdf5,
  Walk: 0xfff0cd,
  Run: 0xffdfa3,
}

/**
 * Tap/click-to-move control for Sophie. Pointer events cover both touch
 * (tablet) and mouse (desktop demo). Input is only accepted in EXPLORE.
 */
export class SophieController {
  private readonly raycaster = new THREE.Raycaster()
  private readonly pointer = new THREE.Vector2()
  private target: THREE.Vector3 | null = null
  private anim: AnimState = 'Idle'
  /** Set by SafetyLayer (Task 4) to notice activity; also used for tests. */
  onInput: (() => void) | null = null
  /** Interaction system gets first look at taps; true = tap consumed. */
  tapInterceptor: ((raycaster: THREE.Raycaster) => boolean) | null = null
  /** Notified on Idle/Walk/Run changes (drives GLB clips once loaded). */
  onAnimChange: ((state: AnimState) => void) | null = null
  /** Точка тапа по земле (риппл-индикатор). */
  onMoveTarget: ((point: THREE.Vector3) => void) | null = null
  /** Тап по интерактиву издалека: вернуть точку и радиус подхода. */
  findFarTap:
    | ((rc: THREE.Raycaster) => { id: string; point: THREE.Vector3; radius: number } | null)
    | null = null
  /** Пришли к объекту из очереди — пора активировать. */
  onArrivedAtInteract: ((id: string) => void) | null = null
  private pendingInteract: string | null = null
  private stuckTime = 0

  constructor(private readonly game: Game) {
    game.renderer.domElement.addEventListener('pointerdown', (e) => {
      this.handlePointer(e)
    })
  }

  get animState(): AnimState {
    return this.anim
  }

  get isMoving(): boolean {
    return this.target !== null
  }

  /** Stop any current movement (used when leaving EXPLORE). */
  halt(): void {
    this.target = null
    this.setAnim('Idle')
  }

  private handlePointer(e: PointerEvent): void {
    if (!this.game.states.is('EXPLORE')) return
    this.onInput?.()

    const rect = this.game.renderer.domElement.getBoundingClientRect()
    this.pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
    this.pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1
    this.raycaster.setFromCamera(this.pointer, this.game.camera)

    if (this.tapInterceptor?.(this.raycaster)) return

    const ground = this.game.scene.getObjectByName('ground')
    if (!ground) return
    const hit = this.raycaster.intersectObject(ground, false)[0]
    if (!hit) return

    // тап по интерактиву издалека: идём к нему и активируем по прибытии
    const far = this.findFarTap?.(this.raycaster)
    if (far) {
      const dir = this.game.sophie.position.clone().sub(far.point)
      dir.y = 0
      if (dir.lengthSq() < 1e-6) dir.set(0, 0, 1)
      dir.normalize()
      this.target = far.point.clone().addScaledVector(dir, Math.min(1.6, far.radius * 0.55))
      this.target.y = 0
      resolveYardCollisions(this.target)
      this.pendingInteract = far.id
      this.onMoveTarget?.(this.target)
      return
    }

    this.pendingInteract = null
    this.target = hit.point.clone()
    this.target.y = 0
    resolveYardCollisions(this.target) // цель не внутри препятствия
    this.onMoveTarget?.(this.target)
  }

  update(dt: number): void {
    if (!this.game.states.is('EXPLORE')) {
      if (this.target) this.halt()
      return
    }
    if (!this.target) return

    const pos = this.game.sophie.position
    const toTarget = new THREE.Vector3().subVectors(this.target, pos)
    toTarget.y = 0
    const distance = toTarget.length()

    if (distance <= ARRIVE_RADIUS) {
      this.target = null
      this.setAnim('Idle')
      this.consumePendingInteract()
      return
    }

    const running = distance > RUN_DISTANCE
    this.setAnim(running ? 'Run' : 'Walk')
    const speed = running ? RUN_SPEED : WALK_SPEED
    const before = pos.clone()

    // Smooth turning: ease the yaw toward the direction of travel.
    const desiredYaw = Math.atan2(toTarget.x, toTarget.z)
    const currentYaw = this.game.sophie.rotation.y
    let delta = desiredYaw - currentYaw
    while (delta > Math.PI) delta -= Math.PI * 2
    while (delta < -Math.PI) delta += Math.PI * 2
    this.game.sophie.rotation.y = currentYaw + delta * Math.min(1, TURN_SPEED * dt)

    const step = Math.min(distance, speed * dt)
    pos.addScaledVector(toTarget.normalize(), step)
    resolveYardCollisions(pos)
    // упёрлись в препятствие — мягко останавливаемся, а не топчемся
    if (pos.distanceTo(before) < step * 0.25) {
      this.stuckTime += dt
      if (this.stuckTime > 0.6) {
        this.target = null
        this.stuckTime = 0
        this.setAnim('Idle')
        // упёрлись рядом с целью-объектом — всё равно пробуем активировать
        this.consumePendingInteract()
      }
    } else {
      this.stuckTime = 0
    }
  }

  private consumePendingInteract(): void {
    if (this.pendingInteract) {
      const id = this.pendingInteract
      this.pendingInteract = null
      this.onArrivedAtInteract?.(id)
    }
  }

  private setAnim(next: AnimState): void {
    if (this.anim === next) return
    this.anim = next
    console.log(`[Anim] Sophie -> ${next}`)
    this.onAnimChange?.(next)
    // Grey-phase tint stub — harmless no-op once the GLB replaces the capsule.
    const body = this.game.sophie.getObjectByName('sophie-body') as THREE.Mesh | null
    if (body) {
      const mat = body.material as THREE.MeshStandardMaterial
      mat.color.setHex(ANIM_TINT[next])
    }
  }
}
