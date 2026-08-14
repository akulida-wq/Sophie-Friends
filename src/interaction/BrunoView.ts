import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'

const TARGET_HEIGHT = 2.35 // рядом с Софи (~0.95) и площадкой
const FADE = 0.5

/**
 * Доля "открытости" позы для каждого шага арки Бруно: 0 = IdleSad,
 * 1 = IdleOpen. Блендинг клипов делает арку видимой без слов.
 */
const STATE_OPEN: Record<string, number> = {
  withdrawn: 0.0,
  noticed: 0.12,
  named: 0.3,
  accepted: 0.55,
  trying: 0.75,
  wobble: 0.45,
  connected: 1.0,
}

/** Клипы-циклы; остальные проигрываются один раз и отпускаются. */
const LOOPING = new Set(['IdleSad', 'IdleOpen', 'Walk', 'PlayIncluded'])

/** Grey-fallback: тинт/поза плейсхолдера, если GLB не загрузился. */
const FALLBACK_TINT: Record<string, number> = {
  withdrawn: 0x6b7f99, noticed: 0x6f8aab, named: 0x7495bc,
  accepted: 0x7fa3cc, trying: 0x88afdb, wobble: 0x82a8d4,
  connected: 0x93bfe8,
}

export class BrunoView {
  private mixer: THREE.AnimationMixer | null = null
  private readonly actions = new Map<string, THREE.AnimationAction>()
  private idleSad: THREE.AnimationAction | null = null
  private idleOpen: THREE.AnimationAction | null = null
  private overlay: THREE.AnimationAction | null = null
  private openTarget = 0
  private open = 0
  private state = 'withdrawn'

  constructor(private readonly anchor: THREE.Object3D) {}

  get isLoaded(): boolean {
    return this.mixer !== null
  }

  get currentState(): string {
    return this.state
  }

  /** Заменяет плейсхолдер моделью; при неудаче остаётся серый стаб. */
  async load(url: string): Promise<boolean> {
    let gltf
    try {
      gltf = await new GLTFLoader().loadAsync(url)
    } catch (err) {
      console.warn(`[BrunoView] could not load ${url} — keeping placeholder`, err)
      return false
    }
    const model = gltf.scene
    model.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) child.castShadow = true
    })
    const bounds = new THREE.Box3().setFromObject(model)
    const size = bounds.getSize(new THREE.Vector3())
    const scale = size.y > 0 ? TARGET_HEIGHT / size.y : 1
    model.scale.setScalar(scale)
    model.position.y = -bounds.min.y * scale
    // Морда в -Z glTF (экспорт из +Y Blender) -> разворот к нашему +Z.
    model.rotation.y = Math.PI
    model.name = 'bruno-model'

    for (const child of [...this.anchor.children]) child.removeFromParent()
    this.anchor.add(model)

    this.mixer = new THREE.AnimationMixer(model)
    for (const clip of gltf.animations) {
      this.actions.set(clip.name, this.mixer.clipAction(clip))
    }
    this.idleSad = this.actions.get('IdleSad') ?? null
    this.idleOpen = this.actions.get('IdleOpen') ?? null
    this.idleSad?.play()
    this.idleOpen?.play()
    if (this.idleSad) this.idleSad.weight = 1
    if (this.idleOpen) this.idleOpen.weight = 0

    this.mixer.addEventListener('finished', (e) => {
      if (e.action === this.overlay) this.clearOverlay()
    })
    this.setState(this.state)
    console.log(`[BrunoView] loaded ${url} (clips: ${[...this.actions.keys()].join(', ')})`)
    return true
  }

  /** bruno_state из story JSON → блендинг IdleSad/IdleOpen (арка видима). */
  setState(state: string): void {
    this.state = state
    console.log(`[BrunoView] state -> ${state}`)
    if (!this.mixer) {
      this.applyFallbackTint(state)
      return
    }
    this.openTarget = STATE_OPEN[state] ?? this.openTarget
    this.clearOverlay()
  }

  /** Story `anim` для Бруно: клип по имени поверх idle-блендинга. */
  play(name: string): boolean {
    if (!this.mixer) return false
    if (name === 'IdleSad') {
      this.openTarget = 0
      this.clearOverlay()
      return true
    }
    if (name === 'IdleOpen') {
      this.openTarget = 1
      this.clearOverlay()
      return true
    }
    const action = this.actions.get(name)
    if (!action) {
      console.warn(`[BrunoView] missing clip "${name}" — keeping idle blend`)
      return false
    }
    this.clearOverlay()
    this.overlay = action
    action.reset()
    if (!LOOPING.has(name)) {
      action.setLoop(THREE.LoopOnce, 1)
      action.clampWhenFinished = true
    } else {
      action.setLoop(THREE.LoopRepeat, Infinity)
    }
    action.fadeIn(FADE)
    action.play()
    return true
  }

  private clearOverlay(): void {
    if (this.overlay) {
      this.overlay.fadeOut(FADE)
      this.overlay = null
    }
  }

  update(dt: number): void {
    if (!this.mixer) return
    const t = 1 - Math.exp(-1.6 * dt)
    this.open += (this.openTarget - this.open) * t
    const idleShare = this.overlay ? Math.max(0, 1 - this.overlay.getEffectiveWeight()) : 1
    if (this.idleSad) this.idleSad.weight = (1 - this.open) * idleShare
    if (this.idleOpen) this.idleOpen.weight = this.open * idleShare
    this.mixer.update(dt)
  }

  private applyFallbackTint(state: string): void {
    const tint = FALLBACK_TINT[state]
    if (tint === undefined) return
    this.anchor.traverse((child) => {
      const mesh = child as THREE.Mesh
      if (mesh.isMesh && (mesh.name === 'bruno-body' || mesh.name === 'bruno-head')) {
        ;(mesh.material as THREE.MeshStandardMaterial).color.setHex(tint)
      }
    })
  }
}
