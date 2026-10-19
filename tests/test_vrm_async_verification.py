import copy
import json
from pathlib import Path
import unittest
from experiments.vrm_async_probe import verify_recovery


class AsyncReceiptTests(unittest.TestCase):
    def setUp(self):
        self.state=json.loads((Path(__file__).resolve().parents[1]/'evidence/vrm-async-live.json').read_text())['state']

    def test_actual_receipt(self):
        self.assertEqual(verify_recovery(self.state),39)

    def test_success_labels_cannot_hide_motion_or_missing_frames(self):
        for field,value in [('maximumDifference',0.2),('mixerRegistered',True),('root',[0,0,0])]:
            changed=copy.deepcopy(self.state);changed['samples'][-1][field]=value
            with self.assertRaises(ValueError):verify_recovery(changed)
        changed=copy.deepcopy(self.state);changed['samples'].pop()
        with self.assertRaises(ValueError):verify_recovery(changed)
        changed=copy.deepcopy(self.state);changed['events'][-1]['status']='applied'
        with self.assertRaises(ValueError):verify_recovery(changed)
