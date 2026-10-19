"""Synthetic live art-job planner probe. Run with an outer process deadline."""
import json
import os
from pathlib import Path
from harness2.actor_provider import chat_completion
from harness2.creative_jobs import JobBoard

PROMPT = '''Plan three independent silhouette auditions under immutable brief-r1: blue coat, no logo, fixed pose. Use capability synthetic_silhouette_v1. Budget metadata exactly 3.0. Invent three distinct descriptive silhouette variation IDs. Return ONLY JSON with exactly parent_revision,capability,budget,jobs. jobs has three objects, each exactly job_id,variation_id,depends_on,status,parent_revision,attempt. Valid job_id is lowercase letters/digits/underscore, starting with a letter. Each depends_on=[], status=pending,parent_revision=brief-r1,attempt=1. This is a plan only; do not claim images exist. No commentary or markdown.'''

def main():
    out = Path('runs/creative-manager-live')
    out.mkdir(parents=True, exist_ok=False)
    reply = chat_completion(base_url='https://openrouter.ai/api/v1',model='google/gemma-4-26b-a4b-it',api_key=os.environ['OPENROUTER_API_KEY'],system='Return only a strict JSON proposal. Do not execute tools or claim completed work.',user=PROMPT,max_output_tokens=700,timeout=25,include_raw=True)
    record={'scope':'live OpenRouter synthetic job-plan trial, not generated art or creative quality evidence','model':reply.model,'finish_reason':reply.finish_reason,'usage':reply.usage,'latency_seconds':reply.latency_seconds,'reported_cost':(reply.raw_response or {}).get('usage',{}).get('cost'),'content':reply.content}
    try:
        proposal=json.loads(reply.content)
        board=JobBoard.from_plan(proposal)
        if reply.finish_reason!='stop' or board.budget != 3.0:
            raise ValueError('incomplete response or altered budget')
        record['valid_plan']=True
        record['snapshot']=board.snapshot()
    except (ValueError,TypeError) as error:
        record['valid_plan']=False
        record['validation_error']=str(error)
    (out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2))

if __name__=='__main__':
    import signal
    signal.alarm(60)
    main()
