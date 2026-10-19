"""No-network lifecycle checks for the single-allocation trial supervisor."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments import motif_runpod_trial as trial


class ControllerTests(unittest.TestCase):
    def simulate(self, mode='normal'):
        state={'pod':None,'template':None,'allocations':0,'terminations':0,'inference':False}
        def gql(query,variables=None):
            if 'podFindAndDeployOnDemand' in query:
                state['allocations']+=1
                values=variables['input']
                self.assertEqual(values['gpuTypeId'],trial.GPU)
                self.assertEqual(values['volumeInGb'],0)
                self.assertEqual(values['gpuCount'],1)
                self.assertNotIn('RUNPOD_API_KEY',str(values))
                self.assertTrue(values['terminateAfter'].endswith('Z'))
                if mode=='ambiguous': raise RuntimeError('TimeoutError')
                state['pod']={'id':'owned','name':values['name'],'costPerHr':3 if mode=='overrate' else 1.2,
                    'adjustedCostPerHr':None,'gpuCount':1,'volumeInGb':0,
                    'containerDiskInGb':100,'networkVolumeId':None}
                return {'podFindAndDeployOnDemand':state['pod']}
            if 'podTerminate' in query:
                self.assertEqual(variables['input']['podId'],'owned')
                state['terminations']+=1;state['pod']=None
                return {'podTerminate':None}
            if 'podTemplates' in query:
                return {'myself':{'podTemplates':[{'id':'owned-template','isPublic':False,
                    'volumeInGb':0,'containerDiskInGb':100,'isServerless':False}]}}
            if 'gpuTypes' in query:
                return {'gpuTypes':[{'id':trial.GPU,'secure':{'uninterruptablePrice':1.19,'stockStatus':'Low'}}]}
            if 'clientBalance' in query:
                return {'myself':{'clientBalance':0 if mode=='balance' else 10,'pods':[],'currentSpendPerHr':0}}
            return {'myself':{'pods':[] if state['pod'] is None else [state['pod']]}}
        def http(method,url,token,body=None,timeout=15):
            if url==trial.REST+'/templates' and method=='POST':
                self.assertEqual(body['env'],{})
                self.assertFalse(body['isPublic'])
                self.assertEqual(body['ports'],['8080/http'])
                state['template']={**body,'id':'owned-template'}
                return state['template']
            if url==trial.REST+'/templates/owned-template':
                if method=='DELETE': state['template']=None;return None
                return state['template']
            if url==trial.REST+'/templates':
                return [] if state['template'] is None else [state['template']]
            if url==trial.REST+'/pods/owned':
                if state['pod'] is None: raise RuntimeError('http_status_404')
                return state['pod']
            if url.endswith('/trial-status'):
                return {'vllm_ready':True,'child_exit_code':None,
                        'gpu':{'name':'NVIDIA GeForce RTX 5090','driver':'580.1.0'}}
            if url.endswith('/health'): return None
            if url.endswith('/v1/models'): return {'data':[{'id':'qwen'}]}
            raise AssertionError('unhandled test route')
        def probe(provider,output):
            state['inference']=True
            return {'complete':True,'summary':{'compiled':8},'calls':[{}]*8}
        class Viewer:
            def __init__(self,model,output,**kwargs):
                self.url='http://127.0.0.1:12345'
                output.write_text(json.dumps({'calls':[]}))
            def serve(self): pass
        class Timer:
            def __init__(self,*args,**kwargs): pass
            def start(self): pass
            def cancel(self): pass
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'private-run'
            with patch.dict(os.environ,{'RUNPOD_API_KEY':'account-test-secret'}), \
                 patch.object(trial,'gql',gql),patch.object(trial,'http',http), \
                 patch.object(trial.time,'sleep',lambda _:None), \
                 patch.object(trial.threading,'Timer',Timer), \
                 patch.object(trial.signal,'signal'), \
                 patch('experiments.motif_remote_probe.run',probe), \
                 patch('harness2.motif_viewer.MotifViewer',Viewer), \
                 patch('sys.argv',['trial','--private-dir',str(root),'--execute']), \
                 contextlib.redirect_stdout(io.StringIO()):
                trial.main()
            receipt=json.loads((root/'receipt.json').read_text())
            self.assertNotIn('account-test-secret',json.dumps(receipt))
            self.assertNotIn('MOTIF_GATE_TOKEN',os.environ)
        return state,receipt

    def test_success_terminates_and_confirms_by_id(self):
        state,report=self.simulate()
        self.assertEqual(state['allocations'],1)
        self.assertEqual(state['terminations'],1)
        self.assertTrue(state['inference'])
        self.assertTrue(report['pod_absent_verified'])
        self.assertTrue(report['template_absent_verified'])
        self.assertFalse(report['provider_billing_cap_enforced'])

    def test_overrate_deletes_before_any_inference(self):
        state,report=self.simulate('overrate')
        self.assertEqual(state['allocations'],1)
        self.assertFalse(state['inference'])
        self.assertTrue(report['pod_absent_verified'])

    def test_ambiguous_allocation_is_not_retried_or_claimed_absent(self):
        state,report=self.simulate('ambiguous')
        self.assertEqual(state['allocations'],1)
        self.assertFalse(report['pod_absent_verified'])
        self.assertTrue(report['template_absent_verified'])

    def test_insufficient_balance_allocates_nothing(self):
        state,report=self.simulate('balance')
        self.assertEqual(state['allocations'],0)
        self.assertIsNone(state['template'])

if __name__=='__main__': unittest.main()
