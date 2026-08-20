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

/** Двор: кликабельный квадратный газон (raycast ходьбы идёт по 'ground'). */
function buildLawnSquare(): THREE.Mesh {
  const HALF = 16.6
  const geo = new THREE.PlaneGeometry(HALF * 2, HALF * 2, 64, 64)
  geo.rotateX(-Math.PI / 2)
  const pos = geo.attributes.position
  const colors = new Float32Array(pos.count * 3)
  const light = new THREE.Color(0x93c483)
  const deep = new THREE.Color(0x77ab68)
  const c = new THREE.Color()
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i)
    const z = pos.getZ(i)
    const n = (Math.sin(x * 0.9 + z * 0.55) + Math.sin(x * 0.35 - z * 1.15) + 2) / 4
    const speck = Math.sin(x * 7.3 + z * 5.1) * Math.sin(x * 3.7 - z * 8.2) * 0.05
    c.copy(light).lerp(deep, Math.min(1, Math.max(0, n + speck)))
    colors[i * 3] = c.r
    colors[i * 3 + 1] = c.g
    colors[i * 3 + 2] = c.b
  }
  geo.setAttribute('color', new THREE.BufferAttribute(colors, 3))
  const mat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1.0 })
  mat.envMapIntensity = 0.18 // газон не должен бликовать как пол
  const mesh = new THREE.Mesh(geo, mat)
  mesh.name = 'ground'
  mesh.receiveShadow = true
  return mesh
}

/** Территория за забором: суше и бледнее; НЕ 'ground' — туда не сходить. */
function buildOuterGround(): THREE.Mesh {
  const geo = new THREE.PlaneGeometry(66, 66, 32, 32)
  geo.rotateX(-Math.PI / 2)
  const pos = geo.attributes.position
  const colors = new Float32Array(pos.count * 3)
  const light = new THREE.Color(0x9dbd85)
  const deep = new THREE.Color(0x88a973)
  const c = new THREE.Color()
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i)
    const z = pos.getZ(i)
    const n = (Math.sin(x * 0.5 + z * 0.3) + Math.sin(x * 0.21 - z * 0.6) + 2) / 4
    c.copy(light).lerp(deep, n)
    colors[i * 3] = c.r
    colors[i * 3 + 1] = c.g
    colors[i * 3 + 2] = c.b
  }
  geo.setAttribute('color', new THREE.BufferAttribute(colors, 3))
  const mat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1.0 })
  mat.envMapIntensity = 0.18
  const mesh = new THREE.Mesh(geo, mat)
  mesh.name = 'ground-outer'
  mesh.position.y = -0.03
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

/** Трава: InstancedMesh из узла GrassTuft (v2), рассыпанная по острову. */
function buildGrass(root: THREE.Group): void {
  const srcNode = root.getObjectByName('GrassTuft')
  if (!srcNode) return
  let src: THREE.Mesh | null = null
  srcNode.traverse((ch) => {
    if (!src && (ch as THREE.Mesh).isMesh) src = ch as THREE.Mesh
  })
  srcNode.visible = false
  if (!src) return
  const tuft = src as THREE.Mesh
  const COUNT = 5600
  const inst = new THREE.InstancedMesh(tuft.geometry, tuft.material, COUNT)
  // детерминированный PRNG: трава не «пересеивается» между кадрами/сессиями
  let seed = 20260820
  const rand = () => {
    seed = (seed * 16807) % 2147483647
    return seed / 2147483647
  }
  // не сажаем траву в дом, объекты и на плиточную дорожку
  const AVOID_C: [number, number, number][] = [
    [-3.0, -11.6, 1.7], [4.4, -12.6, 2.0], [7.4, -9.4, 2.2],
    [6.2, 8.6, 1.4], [-8.6, -6.4, 1.3], [8.6, 5.4, 0.7],
    [-9.4, -2.0, 1.0], [-5.6, 3.4, 0.9],
  ]
  const AVOID_R: [number, number, number, number][] = [
    [6.6, 13.8, -6.2, 0.2],       // дом справа (x0,x1,z0,z1)
    [-16.2, 8.0, 0.2, 2.6],       // дорожка ворота(запад) -> дом
    [0.2, 2.6, -13.6, 0.6],       // ветка на площадку
  ]
  const dummy = new THREE.Object3D()
  let placed = 0
  const HALF = 15.4
  const OUT_COUNT = 1400 // редкая трава на внешней территории (кроме улицы)
  while (placed < COUNT) {
    const outer = placed >= COUNT - OUT_COUNT
    let x: number
    let z: number
    if (outer) {
      x = -14 + rand() * 46      // восточнее улицы: x in [-14, 32]
      z = (rand() * 2 - 1) * 31
      if (Math.abs(x) < 16.4 && Math.abs(z) < 16.4) continue // двор отдельно
      if (Math.max(Math.abs(x), Math.abs(z)) > 31.5) continue
    } else {
      x = (rand() * 2 - 1) * HALF
      z = (rand() * 2 - 1) * HALF
      if (AVOID_C.some(([ax, az, ar]) => Math.hypot(x - ax, z - az) < ar)) continue
      if (AVOID_R.some(([x0, x1, z0, z1]) => x > x0 && x < x1 && z > z0 && z < z1))
        continue
    }
    dummy.position.set(x, 0, z)
    dummy.rotation.y = rand() * Math.PI * 2
    const s = 0.3 + rand() * 0.35
    dummy.scale.setScalar(s)
    dummy.updateMatrix()
    inst.setMatrixAt(placed++, dummy.matrix)
  }
  inst.receiveShadow = true
  inst.name = 'grass'
  root.add(inst)
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

  // Плоская GLB-земля (только в старом environment.glb) прячется,
  // вместо неё — скруглённый остров-газон.
  const flatGround = root.getObjectByName('Ground')
  if (flatGround) {
    flatGround.visible = false
    flatGround.name = 'ground-flat'
    // Композиция старого набора: полукруглой сценой, а не в линию.
    for (const [nodeName, [dx, dz]] of Object.entries(LAYOUT_SHIFT)) {
      const node = root.getObjectByName(nodeName)
      if (node) {
        node.position.x += dx
        node.position.z += dz
      }
    }
  }
  root.add(buildLawnSquare())
  root.add(buildOuterGround())
  root.add(buildSkyDome())
  buildGrass(root)

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
