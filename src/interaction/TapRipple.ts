import * as THREE from 'three'

/**
 * Мягкий риппл в точке тапа: кольцо плавно расширяется и тает.
 * Никаких вспышек — короткая приятная волна (safety-правила).
 */
export class TapRipple {
  private readonly ring: THREE.Mesh
  private readonly material: THREE.MeshBasicMaterial
  private t = 1 // 1 = анимация завершена

  constructor(scene: THREE.Scene) {
    this.material = new THREE.MeshBasicMaterial({
      color: 0xfff6dd,
      transparent: true,
      opacity: 0,
      depthWrite: false,
    })
    this.ring = new THREE.Mesh(
      new THREE.RingGeometry(0.22, 0.3, 40),
      this.material,
    )
    this.ring.rotation.x = -Math.PI / 2
    this.ring.visible = false
    this.ring.name = 'tap-ripple'
    scene.add(this.ring)
  }

  show(point: THREE.Vector3): void {
    this.ring.position.set(point.x, 0.04, point.z)
    this.t = 0
  }

  update(dt: number): void {
    if (this.t >= 1) {
      this.ring.visible = false
      return
    }
    this.t = Math.min(1, this.t + dt * 2.4)
    const ease = 1 - Math.pow(1 - this.t, 2) // ease-out
    this.ring.visible = true
    this.ring.scale.setScalar(0.7 + ease * 1.5)
    this.material.opacity = 0.6 * (1 - ease)
  }
}
