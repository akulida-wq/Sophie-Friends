import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'

/**
 * Друг-монстрик у песочницы: Idle-цикл, изредка Look/Chat, по расписанию
 * из main — «трюк» (танец/бокс). Всё через мягкие кроссфейды.
 */
export class FriendView {
  private mixer: THREE.AnimationMixer | null = null
  private readonly actions = new Map<string, THREE.AnimationAction>()
  private idle: THREE.AnimationAction | null = null
  private overlay: THREE.AnimationAction | null = null

  constructor(
    private readonly anchor: THREE.Object3D,
    private readonly targetHeight: number,
  ) {}

  get isLoaded(): boolean {
    return this.mixer !== null
  }

  hasClip(name: string): boolean {
    return this.actions.has(name)
  }

  async load(url: string, yaw = 0): Promise<boolean> {
    let gltf
    try {
      gltf = await new GLTFLoader().loadAsync(url)
    } catch (err) {
      console.warn(`[FriendView] could not load ${url}`, err)
      return false
    }
    const model = gltf.scene
    model.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) child.castShadow = true
    })
    const bounds = new THREE.Box3().setFromObject(model)
    const size = bounds.getSize(new THREE.Vector3())
    const scale = size.y > 0 ? this.targetHeight / size.y : 1
    model.scale.setScalar(scale)
    model.position.y = -bounds.min.y * scale
    model.rotation.y = yaw
    for (const child of [...this.anchor.children]) child.removeFromParent()
    this.anchor.add(model)

    this.mixer = new THREE.AnimationMixer(model)
    for (const clip of gltf.animations) {
      this.actions.set(clip.name, this.mixer.clipAction(clip))
    }
    this.idle = this.actions.get('Idle') ?? null
    this.idle?.play()
    this.mixer.addEventListener('finished', (e) => {
      if (e.action === this.overlay) this.clearOverlay()
    })
    return true
  }

  /** Разовый клип (Look/Chat/Trick) поверх Idle; сам вернётся в Idle. */
  playOnce(name: string): void {
    if (!this.mixer) return
    const action = this.actions.get(name)
    if (!action || action === this.overlay) return
    this.clearOverlay()
    this.overlay = action
    action.reset()
    action.setLoop(THREE.LoopOnce, 1)
    action.clampWhenFinished = false
    action.fadeIn(0.5)
    action.play()
  }

  private clearOverlay(): void {
    if (this.overlay) {
      this.overlay.fadeOut(0.5)
      this.overlay = null
    }
  }

  update(dt: number): void {
    if (!this.mixer) return
    const share = this.overlay ? Math.max(0, 1 - this.overlay.getEffectiveWeight()) : 1
    if (this.idle) this.idle.weight = share
    this.mixer.update(dt)
  }
}
