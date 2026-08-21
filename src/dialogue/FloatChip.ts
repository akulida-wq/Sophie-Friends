import * as THREE from 'three'
import { renderIcon } from './icons'

/**
 * Плавающая плашка над 3D-объектом (маркер-сердечко, имя персонажа).
 * Мягкое покачивание и пульс (scale 1.0-1.08) — чистый CSS, без миганий.
 */
export class FloatChip {
  private readonly el: HTMLDivElement
  private target: THREE.Object3D | null = null
  private readonly worldPos = new THREE.Vector3()
  private heightOffset = 2.7
  private hideTimer: number | null = null
  /** Тап по плашке (например, маркер над Бруно = «поговорить»). */
  onTap: (() => void) | null = null

  constructor(
    container: HTMLElement,
    private readonly camera: THREE.PerspectiveCamera,
    variant: 'marker' | 'name',
  ) {
    this.el = document.createElement('div')
    this.el.className = `float-chip float-chip--${variant}`
    this.el.addEventListener('pointerdown', (e) => {
      if (this.onTap) {
        e.stopPropagation()
        this.onTap()
      }
    })
    container.appendChild(this.el)
  }

  show(target: THREE.Object3D, text: string, opts: { height?: number; autohideMs?: number } = {}): void {
    this.target = target
    renderIcon(this.el, text)
    this.heightOffset = opts.height ?? 2.7
    this.el.classList.add('float-chip--on')
    this.el.style.pointerEvents = this.onTap ? 'auto' : 'none'
    this.el.style.cursor = this.onTap ? 'pointer' : 'default'
    if (this.hideTimer !== null) window.clearTimeout(this.hideTimer)
    if (opts.autohideMs) {
      this.hideTimer = window.setTimeout(() => this.hide(), opts.autohideMs)
    }
    this.update()
  }

  hide(): void {
    this.target = null
    this.el.classList.remove('float-chip--on')
    if (this.hideTimer !== null) {
      window.clearTimeout(this.hideTimer)
      this.hideTimer = null
    }
  }

  get isVisible(): boolean {
    return this.target !== null
  }

  update(): void {
    if (!this.target) return
    this.target.getWorldPosition(this.worldPos)
    this.worldPos.y += this.heightOffset
    const p = this.worldPos.clone().project(this.camera)
    this.el.style.left = `${((p.x + 1) / 2) * window.innerWidth}px`
    this.el.style.top = `${((1 - p.y) / 2) * window.innerHeight}px`
  }
}
