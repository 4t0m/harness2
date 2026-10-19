import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from experiments.production_transfer_probe import main, CASES
from harness2.production_dispatch import valid_choices


class TransferTests(unittest.TestCase):
    def test_frozen_cases_include_wait_and_useful_retry(self):
        self.assertEqual([valid_choices(t)[0]['operation'] for t in CASES], ['wait','retry','wait','retry'])

    def test_corrections_are_bounded_and_saved(self):
        response = SimpleNamespace(content='{"operation":"dispatch","job_id":"missing"}',
                                   usage={}, model='fake', latency_seconds=0, raw_response={})
        previous = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as directory:
                os.chdir(directory)
                Path('evidence').mkdir()
                with patch.dict(os.environ, {'OPENROUTER_API_KEY':'test'}), \
                     patch('experiments.production_transfer_probe.chat_completion', return_value=response) as provider, \
                     contextlib.redirect_stdout(io.StringIO()):
                    main()
                    self.assertEqual(provider.call_count, 8)
                    saved=json.loads(Path('evidence/production-transfer-gemma-live.json').read_text())
                    self.assertEqual([len(r['attempts']) for r in saved['rows']], [2,2,2,2])
                    for row in saved['rows']:
                        self.assertIn('host_feedback', row['attempts'][1]['request'])
                        self.assertFalse(row['attempts'][1]['verdict']['valid'])
                    with self.assertRaises(SystemExit):
                        main()
                    self.assertEqual(provider.call_count, 8)
        finally:
            os.chdir(previous)
