import * as THREE from 'three'

/**
 * Capsule placeholder for Sophie the dog (white, soft-looking).
 * Replaced by sophie.glb in a later phase.
 */
export function createSophiePlaceholder(): THREE.Group {
  const group = new THREE.Group()
  group.name = 'sophie'

  const body = new THREE.Mesh(
    new THREE.CapsuleGeometry(0.35, 0.6, 8, 16),
    new THREE.MeshStandardMaterial({ color: 0xfffdf5, roughness: 0.9 }),
  )
  // Lay the capsule horizontally so it reads as a small dog body.
  body.rotation.z = Math.PI / 2
  body.position.y = 0.45
  body.castShadow = true
  body.name = 'sophie-body'
  group.add(body)

  // Small head sphere so facing direction is visible in the grey box.
  const head = new THREE.Mesh(
    new THREE.SphereGeometry(0.28, 16, 16),
    new THREE.MeshStandardMaterial({ color: 0xfffdf5, roughness: 0.9 }),
  )
  head.position.set(0, 0.7, 0.55)
  head.castShadow = true
  head.name = 'sophie-head'
  group.add(head)

  group.position.set(0, 0, 0)
  return group
}
