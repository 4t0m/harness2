import copy,json,unittest
from harness2.dance_phrases import compile_plan
from experiments.dance_phrase_preview import verify_readback

class PhrasePreviewTests(unittest.TestCase):
    def setUp(self):
        seq=compile_plan(json.dumps({'moves':[['rise','soft'],['sway','clear'],['pulse','soft'],['settle','clear']]}))['sequence']
        self.sequences=[seq,copy.deepcopy(seq)];self.readback={'frames':[]}
        for index in range(0,80,2):
            actors=[]
            for offset in [-.8,.8]:
                actors.append({'offset_x':offset,'joints':{n:[p[0]+offset,p[1],p[2]] for n,p in seq['frames'][index]['joints'].items()}})
            self.readback['frames'].append({'source_index':index,'actors':actors})
    def test_independent_world_transform_comparison(self):
        self.assertEqual(verify_readback(self.sequences,self.readback)['frames_checked'],40)
        bad=copy.deepcopy(self.readback);bad['frames'][8]['actors'][1]['joints']['left_wrist'][0]+=.02
        with self.assertRaisesRegex(ValueError,'pose mismatch'):verify_readback(self.sequences,bad)
    def test_reject_wrong_timeline_identity_and_offset(self):
        for kind in ['timeline','identity','offset']:
            bad=copy.deepcopy(self.readback)
            if kind=='timeline':bad['frames'][0]['source_index']=1
            elif kind=='identity':del bad['frames'][0]['actors'][0]['joints']['head']
            else:bad['frames'][0]['actors'][0]['offset_x']=0
            with self.subTest(kind=kind),self.assertRaises(ValueError):verify_readback(self.sequences,bad)

if __name__=='__main__':unittest.main()
