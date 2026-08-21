import * as THREE from 'three'

/**
 * Живая вода фонтана: капли летят из верхней чаши параболой в бассейн,
 * на глади — медленные расходящиеся кольца. Всё мягкое и медленное,
 * без брызг и мерцания (safety-правила).
 */
const DROPS = 130
const RINGS = 3

export class FountainWater {
  private readonly drops: THREE.Points
  private readonly dropPos: Float32Array
  private readonly phase: Float32Array
  private readonly angle: Float32Array
  private readonly speed: Float32Array
  private readonly top = new THREE.Vector3()
  private readonly rings: { mesh: THREE.Mesh; mat: THREE.MeshBasicMaterial; offset: number }[] = []
  private readonly surface: THREE.Mesh
  private readonly surfaceMat: THREE.MeshStandardMaterial
  private basinY = 0
  private basinR = 1
  private arcH = 0.5

  constructor(scene: THREE.Scene, fountainNode: THREE.Object3D) {
    const box = new THREE.Box3().setFromObject(fountainNode)
    const size = box.getSize(new THREE.Vector3())
    const center = box.getCenter(new THREE.Vector3())
    // верхняя чаша, гладь бассейна и его радиус — от габаритов модели
    this.top.set(center.x, box.min.y + size.y * 0.86, center.z)
    this.basinY = box.min.y + size.y * 0.30
    this.basinR = Math.min(size.x, size.z) * 0.33
    this.arcH = size.y * 0.22

    let seed = 424242
    const rand = () => {
      seed = (seed * 16807) % 2147483647
      return seed / 2147483647
    }

    // капли
    this.dropPos = new Float32Array(DROPS * 3)
    this.phase = new Float32Array(DROPS)
    this.angle = new Float32Array(DROPS)
    this.speed = new Float32Array(DROPS)
    for (let i = 0; i < DROPS; i++) {
      this.phase[i] = rand()
      this.angle[i] = rand() * Math.PI * 2
      this.speed[i] = 0.55 + rand() * 0.35
    }
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(this.dropPos, 3))
    // круглый мягкий спрайт капли
    const canvas = document.createElement('canvas')
    canvas.width = canvas.height = 32
    const g2d = canvas.getContext('2d')
    if (g2d) {
      const grad = g2d.createRadialGradient(16, 16, 0, 16, 16, 16)
      grad.addColorStop(0, 'rgba(255,255,255,0.95)')
      grad.addColorStop(0.5, 'rgba(210,235,255,0.55)')
      grad.addColorStop(1, 'rgba(210,235,255,0)')
      g2d.fillStyle = grad
      g2d.fillRect(0, 0, 32, 32)
    }
    this.drops = new THREE.Points(
      geo,
      new THREE.PointsMaterial({
        size: 0.09,
        map: new THREE.CanvasTexture(canvas),
        color: 0xcfe9ff,
        transparent: true,
        opacity: 0.85,
        depthWrite: false,
      }),
    )
    this.drops.frustumCulled = false
    this.drops.name = 'fountain-drops'
    scene.add(this.drops)

    // гладь бассейна
    this.surfaceMat = new THREE.MeshStandardMaterial({
      color: 0x9fd0ea,
      transparent: true,
      opacity: 0.78,
      roughness: 0.15,
      metalness: 0,
    })
    this.surface = new THREE.Mesh(
      new THREE.CircleGeometry(this.basinR, 40),
      this.surfaceMat,
    )
    this.surface.rotation.x = -Math.PI / 2
    this.surface.position.set(this.top.x, this.basinY, this.top.z)
    this.surface.name = 'fountain-surface'
    scene.add(this.surface)

    // кольца на глади
    for (let r = 0; r < RINGS; r++) {
      const mat = new THREE.MeshBasicMaterial({
        color: 0xeaf7ff,
        transparent: true,
        opacity: 0,
        depthWrite: false,
      })
      const mesh = new THREE.Mesh(new THREE.RingGeometry(0.9, 1.0, 40), mat)
      mesh.rotation.x = -Math.PI / 2
      mesh.position.set(this.top.x, this.basinY + 0.012, this.top.z)
      scene.add(mesh)
      this.rings.push({ mesh, mat, offset: r / RINGS })
    }
  }

  update(_dt: number, elapsed: number): void {
    // капли: вверх из чаши, наружу и вниз в бассейн
    for (let i = 0; i < DROPS; i++) {
      const t = (elapsed * this.speed[i] * 0.5 + this.phase[i]) % 1
      const r = t * this.basinR * 0.85
      const a = this.angle[i]
      const rise = this.arcH * (1.35 * t - 1.35 * t * t) // парабола, апекс ~t=0.5
      const fall = (this.top.y - this.basinY + this.arcH * 0) * t * t
      const y = this.top.y + rise - (this.top.y - this.basinY) * t * t
      this.dropPos[i * 3] = this.top.x + Math.cos(a) * r
      this.dropPos[i * 3 + 1] = Math.max(this.basinY, y)
      this.dropPos[i * 3 + 2] = this.top.z + Math.sin(a) * r
      void fall
    }
    this.drops.geometry.attributes.position.needsUpdate = true

    // кольца: медленно расширяются и тают
    for (const ring of this.rings) {
      const t = (elapsed * 0.35 + ring.offset) % 1
      const scale = 0.15 + t * this.basinR * 0.92
      ring.mesh.scale.setScalar(scale)
      ring.mat.opacity = 0.35 * (1 - t)
    }

    // лёгкое дыхание глади
    this.surfaceMat.opacity = 0.74 + Math.sin(elapsed * 0.8) * 0.05
  }
}
