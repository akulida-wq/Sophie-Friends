import * as THREE from 'three'

/** An object or NPC Sophie can approach and tap. */
export interface Interactable {
  id: string
  object: THREE.Object3D
  /** Sophie must be within this distance for the object to glow / react. */
  triggerRadius: number
  onActivate: () => void
}

/** Collect all standard-material meshes so the glow pulse can tint them. */
export function collectMaterials(root: THREE.Object3D): THREE.MeshStandardMaterial[] {
  const materials: THREE.MeshStandardMaterial[] = []
  root.traverse((child) => {
    if (child instanceof THREE.Mesh && child.material instanceof THREE.MeshStandardMaterial) {
      materials.push(child.material)
    }
  })
  return materials
}
