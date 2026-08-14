import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'

export type PropId = 'ball' | 'chalk' | 'blocks' | 'tree'

export interface LoadedEnvironment {
  root: THREE.Group
  props: Partial<Record<PropId, THREE.Object3D>>
}

const PROP_NODES: Record<PropId, string> = {
  ball: 'Ball',
  chalk: 'Chalk',
  blocks: 'Blocks',
  tree: 'Tree',
}

/**
 * Playground GLB replaces the grey-box world. The GLB's `Ground` mesh is
 * renamed to `ground` so the movement raycast keeps working unchanged;
 * story props (Ball/Chalk/Blocks/Tree) are exposed for the interaction
 * system. Prop materials are cloned so the glow pulse never lights up
 * unrelated meshes that share a material (e.g. Tree crown vs bushes).
 */
export async function loadEnvironment(url: string): Promise<LoadedEnvironment> {
  const gltf = await new GLTFLoader().loadAsync(url)
  const root = gltf.scene
  root.name = 'environment'
  root.traverse((child) => {
    if ((child as THREE.Mesh).isMesh) {
      child.castShadow = true
      child.receiveShadow = true
    }
  })

  const ground = root.getObjectByName('Ground')
  if (!ground) throw new Error('environment.glb has no Ground mesh')
  ground.name = 'ground'
  ;(ground as THREE.Mesh).castShadow = false

  const props: Partial<Record<PropId, THREE.Object3D>> = {}
  for (const [id, nodeName] of Object.entries(PROP_NODES) as [PropId, string][]) {
    const node = root.getObjectByName(nodeName)
    if (!node) {
      console.warn(`[Environment] prop "${nodeName}" missing in GLB`)
      continue
    }
    node.traverse((child) => {
      const mesh = child as THREE.Mesh
      if (mesh.isMesh) mesh.material = (mesh.material as THREE.Material).clone()
    })
    props[id] = node
  }
  console.log(`[Environment] loaded (${Object.keys(props).join(', ')})`)
  return { root, props }
}
