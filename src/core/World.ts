import * as THREE from 'three'

/**
 * Grey-box world: ground plane, gentle sky color, soft warm lighting.
 * Placeholder geometry only — real environment GLB arrives in a later phase.
 */
export function createWorld(scene: THREE.Scene): void {
  // Gentle sky — soft blue, slightly warm fog so distance fades calmly.
  scene.background = new THREE.Color(0xcfe8f5)
  scene.fog = new THREE.Fog(0xcfe8f5, 30, 80)

  // Ground plane — muted warm green, like a quiet courtyard lawn.
  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(60, 60),
    new THREE.MeshStandardMaterial({ color: 0xa8c69f }),
  )
  ground.rotation.x = -Math.PI / 2
  ground.receiveShadow = true
  ground.name = 'ground'
  scene.add(ground)

  // Soft ambient so nothing is ever harshly dark.
  scene.add(new THREE.AmbientLight(0xfff4e0, 0.6))

  // Warm directional "afternoon sun", soft shadows.
  const sun = new THREE.DirectionalLight(0xffe8c0, 1.4)
  sun.position.set(8, 14, 6)
  sun.castShadow = true
  sun.shadow.mapSize.set(2048, 2048)
  sun.shadow.camera.left = -20
  sun.shadow.camera.right = 20
  sun.shadow.camera.top = 20
  sun.shadow.camera.bottom = -20
  scene.add(sun)

  const hemi = new THREE.HemisphereLight(0xcfe8f5, 0xa8c69f, 0.35)
  scene.add(hemi)
}
