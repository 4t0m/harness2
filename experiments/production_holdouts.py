"""Frozen combination cases, excluded from editor context and development runs."""
from harness2.production_dispatch import _task, _job

PUBLIC_RULE = 'A completed retry descendant satisfies a dependency on its original failed ancestor.'


def fixtures():
    return (
        _task('combo-cap-ready', [_job('scene_a', 'failed', attempt=2),
              _job('scene_b', 'pending'), _job('scene_c', 'pending', deps=('scene_a',))], max_attempts=2),
        _task('combo-lineage', [_job('take_a', 'failed'),
              _job('take_b', 'failed', attempt=2, retry_of='take_a'),
              _job('take_c', 'pending', deps=('take_a',))]),
        _task('combo-approval-block', [_job('design_a', 'pending', approval=True),
              _job('design_b', 'failed', attempt=2),
              _job('design_c', 'pending', deps=('design_b',), approval=True, approved=True)], max_attempts=2),
        _task('combo-retry-success', [_job('clip_a', 'failed'),
              _job('clip_b', 'completed', attempt=2, retry_of='clip_a',
                   artifact={'artifact_id':'asset-clip-b','job_id':'clip_b','parent_revision':'dispatch-r1'}),
              _job('clip_c', 'pending', deps=('clip_a',), approval=True, approved=True)]),
    )
