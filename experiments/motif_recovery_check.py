"""Independent offline kinematic checks; no dance-quality or biomechanics claims."""
from __future__ import annotations
import hashlib, itertools, json, math
from pathlib import Path
from harness2 import dance_motif_recovery, dance_motif_score, dance_motion, dance_phrases

ROOT = Path(__file__).resolve().parents[1]
FILES = [ROOT / p for p in (
    'experiments/dance_motif_cases.py', 'experiments/motif_recovery_check.py',
    'harness2/dance_motif_score.py',
    'harness2/dance_phrases.py', 'harness2/dance_motion.py',
    'harness2/dance_motif_recovery.py')]
OUT = ROOT / 'evidence/motif-recovery-offline-v2.json'

def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()

def inspect(frames, source, rest):
    checks = {}
    failures = []
    def check(name, ok):
        checks[name] = bool(ok)
        if not ok: failures.append(name)
    check('frame_count_41', type(frames) is list and len(frames) == 41)
    if type(frames) is not list or len(frames) != 41:
        return {'checks': checks, 'failures': failures, 'metrics': {}}
    check('exact_start_pose_and_contacts', frames[0].get('joints') == source['joints'] and frames[0].get('contacts') == source['contacts'])
    check('exact_rest_endpoint', frames[-1].get('joints') == rest)
    times_ok = True; joints_ok = True; contacts_ok = True; feet_ok = True; bounds_ok = True
    max_bone_error = max_step = max_speed = max_accel = 0.0
    previous = None; previous_velocity = None; dt = 1 / 20
    for i, frame in enumerate(frames):
        if (type(frame) is not dict or set(frame) != {'time','joints','contacts'} or
            type(frame.get('time')) not in (int,float) or not math.isfinite(frame['time']) or
            abs(frame['time'] - i*dt) > 1e-9):
            times_ok = False; continue
        joints, contacts = frame['joints'], frame['contacts']
        if (type(joints) is not dict or set(joints) != set(dance_phrases._JOINTS) or
            type(contacts) is not dict or set(contacts) != {'left','right'}):
            joints_ok = False; continue
        if any(type(v) is not bool or v is not True for v in contacts.values()): contacts_ok = False
        for point in joints.values():
            if (type(point) not in (list,tuple) or len(point) != 3 or
                any(type(x) not in (int,float) or not math.isfinite(x) for x in point)):
                joints_ok = False; continue
            if any(abs(x) > 3 for x in point): bounds_ok = False
        for side in ('left','right'):
            for part in ('ankle','foot'):
                name = f'{side}_{part}'
                if joints.get(name) != source['joints'].get(name): feet_ok = False
        for a,b,target,_ in dance_motion._SEGMENTS:
            max_bone_error = max(max_bone_error, abs(math.dist(joints[a],joints[b])-target))
        if previous is not None:
            velocities = {}
            for name in joints:
                delta = math.dist(joints[name], previous[name])
                max_step = max(max_step, delta); max_speed = max(max_speed, delta/dt)
                velocities[name] = tuple((joints[name][k]-previous[name][k])/dt for k in range(3))
                if previous_velocity is not None:
                    accel = math.sqrt(sum((velocities[name][k]-previous_velocity[name][k])**2 for k in range(3)))/dt
                    max_accel = max(max_accel, accel)
            previous_velocity = velocities
        previous = joints
    check('20fps_local_timeline', times_ok)
    check('finite_complete_joint_frames', joints_ok)
    check('both_feet_contact_all_frames', contacts_ok)
    check('ankles_and_foot_markers_fixed', feet_ok)
    check('coordinates_within_3m_bound', bounds_ok)
    check('source_bone_lengths_preserved', max_bone_error <= 1e-6)
    return {'checks': checks, 'failures': failures, 'metrics': {
        'max_joint_step_m': max_step, 'max_joint_speed_m_s': max_speed,
        'max_joint_acceleration_m_s2': max_accel, 'max_bone_length_error_m': max_bone_error,
        'dynamics_scope': 'descriptive finite differences only; no biomechanics acceptance threshold'}}

