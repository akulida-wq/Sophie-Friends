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
/** Уютная полукруглая расстановка: сдвиги узлов площадки (dx, dz). */
const LAYOUT_SHIFT: Record<string, [number, number]> = {
  Slide: [-1.5, 1.8],
  Swing: [1.4, 3.9],
  Sandbox: [0, 1.3],
  TreeDeco2: [0.5, 2.5],
}

/** Газон-остров: скруглённый диск с мягкой двухтоновой вариацией травы. */
function buildLawnIsland(): THREE.Mesh {
  // Плотная сетка, спроецированная в диск: без радиальных полос веера.
  const R = 13.5
  const geo = new THREE.PlaneGeometry(R * 2, R * 2, 72, 72)
  geo.rotateX(-Math.PI / 2)
  const pos = geo.attributes.position
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i)
    const z = pos.getZ(i)
    const r = Math.hypot(x, z)
    if (r > R) {
      const k = R / r
      pos.setX(i, x * k)
      pos.setZ(i, z * k)
    }
  }
  const colors = new Float32Array(pos.count * 3)
  const light = new THREE.Color(0x9ccb8b)
  const deep = new THREE.Color(0x83b975)
  const c = new THREE.Color()
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i)
    const z = pos.getZ(i)
    const n = (Math.sin(x * 0.9 + z * 0.55) + Math.sin(x * 0.35 - z * 1.15) + 2) / 4
    c.copy(light).lerp(deep, n)
    colors[i * 3] = c.r
    colors[i * 3 + 1] = c.g
    colors[i * 3 + 2] = c.b
  }
  geo.setAttribute('color', new THREE.BufferAttribute(colors, 3))
  const mesh = new THREE.Mesh(
    geo,
    new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95 }),
  )
  mesh.name = 'ground'
  mesh.receiveShadow = true
  return mesh
}

/** Небо: купол с вертикальным градиентом (голубой -> кремовый горизонт). */
function buildSkyDome(): THREE.Mesh {
  const geo = new THREE.SphereGeometry(70, 32, 20)
  const pos = geo.attributes.position
  const colors = new Float32Array(pos.count * 3)
  const top = new THREE.Color(0xb9ddf3)
  const horizon = new THREE.Color(0xf6ecd8)
  const c = new THREE.Color()
  for (let i = 0; i < pos.count; i++) {
    const t = Math.min(1, Math.max(0, pos.getY(i) / 70))
    c.copy(horizon).lerp(top, Math.pow(t, 0.65))
    colors[i * 3] = c.r
    colors[i * 3 + 1] = c.g
    colors[i * 3 + 2] = c.b
  }
  geo.setAttribute('color', new THREE.BufferAttribute(colors, 3))
  const mesh = new THREE.Mesh(
    geo,
    new THREE.MeshBasicMaterial({ side: THREE.BackSide, vertexColors: true, fog: false }),
  )
  mesh.name = 'sky-dome'
  return mesh
}

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

  // Плоскую GLB-землю прячем, вместо неё — скруглённый остров-газон.
  const flatGround = root.getObjectByName('Ground')
  if (!flatGround) throw new Error('environment.glb has no Ground mesh')
  flatGround.visible = false
  flatGround.name = 'ground-flat'
  const ground = buildLawnIsland()
  root.add(ground)
  root.add(buildSkyDome())

  // Композиция: площадка полукруглой сценой, а не в линию.
  for (const [nodeName, [dx, dz]] of Object.entries(LAYOUT_SHIFT)) {
    const node = root.getObjectByName(nodeName)
    if (node) {
      node.position.x += dx
      node.position.z += dz
    }
  }

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
