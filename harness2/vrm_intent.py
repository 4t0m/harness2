"""Relative intent to existing bounded VRM renderer parameters."""
import math
from .production_dispatch import _strict_object


def compile_intent(raw, anchor_x, offset):
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in (anchor_x,offset)) or offset<=0:
        raise ValueError('finite anchor and positive offset required')
    intent=_strict_object(raw)
    if set(intent)!={'gesture','side'} or intent['gesture'] not in ('salute','wave_goodbye') or intent['side'] not in ('left','right'):
        raise ValueError('unsupported intent')
    x=anchor_x+offset*(1 if intent['side']=='right' else -1)
    if abs(x)>0.6:raise ValueError('relative position exceeds renderer bounds')
    return {'gesture':intent['gesture'],'x_position':x}
