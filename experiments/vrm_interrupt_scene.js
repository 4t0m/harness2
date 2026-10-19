const boneNames = ["chest", "head", "hips", "leftFoot", "leftHand", "leftLowerArm", "leftLowerLeg", "leftShoulder", "leftToes", "leftUpperArm", "leftUpperLeg", "neck", "rightFoot", "rightHand", "rightLowerArm", "rightLowerLeg", "rightShoulder", "rightToes", "rightUpperArm", "rightUpperLeg", "spine", "upperChest"];
function capturePose(vrm) {
  return Object.fromEntries(boneNames.map(name => {
    const n=vrm.humanoid.getNormalizedBoneNode(name);
    if (!n) throw new Error('Missing mapped bone: '+name);
    return [name,{position:n.position.toArray(),quaternion:n.quaternion.toArray(),scale:n.scale.toArray()}];
  }));
}
function restorePose(vrm, pose) {
  for (const [name,p] of Object.entries(pose)) {
    const n=vrm.humanoid.getNormalizedBoneNode(name);
    n.position.fromArray(p.position); n.quaternion.fromArray(p.quaternion); n.scale.fromArray(p.scale);
  }
  vrm.update(0);
}
const samples=[];
// A small command-driven VRM performance probe for the native Eidoverse renderer.
const trialWork = Deno.env.get('EIDOVERSE_TRIAL_WORK') || 'work/eidoverse_probe';
const trialCommand = JSON.parse(Deno.readTextFileSync(`${trialWork}/command.json`));
if (!['salute', 'wave_goodbye'].includes(trialCommand.gesture)) {
  throw new Error(`Unsupported trial gesture: ${trialCommand.gesture}`);
}
if (!Array.isArray(trialCommand.position) || trialCommand.position.length !== 3 ||
    !trialCommand.position.every(Number.isFinite)) {
  throw new Error('Trial position must contain three finite numbers');
}

globalThis.setup = async function () {
  globalThis._noAutoEnhance = true;
  const renderer = new THREE.WebGPURenderer({ canvas, antialias: true,
    adapter: GPU_ADAPTER, device: GPU_DEVICE });
  renderer.setSize(WIDTH, HEIGHT);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  await renderer.init();

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x1a2030);
  const camera = new THREE.PerspectiveCamera(50, WIDTH / HEIGHT, 0.1, 100);
  camera.position.set(0, 1.35, 2.5);
  camera.lookAt(0, 1.1, 0);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x404060, 1.6));
  const sun = new THREE.DirectionalLight(0xffffff, 2.5);
  sun.position.set(3, 5, 4);
  scene.add(sun);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(5, 5),
    new THREE.MeshStandardNodeMaterial({ color: 0x344055, roughness: 0.9 }));
  floor.rotation.x = -Math.PI / 2;
  scene.add(floor);

  const loader = new globalThis.GLTFLoader();
  loader.register(p => new globalThis.VRMLoaderPlugin(p));
  const buffer = globalThis.b64toArrayBuffer(globalThis.ASSETS.character_vrm);
  const gltf = await new Promise((resolve, reject) => loader.parse(buffer, '', resolve, reject));
  const vrm = gltf.userData.vrm;
  vrm.scene.position.set(...trialCommand.position);
  scene.add(vrm.scene);
  const idle = await globalThis.playVRMADefault(vrm, 'idle', { loop: false, fade: 0 });
  idle.mixer.update(0.3); vrm.update(0.3);
  globalThis._savedNeutral = capturePose(vrm);
  await globalThis.playVRMADefault(vrm, trialCommand.gesture, { loop: false, fade: 0 });

  globalThis._r = renderer;
  globalThis._s = scene;
  globalThis._c = camera;
  globalThis._vrm = vrm;
  globalThis._trialInitialArm = vrm.humanoid.getNormalizedBoneNode('rightUpperArm')?.quaternion.toArray();
  console.log('[eidoverse-trial] accepted ' + JSON.stringify(trialCommand));
};


globalThis.renderFrame = async function(t, frameIndex) {
  const vrm=globalThis._vrm;
  if(frameIndex===12) {
    const rec=globalThis._vrmMixers.get(vrm);
    rec.mixer.stopAllAction();
    globalThis._vrmMixers.delete(vrm);
    globalThis._mixer=null;
    restorePose(vrm,globalThis._savedNeutral);
  }
  samples.push({frameIndex,pose:capturePose(vrm),root:vrm.scene.position.toArray(),mixerRegistered:globalThis._vrmMixers.has(vrm)});
  await globalThis._r.renderAsync(globalThis._s,globalThis._c);
  if(frameIndex===23) await Deno.writeTextFile(`${trialWork}/interrupt-state.json`,JSON.stringify({neutral:globalThis._savedNeutral,interruptFrame:12,samples},null,2));
};
