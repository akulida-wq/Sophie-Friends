import * as THREE from 'three'

/**
 * Рисунок мелом на плитке: плоский декаль с процедурной «меловой»
 * текстурой (солнышко с улыбкой). Появляется мягким фейдом — без вспышек.
 */
export class ChalkDrawing {
  private readonly mesh: THREE.Mesh
  private readonly material: THREE.MeshBasicMaterial
  private fade = 0
  private fading = false
  private _drawn = false

  constructor(scene: THREE.Scene, position: THREE.Vector3, size = 0.82) {
    this.material = new THREE.MeshBasicMaterial({
      map: ChalkDrawing.makeSunTexture(),
      transparent: true,
      opacity: 0,
      depthWrite: false,
      polygonOffset: true,
      polygonOffsetFactor: -2,
      polygonOffsetUnits: -2,
    })
    const geo = new THREE.PlaneGeometry(size, size)
    geo.rotateX(-Math.PI / 2)
    this.mesh = new THREE.Mesh(geo, this.material)
    this.mesh.position.copy(position)
    this.mesh.rotation.y = 0.35
    this.mesh.renderOrder = 2
    this.mesh.visible = false
    this.mesh.name = 'chalk-drawing'
    scene.add(this.mesh)
  }

  /** Рисунок уже на плитке (без таймера — на всю сессию). */
  get drawn(): boolean {
    return this._drawn
  }

  /** Мягко проявить солнышко (~1.6с). */
  reveal(): void {
    this._drawn = true
    this.mesh.visible = true
    this.fading = true
  }

  update(dt: number): void {
    if (!this.fading) return
    this.fade = Math.min(1, this.fade + dt / 1.6)
    this.material.opacity = this.fade * this.fade * (3 - 2 * this.fade)
    if (this.fade >= 1) this.fading = false
  }

  /** Меловое солнышко: зернистые штрихи, улыбка, тёплая палитра. */
  private static makeSunTexture(): THREE.CanvasTexture {
    const S = 256
    const canvas = document.createElement('canvas')
    canvas.width = S
    canvas.height = S
    const ctx = canvas.getContext('2d')!
    ctx.clearRect(0, 0, S, S)
    const cx = S / 2
    const cy = S / 2
    const chalk = (color: string, alpha: number) => {
      ctx.strokeStyle = color
      ctx.fillStyle = color
      ctx.globalAlpha = alpha
      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'
    }
    // диск — несколько неровных слоёв, как мел по шершавой плитке
    for (let i = 0; i < 4; i++) {
      chalk('#ffd65c', 0.32)
      ctx.beginPath()
      ctx.arc(cx + (i - 1.5) * 1.6, cy + (i % 2) * 1.4, 50 - i * 1.2, 0, Math.PI * 2)
      ctx.fill()
    }
    chalk('#ffb83a', 0.8)
    ctx.lineWidth = 7
    ctx.beginPath()
    ctx.arc(cx, cy, 50, 0, Math.PI * 2)
    ctx.stroke()
    // лучи — чуть дрожащие, разной длины
    for (let k = 0; k < 10; k++) {
      const a = (k / 10) * Math.PI * 2 + 0.2
      const r0 = 62
      const r1 = 92 + (k % 3) * 8
      chalk('#ffc447', 0.85)
      ctx.lineWidth = 8
      ctx.beginPath()
      ctx.moveTo(cx + Math.cos(a) * r0, cy + Math.sin(a) * r0)
      ctx.lineTo(cx + Math.cos(a + 0.03) * r1, cy + Math.sin(a + 0.03) * r1)
      ctx.stroke()
    }
    // глазки и улыбка
    chalk('#8a5a3c', 0.9)
    ctx.lineWidth = 6
    ctx.beginPath()
    ctx.arc(cx - 17, cy - 10, 4.5, 0, Math.PI * 2)
    ctx.fill()
    ctx.beginPath()
    ctx.arc(cx + 17, cy - 10, 4.5, 0, Math.PI * 2)
    ctx.fill()
    ctx.beginPath()
    ctx.arc(cx, cy + 4, 22, 0.25 * Math.PI, 0.75 * Math.PI)
    ctx.stroke()
    // меловая зернистость: редкие светлые точки и «проплешины»
    ctx.globalCompositeOperation = 'destination-out'
    let seed = 4242
    const rand = () => {
      seed = (seed * 16807) % 2147483647
      return seed / 2147483647
    }
    for (let i = 0; i < 900; i++) {
      ctx.globalAlpha = 0.35 + rand() * 0.4
      ctx.beginPath()
      ctx.arc(rand() * S, rand() * S, 0.6 + rand() * 1.4, 0, Math.PI * 2)
      ctx.fill()
    }
    ctx.globalCompositeOperation = 'source-over'
    const tex = new THREE.CanvasTexture(canvas)
    tex.colorSpace = THREE.SRGBColorSpace
    tex.anisotropy = 4
    return tex
  }
}
