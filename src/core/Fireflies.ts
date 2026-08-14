import * as THREE from 'three'

/**
 * Светлячки для тёплых сцен (Resolution): медленные, мягкие, аддитивные
 * точки, плавное появление/угасание. Никакого мерцания — только дрейф.
 */
const COUNT = 36
const AREA_R = 8
const CENTER = new THREE.Vector3(0, 0, -6)

export class Fireflies {
  private readonly points: THREE.Points
  private readonly material: THREE.PointsMaterial
  private readonly base: Float32Array
  private readonly phase: Float32Array
  private targetOpacity = 0

  constructor(scene: THREE.Scene) {
    const geo = new THREE.BufferGeometry()
    const positions = new Float32Array(COUNT * 3)
    this.base = new Float32Array(COUNT * 3)
    this.phase = new Float32Array(COUNT)
    for (let i = 0; i < COUNT; i++) {
      const a = (i / COUNT) * Math.PI * 2
      const r = AREA_R * (0.3 + 0.7 * ((i * 37) % 100) / 100)
      this.base[i * 3] = CENTER.x + Math.cos(a) * r
      this.base[i * 3 + 1] = 0.6 + (((i * 53) % 100) / 100) * 2.2
      this.base[i * 3 + 2] = CENTER.z + Math.sin(a) * r
      this.phase[i] = (i * 97) % 7
      positions.set(this.base.subarray(i * 3, i * 3 + 3), i * 3)
    }
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    // круглый мягкий спрайт вместо квадратных точек
    const canvas = document.createElement('canvas')
    canvas.width = canvas.height = 64
    const g2d = canvas.getContext('2d')
    if (g2d) {
      const grad = g2d.createRadialGradient(32, 32, 0, 32, 32, 32)
      grad.addColorStop(0, 'rgba(255,255,255,1)')
      grad.addColorStop(0.4, 'rgba(255,255,255,0.6)')
      grad.addColorStop(1, 'rgba(255,255,255,0)')
      g2d.fillStyle = grad
      g2d.fillRect(0, 0, 64, 64)
    }
    this.material = new THREE.PointsMaterial({
      size: 0.28,
      map: new THREE.CanvasTexture(canvas),
      color: 0xffe6a3,
      transparent: true,
      opacity: 0,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    })
    this.points = new THREE.Points(geo, this.material)
    this.points.frustumCulled = false
    this.points.visible = false
    this.points.name = 'fireflies'
    scene.add(this.points)
  }

  setActive(on: boolean): void {
    this.targetOpacity = on ? 0.75 : 0
  }

  update(dt: number, elapsed: number): void {
    const t = 1 - Math.exp(-0.8 * dt)
    this.material.opacity += (this.targetOpacity - this.material.opacity) * t
    const visible = this.material.opacity > 0.01
    this.points.visible = visible
    if (!visible) return
    const pos = this.points.geometry.attributes.position
    for (let i = 0; i < COUNT; i++) {
      const p = this.phase[i]
      pos.setX(i, this.base[i * 3] + Math.sin(elapsed * 0.22 + p) * 0.7)
      pos.setY(i, this.base[i * 3 + 1] + Math.sin(elapsed * 0.35 + p * 1.7) * 0.45)
      pos.setZ(i, this.base[i * 3 + 2] + Math.cos(elapsed * 0.18 + p) * 0.7)
    }
    pos.needsUpdate = true
  }
}
