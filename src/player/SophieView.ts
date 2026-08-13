import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'

const CROSSFADE_SEC = 0.3
const TARGET_HEIGHT = 0.95 // small dog next to Bruno (~2.4 world units)

/**
 * Sophie's GLB model + animation clips. The logical anchor group (owned by
 * Game, moved by SophieController) stays untouched — the model is parented
 * into it, so movement/camera code needs no changes.
 *
 * Clip changes always crossfade (never snap). A missing clip logs a
 * warning and keeps the current motion — no crash, no visual pop.
 */
export class SophieView {
  private mixer: THREE.AnimationMixer | null = null
  private readonly actions = new Map<string, THREE.AnimationAction>()
  private current: THREE.AnimationAction | null = null
  private currentName = ''

  constructor(private readonly anchor: THREE.Group) {}

  get isLoaded(): boolean {
    return this.mixer !== null
  }

  get currentClip(): string {
    return this.currentName
  }

  get clipNames(): string[] {
    return [...this.actions.keys()]
  }

  /** Load the GLB; on failure the capsule placeholder simply stays. */
  async load(url: string): Promise<boolean> {
    let gltf
    try {
      gltf = await new GLTFLoader().loadAsync(url)
    } catch (err) {
      console.warn(`[SophieView] could not load ${url} — keeping placeholder`, err)
      return false
    }

    const model = gltf.scene
    model.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) child.castShadow = true
    })

    // Normalize: feet on the ground, height ~TARGET_HEIGHT world units.
    const bounds = new THREE.Box3().setFromObject(model)
    const size = bounds.getSize(new THREE.Vector3())
    const scale = size.y > 0 ? TARGET_HEIGHT / size.y : 1
    model.scale.setScalar(scale)
    model.position.y = -bounds.min.y * scale
    model.name = 'sophie-model'

    // Swap out the grey capsule placeholder.
    for (const name of ['sophie-body', 'sophie-head']) {
      const placeholder = this.anchor.getObjectByName(name)
      placeholder?.removeFromParent()
    }
    this.anchor.add(model)

    this.mixer = new THREE.AnimationMixer(model)
    for (const clip of gltf.animations) {
      this.actions.set(clip.name, this.mixer.clipAction(clip))
    }
    console.log(`[SophieView] loaded ${url} (clips: ${this.clipNames.join(', ')})`)
    this.play('Idle')
    return true
  }

  /** Crossfade to a clip by name. Returns false if the clip is unknown. */
  play(name: string): boolean {
    if (!this.mixer) return false // placeholder mode — tint stub handles it
    if (this.currentName === name) return true

    const next = this.actions.get(name)
    if (!next) {
      console.warn(`[SophieView] missing clip "${name}" — keeping "${this.currentName || 'Idle'}"`)
      if (!this.current) this.play('Idle')
      return false
    }

    next.enabled = true
    next.reset().play()
    if (this.current && this.current !== next) {
      this.current.crossFadeTo(next, CROSSFADE_SEC, false)
    } else {
      next.fadeIn(CROSSFADE_SEC)
    }
    this.current = next
    this.currentName = name
    return true
  }

  update(dt: number): void {
    this.mixer?.update(dt)
  }
}