def run():
    cases=[]; states={}; rest=None
    for motif in ('sway','pulse'):
        for accents in itertools.product(('soft','clear'), repeat=4):
            intent={'motif':motif,'accents':list(accents)}
            compiled=dance_motif_score.compile_intent(json.dumps(intent))
            vr=dance_motif_score.verify_score(compiled); frames=compiled['sequence']['frames']
            if len(frames)!=321 or vr.get('frame_count')!=321: raise AssertionError('source not 321 frames')
            rest=frames[-1]['joints']; ih=digest(intent)
            cases.append({'intent_sha256':ih,'sequence_sha256':compiled['receipt']['sequence_sha256'],'frames':321})
            for ix,frame in enumerate(frames):
                key=digest({'joints':frame['joints'],'contacts':frame['contacts']})
                states.setdefault(key,{'frame':frame,'sources':[]})['sources'].append({'intent_sha256':ih,'frame_index':ix,'time':frame['time']})
    if len(cases)!=32 or rest is None: raise AssertionError('expected all 32 intents')
    rows=[]
    for key,entry in sorted(states.items()):
        src=entry['frame']; before=digest(src)
        out=dance_motif_recovery.recover_frames(src)
        module=dance_motif_recovery.verify_recovery(out,src)
        independent=inspect(out,src,rest)
        unchanged=digest(src)==before
        independent['checks']['source_frame_unchanged']=unchanged
        if not unchanged: independent['failures'].append('source_frame_unchanged')
        rows.append({'pose_sha256':key,'source_provenance_count':len(entry['sources']),
                     'source_frame_examples':entry['sources'][:4], 'module_verification':module,'independent':independent})
    # Choose the source state furthest from shared rest so the restart test is
    # demonstrably interrupted mid-motion rather than a trivial rest-to-rest run.
    def displacement_from_rest(entry):
        joints = entry['frame']['joints']
        return sum((joints[name][axis] - rest[name][axis]) ** 2
                   for name in joints for axis in range(3))
    restart_source_hash, restart_entry = max(
        states.items(), key=lambda item: (displacement_from_rest(item[1]), item[0]))
    restart_source = restart_entry['frame']
    interrupted=dance_motif_recovery.recover_frames(restart_source)[17]
    restarted=dance_motif_recovery.recover_frames(interrupted)
    restart_check=inspect(restarted,interrupted,rest)
    restart_module=dance_motif_recovery.verify_recovery(restarted,interrupted)
    def pose_distance(left, right):
        return math.sqrt(sum((left['joints'][name][axis] - right['joints'][name][axis]) ** 2
                             for name in left['joints'] for axis in range(3)))
    source_pose = {'joints': restart_source['joints'], 'contacts': restart_source['contacts']}
    interrupted_pose = {'joints': interrupted['joints'], 'contacts': interrupted['contacts']}
    restart_source_distance = pose_distance(source_pose, {'joints':rest,'contacts':restart_source['contacts']})
    interrupted_to_source = pose_distance(interrupted_pose, source_pose)
    interrupted_to_rest = pose_distance(interrupted_pose, {'joints':rest,'contacts':interrupted['contacts']})
    nontrivial_restart = restart_source_distance > 1e-4 and interrupted_to_source > 1e-4 and interrupted_to_rest > 1e-4
    restart_check['checks']['interruption_pose_is_nontrivial'] = nontrivial_restart
    restart_check['metrics'].update({'source_from_rest_joint_distance_m':restart_source_distance,
                                     'interrupted_from_source_joint_distance_m':interrupted_to_source,
                                     'interrupted_from_rest_joint_distance_m':interrupted_to_rest})
    if not nontrivial_restart:
        restart_check['failures'].append('interruption_pose_is_nontrivial')
    names=sorted({n for row in rows for n in row['independent']['checks']})
    aggregate={n:{'passed':sum(bool(r['independent']['checks'].get(n)) for r in rows),'total':len(rows)} for n in names}
    failures=[{'pose_sha256':r['pose_sha256'],'failed_checks':r['independent']['failures']} for r in rows if r['independent']['failures']]
    hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}
    dynamics_max = {key: max((r['independent']['metrics'][key] for r in rows), default=0.0)
                    for key in ('max_joint_step_m','max_joint_speed_m_s',
                                'max_joint_acceleration_m_s2','max_bone_length_error_m')}
    evidence={'kind':'offline_motif_recovery_independent_check','schema_version':2,'provider_calls':0,
      'source':{'fixture_case_count':len(cases),'intents_exhausted':len(cases),'frames_per_intent':321,
        'source_frame_instances':len(cases)*321,'unique_joint_contact_states':len(states),
        'provenance_multiplicity_retained':True,'source_intents':cases},
      'recovery':{'unique_pose_recoveries':len(rows),'frames_per_recovery':41,
        'module_verifier_passes':sum(bool(r['module_verification'].get('valid')) for r in rows),
        'independent_checks':aggregate,'failure_count':len(failures),'failures':failures,
        'restart_failure_count':len(restart_check['failures']),
        'observed_maxima':dynamics_max,
        'restart_from_interrupted_sample':{'source_pose_sha256':restart_source_hash,'source_frame_index':17,'module_verification':restart_module,
          'independent_checks':restart_check['checks'],'pose_distance_metrics':{k:v for k,v in restart_check['metrics'].items() if k.endswith('_m')},'failures':restart_check['failures'],
          'passed':not restart_check['failures'],
          'nontrivial_restart_pose':nontrivial_restart,
          'scope':'fresh recover_frames call from captured mid-clip sample; not runtime-state interruption'}},
      'visual_quality':'not assessed; no renderer or human visual review',
      'biomechanics':'not assessed; step, speed and acceleration are descriptive only',
      'source_sha256':hashes,'poses':rows}
    OUT.write_text(json.dumps(evidence,indent=2,sort_keys=True)+'\n')
    return evidence

if __name__=='__main__':
    e=run(); print(json.dumps({'intents':e['source']['intents_exhausted'],'source_frames':e['source']['source_frame_instances'],
      'unique_states':e['source']['unique_joint_contact_states'],'recoveries':e['recovery']['unique_pose_recoveries'],
      'failures':e['recovery']['failure_count'],'restart_passed':e['recovery']['restart_from_interrupted_sample']['passed'],
      'evidence':str(OUT)},indent=2))
