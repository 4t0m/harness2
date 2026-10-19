"""Bounded comparison of compact creative intent and an expanded motif score."""
import copy,hashlib,json,math,time
from pathlib import Path
from urllib.request import urlopen
from harness2.bounded_json_http import request_json

LOCAL=['gemma4:e2b','hermes-lab-qwen3-8b:latest']
HOSTED=['qwen/qwen3.6-35b-a3b','google/gemma-4-26b-a4b-it']
COMMON=('Plan a 32-beat procedural dance at 120 BPM: four eight-beat sections in A,A,B,A order. '
 'Choose the A motif as sway (side-to-side) or pulse (up-and-down). B uses the other motif. '
 'Each section has four two-beat moves: rise, motif, motif, settle. All four moves in a section share its accent, soft or clear. '
 'Each section starts and finishes at rest. Honor the requested motif and the four chronological section accents, including final amendments. '
 'These are technical movement choices, not an authentic dance style. Return minified JSON only, no explanation. ')
SYSTEMS={
 'compact':COMMON+'Return exactly two fields: motif (sway or pulse for A), and accents (array of four strings, each soft or clear). The host expands the score. No other fields.',
 'expanded':COMMON+'Return exactly one field: moves, an array of sixteen [move,accent] pairs in chronological order. Use rise, sway, pulse, settle as move identifiers; use soft or clear as accent identifiers. Emit the full A,A,B,A score. No other fields.'}
