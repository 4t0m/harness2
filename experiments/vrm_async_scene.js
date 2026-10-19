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


let revision=1;
let lastEvent=0;
let interruptedAt=null;
const events=[];
globalThis.renderFrame = async function(t, frameIndex) {
  const vrm=globalThis._vrm;
  if(frameIndex===8) await Deno.writeTextFile(`${trialWork}/ready.json`,JSON.stringify({frameIndex,revision}));
  let event=null;
  try {event=JSON.parse(await Deno.readTextFile(`${trialWork}/event.json`));}
  catch(e) {if(!(e instanceof Deno.errors.NotFound)) throw e;}
  if(event && event.eventId>lastEvent) {
    if(!Number.isInteger(event.eventId)||!Number.isInteger(event.revision)||!['interrupt','gesture'].includes(event.type)) throw new Error('invalid event');
    lastEvent=event.eventId;
    let status;
    if(event.type==='interrupt' && event.revision>revision) {
      revision=event.revision;
      globalThis._vrmMixers.get(vrm)?.mixer.stopAllAction();
      globalThis._vrmMixers.delete(vrm);globalThis._mixer=null;
      restorePose(vrm,globalThis._savedNeutral);
      interruptedAt=frameIndex;status='interrupted';
    } else if(event.revision!==revision) {
      status='stale_rejected';
    } else if(event.type==='gesture' && event.gesture==='wave_goodbye') {
      await globalThis.playVRMADefault(vrm,event.gesture,{loop:false,fade:0});
      status='applied';
    } else {status='unsupported';}
    events.push({eventId:event.eventId,status,frameIndex,revision});
    await Deno.writeTextFile(`${trialWork}/ack-${event.eventId}.json`,JSON.stringify(events.at(-1)));
  }
  const pose=capturePose(vrm);
  let maximumDifference=0;
  for(const [name,p] of Object.entries(pose)) for(const field of ['position','quaternion','scale'])
    for(let i=0;i<p[field].length;i++) maximumDifference=Math.max(maximumDifference,Math.abs(p[field][i]-globalThis._savedNeutral[name][field][i]));
  samples.push({frameIndex,maximumDifference,root:vrm.scene.position.toArray(),arm:pose.rightUpperArm.quaternion,mixerRegistered:globalThis._vrmMixers.has(vrm)});
  await globalThis._r.renderAsync(globalThis._s,globalThis._c);
  if(frameIndex===47) await Deno.writeTextFile(`${trialWork}/async-state.json`,JSON.stringify({interruptedAt,events,samples},null,2));
};
