import * as THREE from 'three'
import { GameStateMachine } from './GameState'
import { createWorld } from './World'
import { createSophiePlaceholder } from '../player/SophiePlaceholder'

/**
 * Owns the renderer, scene, camera and the main loop.
 * Systems (player, camera, interaction, story, safety) are attached here
 * as tasks progress — no game logic lives in this class beyond wiring.
 */
export class Game {
  readonly scene = new THREE.Scene()
  readonly renderer: THREE.WebGLRenderer
  readonly camera: THREE.PerspectiveCamera
  readonly states = new GameStateMachine()
  readonly sophie: THREE.Group

  private readonly timer = new THREE.Timer()
  private updatables: Array<(dt: number, elapsed: number) => void> = []

  constructor(container: HTMLElement) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true })
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    this.renderer.setSize(window.innerWidth, window.innerHeight)
    this.renderer.shadowMap.enabled = true
    this.renderer.shadowMap.type = THREE.PCFShadowMap
    container.appendChild(this.renderer.domElement)

    this.camera = new THREE.PerspectiveCamera(
      45,
      window.innerWidth / window.innerHeight,
      0.1,
      200,
    )
    // Sims-like starting view: above and behind, looking down at the yard.
    this.camera.position.set(0, 9, 12)
    this.camera.lookAt(0, 0, 0)

    createWorld(this.scene)

    this.sophie = createSophiePlaceholder()
    this.scene.add(this.sophie)

    window.addEventListener('resize', () => this.onResize())
  }

  /** Register a per-frame update callback. */
  addUpdatable(fn: (dt: number, elapsed: number) => void): void {
    this.updatables.push(fn)
  }

  start(): void {
    this.renderer.setAnimationLoop(() => this.tick())
    console.log('[Game] started in state', this.states.state)
  }

  private tick(): void {
    this.timer.update()
    const dt = Math.min(this.timer.getDelta(), 0.05)
    const elapsed = this.timer.getElapsed()
    for (const update of this.updatables) update(dt, elapsed)
    this.renderer.render(this.scene, this.camera)
  }

  private onResize(): void {
    this.camera.aspect = window.innerWidth / window.innerHeight
    this.camera.updateProjectionMatrix()
    this.renderer.setSize(window.innerWidth, window.innerHeight)
  }
}
