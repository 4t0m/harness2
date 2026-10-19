"""Finite model-selected variations compiled into host-owned motion edits."""
from .production_dispatch import _strict_object

SOURCE_SHA256='85975be49a7fd4c7079501cdce94a27f271b4ccb7d9c71063911e35828da58c4'
VARIATIONS={'soft':2.35,'restrained':2.10}


def compile_variation(raw, current_source_sha256):
    if current_source_sha256!=SOURCE_SHA256:
        raise ValueError('source revision changed; requalify motion contract')
    value=_strict_object(raw)
    if set(value)!={'variation'} or not isinstance(value['variation'],str) or value['variation'] not in VARIATIONS:
        raise ValueError('choose exactly one supported variation')
    return {'source_sha256':SOURCE_SHA256,'variation':value['variation'],
            'joint':'right_shoulder','property':'rotation_euler','axis':1,'keyframe':24,
            'peak_radians':VARIATIONS[value['variation']],'editable_frames':[13,35],
            'protected_frames':[[1,12],[36,48]],'camera':'unchanged'}
