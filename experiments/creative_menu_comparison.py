"""Frozen constraint-following comparison; option order varied, no jobs run."""
import json
import os
from pathlib import Path
import signal
from harness2.actor_provider import chat_completion, ProviderError, ProviderIncomplete
from harness2.production_dispatch import _task, _job
from harness2.production_menu import menu, resolve
from experiments.creative_retry_probe import normalize_single_json_fence

MODELS = ['google/gemma-4-26b-a4b-it', 'google/gemma-4-31b-it']
CASES = [
 ('contact-repair', 'The dance slides at the planted left foot during beats 5–6. Beats 1–4 and 7–8 are approved. Keep those spans and the camera unchanged; inspect contact repair before final rendering.',
  ['Regenerate all eight beats with stronger foot planting.',
   'Hide the sliding with a camera cut during beats 5–6.',
   'Repair the left-foot contact in beats 5–6, preserve neighboring spans, and make a fixed-camera draft.',
   'Render the approved full sequence at final quality.'], 2),
 ('appearance-lock', 'The character silhouette and costume are approved. The next comparison should isolate expression; keep lighting, framing, costume and body pose identical.',
  ['Make three facial expression variants with the same pose, costume, lighting and framing.',
   'Make three expression variants with different camera angles to clarify emotion.',
   'Make three expression variants with revised hair silhouettes and matching lighting.',
   'Make three full-body pose variants with the same face and costume.'], 0),
 ('budget-preview', 'We have 12 GPU-seconds available now. Judge the full eight-beat motion from a fixed camera. Do not shorten it or change the motion; choose a plan that fits the budget.',
  ['Full eight-beat final render, fixed camera, estimated 30 GPU-seconds.',
   'Four-beat low-resolution render, fixed camera, estimated 6 GPU-seconds.',
   'Eight-beat low-resolution render with a regenerated simpler motion, estimated 10 GPU-seconds.',
   'Eight-beat low-resolution render of the existing motion, fixed camera, estimated 10 GPU-seconds.'], 3),
 ('taste-uncertain', 'Two physically valid dance variants are ready. Nobody has watched them, and we have no preference history for this style. Before committing to one, obtain useful taste feedback without generating more variants.',
  ['Commit the variant with the lower foot-sliding score as the most appealing.',
   'Present the two existing fixed-camera previews in a blind comparison with both/neither choices.',
   'Generate four more variants to improve the chance of finding a favorite.',
   'Ask a text model to select the more compelling variant using only filenames.'], 1),
]


def build(case, rotation):
    task_id, brief, descriptions, expected = case
    order=list(range(len(descriptions)))
    order=order[rotation:]+order[:rotation]
    task=_task(task_id, [_job('job_'+str(i),'pending') for i in order])
    labels={'job_'+str(i):d for i,d in enumerate(descriptions)}
    packet=menu(task,labels,brief)
    return task,labels,brief,packet,'job_'+str(expected)


def main():
    output=Path('evidence/creative-menu-comparison-v1.json')
    if output.exists():raise SystemExit('refusing overwrite')
    report={'scope':'explicit constraint and preference-process following; not artistic quality',
            'models':MODELS, 'cases':CASES, 'rotations':[0,1,2], 'max_calls':24,'rows':[]}
    def save():output.write_text(json.dumps(report,indent=2)+'\n')
    save()
    def deadline(*_):raise TimeoutError('call deadline')
    signal.signal(signal.SIGALRM,deadline)
    # Interleave providers, alternating order to reduce time-of-run confounding.
    for rotation in range(3):
        for case in CASES:
            for model in MODELS[::(-1 if rotation%2 else 1)]:
                task,labels,brief,packet,expected=build(case,rotation)
                row={'task_id':task['task_id'],'rotation':rotation,'requested_model':model,
                     'request':packet['prompt'],'expected_job':expected}
                signal.alarm(30)
                try:
                    r=chat_completion(base_url='https://openrouter.ai/api/v1',model=model,
                        api_key=os.environ['OPENROUTER_API_KEY'],system='Choose the legal option that satisfies the user brief. Return strict JSON only.',
                        user=json.dumps(packet['prompt']),timeout=20,max_output_tokens=192,include_raw=True)
                    raw=resolve(task,labels,brief,packet['revision'],r.content)
                    text,changed=normalize_single_json_fence(r.content)
                    repaired=resolve(task,labels,brief,packet['revision'],text)
                    row.update(content=r.content,usage=r.usage,latency_seconds=r.latency_seconds,
                               served_model=r.model,cost=r.raw_response.get('usage',{}).get('cost'),
                               strict_legal=raw['valid'],strict_match=raw.get('action',{}).get('job_id')==expected,
                               format_changed=changed,repaired_legal=repaired['valid'],
                               repaired_match=repaired.get('action',{}).get('job_id')==expected)
                except ProviderIncomplete as exc:row.update(error='incomplete',usage=exc.usage,finish_reason=exc.finish_reason)
                except (ProviderError,TimeoutError,ValueError) as exc:row.update(error=type(exc).__name__)
                finally:signal.alarm(0)
                report['rows'].append(row);save()
                print(json.dumps({k:v for k,v in row.items() if k not in ('request','content')}),flush=True)


if __name__=='__main__':main()
