import * as THREE from 'three'
import type { Game } from '../core/Game'
import { collectMaterials, type Interactable } from './Interactable'

const PULSE_PERIOD = 2.4 // seconds per full glow cycle — slow and soft
const PULSE_MAX = 0.35 // peak emissive intensity, gentle (never a blink)

/**
 * Tracks which interactable Sophie is near, drives the soft glow pulse,
 * and activates an interactable when it is tapped while in range.
 */
export class InteractionSystem {
  private readonly interactables: Interactable[] = []
  private readonly materialCache = new Map<Interactable, THREE.MeshStandardMaterial[]>()
  private focused: Interactable | null = null
  /** Forced highlight target for Sophie's hints (Task 4). */
  private hinted: Interactable | null = null

  constructor(private readonly game: Game) {}

  add(interactable: Interactable): void {
    this.interactables.push(interactable)
    const materials = collectMaterials(interactable.object)
    for (const m of materials) {
      m.emissive = new THREE.Color(0xfff2b8)
      m.emissiveIntensity = 0
    }
    this.materialCache.set(interactable, materials)
  }

  get focusedInteractable(): Interactable | null {
    return this.focused
  }

  list(): readonly Interactable[] {
    return this.interactables
  }

  /** SafetyLayer (Task 4) can softly highlight one object as a hint. */
  setHint(interactable: Interactable | null): void {
    if (this.hinted && this.hinted !== interactable) this.setGlow(this.hinted, 0)
    this.hinted = interactable
  }

  /**
   * Called by SophieController before the ground raycast. Returns true if
   * the tap hit an in-range interactable (consuming the tap).
   */
  tryActivate(raycaster: THREE.Raycaster): boolean {
    if (!this.game.states.is('EXPLORE')) return false
    for (const item of this.interactables) {
      if (!this.inRange(item)) continue
      if (raycaster.intersectObject(item.object, true).length > 0) {
        this.setGlow(item, 0)
        item.onActivate()
        return true
      }
    }
    return false
  }

  update(_dt: number, elapsed: number): void {
    if (!this.game.states.is('EXPLORE')) {
      if (this.focused) {
        this.setGlow(this.focused, 0)
        this.focused = null
      }
      return
    }

    // Nearest in-range interactable becomes the focused one.
    let nearest: Interactable | null = null
    let nearestDist = Infinity
    for (const item of this.interactables) {
      const d = this.distanceTo(item)
      if (d <= item.triggerRadius && d < nearestDist) {
        nearest = item
        nearestDist = d
      }
    }

    if (this.focused && this.focused !== nearest) this.setGlow(this.focused, 0)
    this.focused = nearest

    // Soft sine pulse — eased, slow, never a hard blink.
    const wave = (Math.sin((elapsed / PULSE_PERIOD) * Math.PI * 2) + 1) / 2
    const intensity = PULSE_MAX * (0.35 + 0.65 * wave)
    if (this.focused) this.setGlow(this.focused, intensity)
    if (this.hinted && this.hinted !== this.focused) this.setGlow(this.hinted, intensity)
  }

  private distanceTo(item: Interactable): number {
    const pos = new THREE.Vector3()
    item.object.getWorldPosition(pos)
    pos.y = 0
    const sophie = this.game.sophie.position.clone()
    sophie.y = 0
    return pos.distanceTo(sophie)
  }

  private inRange(item: Interactable): boolean {
    return this.distanceTo(item) <= item.triggerRadius
  }

  private setGlow(item: Interactable, intensity: number): void {
    const materials = this.materialCache.get(item)
    if (!materials) return
    for (const m of materials) m.emissiveIntensity = intensity
  }
}
