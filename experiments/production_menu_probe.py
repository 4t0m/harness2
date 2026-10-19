"""Priority-following on legal menus; intentionally different from raw-ledger reasoning."""
import json
import os
from pathlib import Path
import signal
from harness2.actor_provider import chat_completion, ProviderError, ProviderIncomplete
from harness2.production_dispatch import _task, _job
from harness2.production_menu import menu, resolve

CASES = [
    ('pose-explore', 'Before polishing, explore different silhouettes for the same character.',
     ['Render the current pose at final resolution.', 'Make three rough pose variations with different silhouettes.', 'Try three lighting palettes for the current pose.'], 1),
    ('motion-first', 'Keep the camera fixed. Compare the rhythm of two dance phrases before choosing lighting.',
     ['Render two motion phrases using the same camera and neutral lighting.', 'Try three dramatic camera cuts on the current phrase.', 'Design a new lighting palette.'], 0),
    ('preserve-span', 'Keep the approved opening and ending. Revise only the awkward transition in the middle.',
     ['Regenerate the whole dance with a new motif.', 'Replace the opening with a larger gesture.', 'Rework the middle transition while preserving the approved neighboring spans.'], 2),
    ('cheap-preview', 'We have not approved the movement yet. Use the cheapest useful motion preview before spending on final output.',
     ['Render a final high-resolution sequence.', 'Generate a low-resolution fixed-camera preview of the movement.', 'Polish costume textures at full resolution.'], 1),
]


def main():
    output=Path('evidence/production-menu-gemma-live.json')
    if output.exists():raise SystemExit('refusing overwrite')
    report={'scope':'legal-menu priority following, not constraint reasoning or artistic taste', 'rows':[]}
    def deadline(*_):raise TimeoutError('call deadline')
    signal.signal(signal.SIGALRM,deadline)
    for task_id,brief,descriptions,expected in CASES:
        task=_task(task_id, [_job('job_'+str(i),'pending') for i in range(3)])
        labels={'job_'+str(i):s for i,s in enumerate(descriptions)}
        packet=menu(task,labels,brief)
        row={'task_id':task_id,'request':packet['prompt'],'expected_choice':'option_'+str(expected)}
        signal.alarm(30)
        try:
            r=chat_completion(base_url='https://openrouter.ai/api/v1',model='google/gemma-4-26b-a4b-it',
                api_key=os.environ['OPENROUTER_API_KEY'],system='Choose from the legal menu based on the user brief. Return strict JSON only.',
                user=json.dumps(packet['prompt']),timeout=20,max_output_tokens=128,include_raw=True)
            verdict=resolve(task,labels,brief,packet['revision'],r.content)
            matched=verdict.get('action',{}).get('job_id')=='job_'+str(expected)
            row.update(content=r.content,usage=r.usage,latency_seconds=r.latency_seconds,cost=r.raw_response.get('usage',{}).get('cost'),
                       legal=verdict['valid'],priority_match=matched,model=r.model)
        except ProviderIncomplete as exc:row.update(error='incomplete',usage=exc.usage)
        except (ProviderError,TimeoutError) as exc:row.update(error=type(exc).__name__)
        finally:signal.alarm(0)
        report['rows'].append(row)
        output.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(row),flush=True)


if __name__=='__main__':main()
