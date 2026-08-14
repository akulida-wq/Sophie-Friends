import * as THREE from 'three'
import { audio } from '../audio/AudioSystem'

/**
 * Soft pulsing tap cue (💛) floated over a 3D target — used by
 * `advance: tap_cue` scenes. No timer: the story waits calmly until the
 * child taps. The pulse is a gentle scale breathe, never a blink.
 */
export class TapCue {
  private readonly button: HTMLButtonElement
  private target: THREE.Object3D | null = null
  private readonly worldPos = new THREE.Vector3()

  constructor(
    container: HTMLElement,
    private readonly camera: THREE.PerspectiveCamera,
  ) {
    this.button = document.createElement('button')
    this.button.className = 'tap-cue'
    this.button.type = 'button'
    this.button.textContent = '💛'
    this.button.setAttribute('aria-label', 'Continue')
    container.appendChild(this.button)
  }

  show(target: THREE.Object3D, onTap: () => void): void {
    this.target = target
    this.button.onclick = () => {
      audio.ui('cue')
      this.hide()
      onTap()
    }
    this.button.classList.add('tap-cue--open')
    this.update()
  }

  hide(): void {
    this.target = null
    this.button.onclick = null
    this.button.classList.remove('tap-cue--open')
  }

  /** Keep the cue floating over the target (called every frame). */
  update(): void {
    if (!this.target) return
    this.target.getWorldPosition(this.worldPos)
    this.worldPos.y += 2.7 // above Bruno's head
    const projected = this.worldPos.clone().project(this.camera)
    const x = ((projected.x + 1) / 2) * window.innerWidth
    const y = ((1 - projected.y) / 2) * window.innerHeight
    this.button.style.left = `${x}px`
    this.button.style.top = `${y}px`
  }
}