SCHEMAS={
 'compact':{'type':'object','required':['motif','accents'],'additionalProperties':False,'properties':{'motif':{'type':'string','enum':['sway','pulse']},'accents':{'type':'array','minItems':4,'maxItems':4,'items':{'type':'string','enum':['soft','clear']}}}},
 'expanded':{'type':'object','required':['moves'],'additionalProperties':False,'properties':{'moves':{'type':'array','minItems':16,'maxItems':16,'items':{'type':'array','minItems':2,'maxItems':2,'items':{'type':'string','enum':['rise','sway','pulse','settle','soft','clear']}}}}}}
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
 from harness2.dance_motif_score import compile_intent,compile_expanded,verify_score
 from experiments.dance_motif_cases import CASES,score_intent
 out=Path('evidence/dance-motif-model-v1.json')
 if out.exists():raise ValueError('refusing overwrite')
 with urlopen('http://127.0.0.1:11434/api/tags',timeout=5) as r:localtags=json.load(r)['models']
 with urlopen('https://openrouter.ai/api/v1/models',timeout=15) as r:hostedtags=json.load(r)['data']
 localmeta={m:next(t for t in localtags if t['name']==m) for m in LOCAL}
 hostmeta={m:next(t for t in hostedtags if t['id']==m) for m in HOSTED}
 if any(float(t['pricing']['prompt'])>1e-6 or float(t['pricing']['completion'])>3e-6 for t in hostmeta.values()):raise ValueError('price cap')
 for c in CASES:
  v=compile_intent(json.dumps(c['expected']));verify_score(v)
  if score_intent(v['intent'],c):raise ValueError('fixture self-check')
 sources=['harness2/dance_motif_score.py','harness2/dance_phrases.py','harness2/dance_motion.py','harness2/bounded_json_http.py','experiments/dance_motif_cases.py','experiments/dance_motif_probe.py']
 report={'scope':'Fixed tool-representation comparison on new within-grammar prose briefs. Not H2 adaptation, learned choreography quality or natural-language acceptance deployment. Host expands compact intent and enforces AABA grammar in both conditions.',
  'sources':{p:digest(p) for p in sources},'cases':copy.deepcopy(CASES),'systems':SYSTEMS,'schemas':SCHEMAS,
  'local_metadata':{m:{k:t.get(k) for k in ['name','digest','size']} for m,t in localmeta.items()},
  'hosted_metadata':{m:{k:t.get(k) for k in ['id','pricing','architecture','supported_parameters']} for m,t in hostmeta.items()},
  'max_calls':128,'max_output_tokens':384,'max_input_bytes':10000,'max_seconds_per_call':30,'reported_cost_stop_usd':.25,'price_caps_per_million':{'prompt':1,'completion':3},
  'correction_policy':'At most one correction only after public grammar/compiler rejection. Valid but brief-inaccurate output is scored offline and never triggers correction. No expected intent enters provider messages.',
  'reported_hosted_cost_usd':0.0,'calls':[],'results':[]}
 calls=report['calls'];errors=0
 def save():out.write_text(json.dumps(report,indent=2)+'\n')
 save()
 try:
  for mi,model in enumerate(LOCAL+HOSTED):
   cases=CASES if mi%2==0 else list(reversed(CASES))
   for ci,case in enumerate(cases):
    conditions=['compact','expanded'] if (mi+ci)%2==0 else ['expanded','compact']
    for condition in conditions:
     compiler=compile_intent if condition=='compact' else compile_expanded
     messages=[{'role':'system','content':SYSTEMS[condition]},{'role':'user','content':case['request']}]
     result={'model':model,'case_id':case['id'],'condition':condition,'attempts':[]};report['results'].append(result)
     for attempt in range(2):
      if len(calls)>=128 or errors>=2 or report.get('cost_unknown') or report['reported_hosted_cost_usd']>=.25:raise RuntimeError('bounded call/error/cost stop')
      if sum(len(m['content'].encode()) for m in messages)>10000:raise ValueError('context cap')
      row={'model':model,'case_id':case['id'],'condition':condition,'attempt':attempt,'messages':copy.deepcopy(messages),'input_text_characters':sum(len(m['content']) for m in messages),'compiled':False,'brief_correct':False}
      calls.append(row);result['attempts'].append(len(calls)-1);save();start=time.monotonic()
      try:
       if model in LOCAL:
        raw=request_json('http://127.0.0.1:11434/api/chat',{'model':model,'messages':messages,'stream':False,'think':False,'format':SCHEMAS[condition],'options':{'temperature':0,'num_ctx':4096,'num_predict':384},'keep_alive':'2m'},timeout=20)
        row['raw_response']=raw;row['content']=raw.get('message',{}).get('content','');row['finish_reason']=raw.get('done_reason')
        row['usage']={'prompt_tokens':raw.get('prompt_eval_count'),'completion_tokens':raw.get('eval_count')}
       else:
        raw=request_json('https://openrouter.ai/api/v1/chat/completions',{'model':model,'messages':messages,'temperature':0,'max_tokens':384,'reasoning':{'enabled':False},'provider':{'max_price':{'prompt':1,'completion':3}},'response_format':{'type':'json_schema','json_schema':{'name':'motif_score','strict':True,'schema':SCHEMAS[condition]}}},timeout=30,bearer_env='OPENROUTER_API_KEY')
        row['raw_response']=raw;row['usage']=raw.get('usage',{});cost=row['usage'].get('cost');row['reported_cost_usd']=cost
        if type(cost) not in (int,float) or not math.isfinite(cost) or cost<0:report['cost_unknown']=True
        else:report['reported_hosted_cost_usd']+=cost
        choice=raw.get('choices',[{}])[0];row['content']=choice.get('message',{}).get('content','');row['finish_reason']=choice.get('finish_reason')
       row['provider_seconds']=time.monotonic()-start;errors=0
       if row['finish_reason']!='stop':raise ValueError('incomplete response')
       compiled=compiler(row['content']);verify_score(compiled)
       row.update(compiled=True,intent=compiled['intent'],motion_receipt=compiled['receipt'])
       row['violations']=score_intent(compiled['intent'],case);row['brief_correct']=not row['violations']
      except Exception as exc:
       row.update(error_type=type(exc).__name__,error=str(exc))
       if 'raw_response' not in row:
        errors+=1
        if model in HOSTED:report['cost_unknown']=True
      row['wall_seconds']=time.monotonic()-start;save()
      print(json.dumps({k:row.get(k) for k in ['model','case_id','condition','attempt','compiled','brief_correct','error']}),flush=True)
      if row['compiled'] or row.get('finish_reason')!='stop':break
      messages += [{'role':'assistant','content':row['content']},{'role':'user','content':'The host rejected the score: '+row['error']+'. Return a corrected score following the original brief and public grammar.'}]
  report['complete']=True
 except Exception as exc:report.update(complete=False,error_type=type(exc).__name__,error=str(exc))
 finally:save();print(json.dumps({'complete':report.get('complete'),'calls':len(calls),'hosted_cost':report['reported_hosted_cost_usd'],'error':report.get('error')}),flush=True)

if __name__=='__main__':main()
